"""
Rate limiting middleware for API endpoints.
"""
import time
import json
from typing import Dict, Optional, Tuple
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
import redis
import asyncio
from datetime import datetime, timedelta

from ..core.config import settings


class RateLimiter:
    """Redis-based rate limiter with sliding window algorithm."""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self.redis_client = None
        self._connect_redis()
    
    def _connect_redis(self):
        """Connect to Redis."""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self.redis_client.ping()
        except Exception as e:
            print(f"Redis connection failed: {e}")
            # Fallback to in-memory storage for development
            self.redis_client = None
            self._memory_store = {}
    
    async def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int,
        identifier: str = None
    ) -> Tuple[bool, Dict[str, int]]:
        """
        Check if request is allowed based on rate limit.
        
        Args:
            key: Rate limit key (e.g., "api:user:123" or "api:ip:192.168.1.1")
            limit: Maximum requests allowed in window
            window_seconds: Time window in seconds
            identifier: Additional identifier for logging
        
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        current_time = int(time.time())
        window_start = current_time - window_seconds
        
        if self.redis_client:
            return await self._redis_rate_limit(key, limit, window_seconds, current_time, window_start)
        else:
            return await self._memory_rate_limit(key, limit, window_seconds, current_time, window_start)
    
    async def _redis_rate_limit(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int, 
        current_time: int, 
        window_start: int
    ) -> Tuple[bool, Dict[str, int]]:
        """Redis-based rate limiting."""
        pipe = self.redis_client.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(current_time): current_time})
        
        # Set expiry
        pipe.expire(key, window_seconds)
        
        results = pipe.execute()
        current_requests = results[1]
        
        rate_limit_info = {
            "limit": limit,
            "remaining": max(0, limit - current_requests - 1),
            "reset": current_time + window_seconds,
            "window": window_seconds
        }
        
        return current_requests < limit, rate_limit_info
    
    async def _memory_rate_limit(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int, 
        current_time: int, 
        window_start: int
    ) -> Tuple[bool, Dict[str, int]]:
        """In-memory rate limiting fallback."""
        if key not in self._memory_store:
            self._memory_store[key] = []
        
        # Remove old entries
        self._memory_store[key] = [
            timestamp for timestamp in self._memory_store[key] 
            if timestamp > window_start
        ]
        
        current_requests = len(self._memory_store[key])
        
        rate_limit_info = {
            "limit": limit,
            "remaining": max(0, limit - current_requests - 1),
            "reset": current_time + window_seconds,
            "window": window_seconds
        }
        
        if current_requests < limit:
            self._memory_store[key].append(current_time)
            return True, rate_limit_info
        
        return False, rate_limit_info


class RateLimitConfig:
    """Rate limit configurations for different endpoints."""
    
    # Default rate limits (requests per minute)
    DEFAULT_RATE_LIMIT = 60
    
    # Endpoint-specific rate limits
    ENDPOINT_LIMITS = {
        "/auth/login": 5,  # 5 login attempts per minute
        "/auth/register": 3,  # 3 registrations per minute
        "/auth/forgot-password": 3,  # 3 password reset requests per minute
        "/transactions/import": 10,  # 10 imports per minute
        "/api/kra/file": 2,  # 2 KRA filings per minute
        "/api/reports/generate": 20,  # 20 report generations per minute
    }
    
    # User-based rate limits (requests per minute)
    USER_RATE_LIMITS = {
        "default": 100,
        "premium": 200,
        "admin": 500
    }
    
    # IP-based rate limits (requests per minute)
    IP_RATE_LIMIT = 200


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware."""
    rate_limiter = RateLimiter()
    
    # Get client IP
    client_ip = request.client.host
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    
    # Get endpoint path
    endpoint_path = request.url.path
    
    # Determine rate limit
    endpoint_limit = RateLimitConfig.ENDPOINT_LIMITS.get(
        endpoint_path, 
        RateLimitConfig.DEFAULT_RATE_LIMIT
    )
    
    # Check IP-based rate limit
    ip_key = f"rate_limit:ip:{client_ip}"
    ip_allowed, ip_info = await rate_limiter.is_allowed(
        ip_key, 
        RateLimitConfig.IP_RATE_LIMIT, 
        60,  # 1 minute window
        client_ip
    )
    
    if not ip_allowed:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests from this IP address",
                    "details": {
                        "limit": ip_info["limit"],
                        "reset": ip_info["reset"],
                        "retry_after": ip_info["reset"] - int(time.time())
                    }
                }
            },
            headers={
                "X-RateLimit-Limit": str(ip_info["limit"]),
                "X-RateLimit-Remaining": str(ip_info["remaining"]),
                "X-RateLimit-Reset": str(ip_info["reset"]),
                "Retry-After": str(ip_info["reset"] - int(time.time()))
            }
        )
    
    # Check endpoint-specific rate limit
    endpoint_key = f"rate_limit:endpoint:{endpoint_path}:{client_ip}"
    endpoint_allowed, endpoint_info = await rate_limiter.is_allowed(
        endpoint_key,
        endpoint_limit,
        60,  # 1 minute window
        f"{client_ip}:{endpoint_path}"
    )
    
    if not endpoint_allowed:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": {
                    "code": "ENDPOINT_RATE_LIMIT_EXCEEDED",
                    "message": f"Too many requests to {endpoint_path}",
                    "details": {
                        "limit": endpoint_info["limit"],
                        "reset": endpoint_info["reset"],
                        "retry_after": endpoint_info["reset"] - int(time.time())
                    }
                }
            },
            headers={
                "X-RateLimit-Limit": str(endpoint_info["limit"]),
                "X-RateLimit-Remaining": str(endpoint_info["remaining"]),
                "X-RateLimit-Reset": str(endpoint_info["reset"]),
                "Retry-After": str(endpoint_info["reset"] - int(time.time()))
            }
        )
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers to response
    response.headers["X-RateLimit-Limit"] = str(endpoint_info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(endpoint_info["remaining"])
    response.headers["X-RateLimit-Reset"] = str(endpoint_info["reset"])
    
    return response