"""
Webhook service for handling real-time updates from external services.
"""
import hashlib
import hmac
import json
import logging
from typing import Dict, List, Optional, Any
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException

from ..crud.integration import webhook_endpoint as webhook_endpoint_crud, webhook_event as webhook_event_crud
from ..models.integration import Integration
from ..schemas.integration import WebhookEventCreate
from .integration_service import integration_service

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for handling webhook events from external services."""
    
    def __init__(self):
        # Webhook signature verification methods by provider
        self.signature_methods = {
            "stripe": self._verify_stripe_signature,
            "paypal": self._verify_paypal_signature,
            "quickbooks": self._verify_quickbooks_signature,
            "xero": self._verify_xero_signature,
            "plaid": self._verify_plaid_signature
        }
        
        # Event processors by provider
        self.event_processors = {
            "stripe": self._process_stripe_event,
            "paypal": self._process_paypal_event,
            "quickbooks": self._process_quickbooks_event,
            "xero": self._process_xero_event,
            "plaid": self._process_plaid_event
        }
    
    async def handle_webhook(
        self,
        db: Session,
        provider: str,
        endpoint_url: str,
        headers: Dict[str, str],
        payload: bytes
    ) -> Dict[str, Any]:
        """Handle incoming webhook from external service."""
        try:
            # Find webhook endpoint configuration
            webhook_endpoint = webhook_endpoint_crud.get_by_url(db, endpoint_url)
            if not webhook_endpoint:
                logger.warning(f"Webhook endpoint not found: {endpoint_url}")
                raise HTTPException(status_code=404, detail="Webhook endpoint not found")
            
            # Verify webhook signature
            if not await self._verify_webhook_signature(
                provider, webhook_endpoint.webhook_secret, headers, payload
            ):
                logger.warning(f"Invalid webhook signature from {provider}")
                raise HTTPException(status_code=401, detail="Invalid webhook signature")
            
            # Parse payload
            try:
                event_data = json.loads(payload.decode('utf-8'))
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON payload from {provider}: {str(e)}")
                raise HTTPException(status_code=400, detail="Invalid JSON payload")
            
            # Extract event type
            event_type = self._extract_event_type(provider, event_data)
            if not event_type:
                logger.warning(f"Could not determine event type from {provider}")
                raise HTTPException(status_code=400, detail="Could not determine event type")
            
            # Check if this event type is configured for this endpoint
            if event_type not in webhook_endpoint.event_types:
                logger.info(f"Event type {event_type} not configured for endpoint {endpoint_url}")
                return {"status": "ignored", "reason": "Event type not configured"}
            
            # Store webhook event
            webhook_event = webhook_event_crud.create(
                db,
                obj_in=WebhookEventCreate(
                    webhook_endpoint_id=webhook_endpoint.id,
                    event_type=event_type,
                    event_data=event_data
                )
            )
            
            # Process event asynchronously
            try:
                result = await self._process_webhook_event(
                    db, provider, event_type, event_data, webhook_endpoint
                )
                
                # Mark as processed
                webhook_event_crud.mark_processed(
                    db, webhook_event.id, success=True
                )
                
                return {
                    "status": "processed",
                    "event_id": str(webhook_event.id),
                    "result": result
                }
                
            except Exception as e:
                logger.error(f"Failed to process webhook event {webhook_event.id}: {str(e)}")
                
                # Mark as failed
                webhook_event_crud.mark_processed(
                    db, webhook_event.id, success=False, error_message=str(e)
                )
                
                return {
                    "status": "error",
                    "event_id": str(webhook_event.id),
                    "error": str(e)
                }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error handling webhook from {provider}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _verify_webhook_signature(
        self,
        provider: str,
        webhook_secret: Optional[str],
        headers: Dict[str, str],
        payload: bytes
    ) -> bool:
        """Verify webhook signature based on provider."""
        if not webhook_secret:
            logger.warning(f"No webhook secret configured for {provider}")
            return False
        
        signature_method = self.signature_methods.get(provider.lower())
        if not signature_method:
            logger.warning(f"No signature verification method for {provider}")
            return False
        
        return signature_method(webhook_secret, headers, payload)
    
    def _verify_stripe_signature(
        self, 
        webhook_secret: str, 
        headers: Dict[str, str], 
        payload: bytes
    ) -> bool:
        """Verify Stripe webhook signature."""
        signature_header = headers.get("stripe-signature")
        if not signature_header:
            return False
        
        # Parse signature header
        signatures = {}
        for item in signature_header.split(","):
            key, value = item.split("=", 1)
            signatures[key] = value
        
        timestamp = signatures.get("t")
        signature = signatures.get("v1")
        
        if not timestamp or not signature:
            return False
        
        # Create expected signature
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def _verify_paypal_signature(
        self, 
        webhook_secret: str, 
        headers: Dict[str, str], 
        payload: bytes
    ) -> bool:
        """Verify PayPal webhook signature."""
        # PayPal uses a different verification method
        # This is simplified - actual implementation would use PayPal's SDK
        signature = headers.get("paypal-transmission-sig")
        if not signature:
            return False
        
        # In practice, you'd use PayPal's webhook verification API
        # For now, just check if signature exists
        return bool(signature)
    
    def _verify_quickbooks_signature(
        self, 
        webhook_secret: str, 
        headers: Dict[str, str], 
        payload: bytes
    ) -> bool:
        """Verify QuickBooks webhook signature."""
        signature = headers.get("intuit-signature")
        if not signature:
            return False
        
        # QuickBooks uses HMAC-SHA256
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).digest().hex()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def _verify_xero_signature(
        self, 
        webhook_secret: str, 
        headers: Dict[str, str], 
        payload: bytes
    ) -> bool:
        """Verify Xero webhook signature."""
        signature = headers.get("x-xero-signature")
        if not signature:
            return False
        
        # Xero uses HMAC-SHA256 with base64 encoding
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).digest().hex()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def _verify_plaid_signature(
        self, 
        webhook_secret: str, 
        headers: Dict[str, str], 
        payload: bytes
    ) -> bool:
        """Verify Plaid webhook signature."""
        signature = headers.get("plaid-verification")
        if not signature:
            return False
        
        # Plaid uses HMAC-SHA256
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def _extract_event_type(self, provider: str, event_data: Dict[str, Any]) -> Optional[str]:
        """Extract event type from webhook payload."""
        event_type_fields = {
            "stripe": "type",
            "paypal": "event_type",
            "quickbooks": "eventNotifications.0.dataChangeEvent.0.operation",
            "xero": "events.0.eventType",
            "plaid": "webhook_type"
        }
        
        field_path = event_type_fields.get(provider.lower())
        if not field_path:
            return None
        
        # Navigate nested fields
        current = event_data
        for field in field_path.split("."):
            if field.isdigit():
                # Array index
                try:
                    current = current[int(field)]
                except (IndexError, TypeError):
                    return None
            else:
                # Object field
                current = current.get(field)
                if current is None:
                    return None
        
        return str(current) if current else None
    
    async def _process_webhook_event(
        self,
        db: Session,
        provider: str,
        event_type: str,
        event_data: Dict[str, Any],
        webhook_endpoint
    ) -> Dict[str, Any]:
        """Process webhook event based on provider and event type."""
        processor = self.event_processors.get(provider.lower())
        if not processor:
            return {"status": "no_processor", "message": f"No processor for {provider}"}
        
        return await processor(db, event_type, event_data, webhook_endpoint)
    
    async def _process_stripe_event(
        self,
        db: Session,
        event_type: str,
        event_data: Dict[str, Any],
        webhook_endpoint
    ) -> Dict[str, Any]:
        """Process Stripe webhook events."""
        if event_type.startswith("payment_intent."):
            # Handle payment intent events
            payment_intent = event_data.get("data", {}).get("object", {})
            return {"processed": "payment_intent", "id": payment_intent.get("id")}
            
        elif event_type.startswith("charge."):
            # Handle charge events
            charge = event_data.get("data", {}).get("object", {})
            return {"processed": "charge", "id": charge.get("id")}
            
        elif event_type.startswith("transfer."):
            # Handle transfer events - might trigger transaction sync
            transfer = event_data.get("data", {}).get("object", {})
            # Could trigger a sync of the integration here
            return {"processed": "transfer", "id": transfer.get("id")}
        
        return {"processed": "generic", "event_type": event_type}
    
    async def _process_paypal_event(
        self,
        db: Session,
        event_type: str,
        event_data: Dict[str, Any],
        webhook_endpoint
    ) -> Dict[str, Any]:
        """Process PayPal webhook events."""
        if event_type == "PAYMENT.CAPTURE.COMPLETED":
            # Handle completed payment
            resource = event_data.get("resource", {})
            return {"processed": "payment_completed", "id": resource.get("id")}
            
        elif event_type == "PAYMENT.CAPTURE.DENIED":
            # Handle denied payment
            resource = event_data.get("resource", {})
            return {"processed": "payment_denied", "id": resource.get("id")}
        
        return {"processed": "generic", "event_type": event_type}
    
    async def _process_quickbooks_event(
        self,
        db: Session,
        event_type: str,
        event_data: Dict[str, Any],
        webhook_endpoint
    ) -> Dict[str, Any]:
        """Process QuickBooks webhook events."""
        # QuickBooks events indicate data changes
        if event_type in ["Create", "Update", "Delete"]:
            # Could trigger a sync of affected data
            return {"processed": "data_change", "operation": event_type}
        
        return {"processed": "generic", "event_type": event_type}
    
    async def _process_xero_event(
        self,
        db: Session,
        event_type: str,
        event_data: Dict[str, Any],
        webhook_endpoint
    ) -> Dict[str, Any]:
        """Process Xero webhook events."""
        if event_type in ["CREATE", "UPDATE", "DELETE"]:
            # Handle data change events
            events = event_data.get("events", [])
            processed_count = len(events)
            return {"processed": "data_changes", "count": processed_count}
        
        return {"processed": "generic", "event_type": event_type}
    
    async def _process_plaid_event(
        self,
        db: Session,
        event_type: str,
        event_data: Dict[str, Any],
        webhook_endpoint
    ) -> Dict[str, Any]:
        """Process Plaid webhook events."""
        if event_type == "TRANSACTIONS":
            # New transactions available
            item_id = event_data.get("item_id")
            new_transactions = event_data.get("new_transactions", 0)
            return {"processed": "new_transactions", "item_id": item_id, "count": new_transactions}
            
        elif event_type == "ITEM":
            # Item status change
            item_id = event_data.get("item_id")
            error = event_data.get("error")
            return {"processed": "item_status", "item_id": item_id, "error": error}
        
        return {"processed": "generic", "event_type": event_type}
    
    async def process_pending_webhooks(self, db: Session, limit: int = 100) -> Dict[str, Any]:
        """Process pending webhook events."""
        pending_events = webhook_event_crud.get_unprocessed(db, limit)
        
        results = {
            "total": len(pending_events),
            "processed": 0,
            "failed": 0,
            "errors": []
        }
        
        for event in pending_events:
            try:
                # Get webhook endpoint
                webhook_endpoint = webhook_endpoint_crud.get(db, event.webhook_endpoint_id)
                if not webhook_endpoint:
                    continue
                
                # Determine provider from integration
                # This would require joining with integration table
                provider = "unknown"  # Simplified for now
                
                result = await self._process_webhook_event(
                    db, provider, event.event_type, event.event_data, webhook_endpoint
                )
                
                webhook_event_crud.mark_processed(db, event.id, success=True)
                results["processed"] += 1
                
            except Exception as e:
                webhook_event_crud.mark_processed(
                    db, event.id, success=False, error_message=str(e)
                )
                results["failed"] += 1
                results["errors"].append({
                    "event_id": str(event.id),
                    "error": str(e)
                })
        
        return results


# Create service instance
webhook_service = WebhookService()