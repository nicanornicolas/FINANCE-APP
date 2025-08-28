# External Integrations Framework

This document describes the external integrations framework implemented for the finance application. The framework provides a comprehensive solution for connecting with external financial services including banks, accounting software, payment processors, and other financial platforms.

## Overview

The integration framework consists of several key components:

1. **Integration Service Architecture** - Core service for managing integrations
2. **OAuth Service** - Handles authentication with external services
3. **Bank Integration Service** - Implements Open Banking API connections
4. **Accounting Integration Service** - Connects with QuickBooks, Xero, etc.
5. **Payment Integration Service** - Integrates with PayPal, Stripe, etc.
6. **Webhook Service** - Handles real-time updates from external services
7. **Integration Monitoring** - Status monitoring and error handling

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Gateway   │    │   Integration   │
│   Application   │◄──►│   (FastAPI)     │◄──►│   Services      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────┐             │
                       │   Database      │◄────────────┘
                       │   (PostgreSQL)  │
                       └─────────────────┘
                                │
                       ┌─────────────────┐
                       │   External      │
                       │   Services      │
                       │   (Banks, etc.) │
                       └─────────────────┘
```

## Database Schema

### Core Tables

#### integrations
Stores integration configurations and status.

```sql
CREATE TABLE integrations (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    integration_type integration_type_enum NOT NULL,
    provider VARCHAR(100) NOT NULL,
    status integration_status_enum NOT NULL DEFAULT 'inactive',
    oauth_provider oauth_provider_enum,
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    config JSON,
    metadata JSON,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    next_sync_at TIMESTAMP WITH TIME ZONE,
    sync_frequency_minutes VARCHAR(50) DEFAULT '60',
    last_error TEXT,
    error_count VARCHAR(10) DEFAULT '0',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);
```

#### webhook_endpoints
Stores webhook endpoint configurations.

```sql
CREATE TABLE webhook_endpoints (
    id UUID PRIMARY KEY,
    integration_id UUID NOT NULL,
    endpoint_url VARCHAR(500) NOT NULL,
    webhook_secret VARCHAR(255),
    event_types JSON NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### webhook_events
Stores incoming webhook events for processing.

```sql
CREATE TABLE webhook_events (
    id UUID PRIMARY KEY,
    webhook_endpoint_id UUID NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_data JSON NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    processing_error TEXT,
    received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);
```

#### integration_logs
Stores integration activity logs.

```sql
CREATE TABLE integration_logs (
    id UUID PRIMARY KEY,
    integration_id UUID NOT NULL,
    action VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    message TEXT,
    details JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## API Endpoints

### Integration Management

- `GET /api/integrations/` - List user integrations
- `POST /api/integrations/` - Create new integration
- `GET /api/integrations/{id}` - Get integration details
- `PUT /api/integrations/{id}` - Update integration
- `DELETE /api/integrations/{id}` - Delete integration
- `GET /api/integrations/{id}/status` - Get integration status
- `POST /api/integrations/{id}/sync` - Manual sync
- `POST /api/integrations/{id}/test` - Test connection

### OAuth Flow

- `POST /api/integrations/oauth/authorize` - Get authorization URL
- `POST /api/integrations/oauth/token` - Exchange code for tokens
- `POST /api/integrations/{id}/oauth/refresh` - Refresh tokens

### Webhooks

- `POST /api/integrations/webhooks/{provider}` - Webhook endpoint

### Monitoring

- `GET /api/integrations/{id}/logs` - Get integration logs
- `POST /api/integrations/sync-all` - Sync all due integrations (admin)
- `POST /api/integrations/refresh-expired-tokens` - Refresh expired tokens (admin)

## Supported Integrations

### Bank APIs (Open Banking)

Supported banks:
- HSBC
- Barclays
- Lloyds
- Santander

Features:
- Account synchronization
- Transaction import
- Balance updates
- Real-time notifications

### Accounting Software

Supported platforms:
- QuickBooks Online
- Xero
- Sage (planned)

Features:
- Chart of accounts sync
- Transaction synchronization
- Invoice management
- Financial reporting

### Payment Processors

Supported processors:
- Stripe
- PayPal
- Square (planned)

Features:
- Payment transaction sync
- Balance tracking
- Payout management
- Dispute handling

### KRA iTax Integration

Features:
- Taxpayer verification
- Tax form preparation
- Electronic filing
- Payment processing

## OAuth Configuration

### Provider Configurations

Each OAuth provider requires specific configuration:

```python
provider_configs = {
    "stripe": {
        "authorization_url": "https://connect.stripe.com/oauth/authorize",
        "token_url": "https://connect.stripe.com/oauth/token",
        "scopes": ["read_write"],
        "client_id": "your_stripe_client_id",
        "client_secret": "your_stripe_client_secret"
    },
    # ... other providers
}
```

### Environment Variables

Required environment variables:

```bash
# Stripe
STRIPE_CLIENT_ID=your_stripe_client_id
STRIPE_CLIENT_SECRET=your_stripe_client_secret

# PayPal
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_client_secret

# QuickBooks
QUICKBOOKS_CLIENT_ID=your_quickbooks_client_id
QUICKBOOKS_CLIENT_SECRET=your_quickbooks_client_secret

# Xero
XERO_CLIENT_ID=your_xero_client_id
XERO_CLIENT_SECRET=your_xero_client_secret

# Open Banking
OPEN_BANKING_CLIENT_ID=your_open_banking_client_id
OPEN_BANKING_CLIENT_SECRET=your_open_banking_client_secret
```

## Webhook Security

### Signature Verification

Each provider uses different signature verification methods:

#### Stripe
```python
def verify_stripe_signature(webhook_secret, headers, payload):
    signature_header = headers.get("stripe-signature")
    # HMAC-SHA256 verification
    return hmac.compare_digest(expected_signature, actual_signature)
```

#### PayPal
```python
def verify_paypal_signature(webhook_secret, headers, payload):
    # Uses PayPal's webhook verification API
    return verify_with_paypal_api(headers, payload)
```

## Error Handling

### Error Types

1. **Authentication Errors** - Invalid or expired tokens
2. **Network Errors** - Connection timeouts, API unavailable
3. **Rate Limiting** - API rate limits exceeded
4. **Data Validation** - Invalid data from external APIs
5. **Business Logic** - Duplicate transactions, invalid accounts

### Error Recovery

- **Exponential Backoff** - Retry failed requests with increasing delays
- **Circuit Breaker** - Temporarily disable failing integrations
- **Fallback Mechanisms** - Use cached data when APIs are unavailable
- **Manual Intervention** - Flag issues requiring user attention

## Monitoring and Alerting

### Health Checks

Each integration provides health status:

```python
{
    "integration_id": "uuid",
    "status": "active|inactive|error|expired",
    "last_sync_at": "2024-01-15T10:30:00Z",
    "next_sync_at": "2024-01-15T11:30:00Z",
    "error_count": 0,
    "health_score": 0.95  # 0.0 to 1.0 based on success rate
}
```

### Metrics

- **Sync Success Rate** - Percentage of successful syncs
- **Response Time** - Average API response times
- **Error Rate** - Rate of errors by type
- **Data Volume** - Amount of data synchronized

### Alerts

- **Integration Failures** - Multiple consecutive failures
- **Token Expiration** - Tokens expiring soon
- **Rate Limiting** - Approaching API limits
- **Data Anomalies** - Unusual data patterns

## Security Considerations

### Data Protection

- **Encryption at Rest** - Sensitive data encrypted in database
- **Encryption in Transit** - All API calls use HTTPS/TLS
- **Token Security** - OAuth tokens encrypted and rotated
- **PII Handling** - Personal data anonymized in logs

### Access Control

- **User Isolation** - Users can only access their integrations
- **Role-Based Access** - Admin functions require elevated permissions
- **API Rate Limiting** - Prevent abuse and ensure fair usage
- **Audit Logging** - All actions logged for compliance

## Testing

### Test Coverage

- **Unit Tests** - Individual service methods
- **Integration Tests** - End-to-end API flows
- **Mock Services** - External API simulation
- **Error Scenarios** - Failure condition testing

### Test Data

- **Anonymized Data** - Real data patterns without PII
- **Edge Cases** - Boundary conditions and unusual scenarios
- **Performance Tests** - Load testing with realistic volumes

## Deployment

### Infrastructure Requirements

- **Database** - PostgreSQL with JSON support
- **Cache** - Redis for session and temporary data
- **Queue** - Celery for background processing
- **Monitoring** - Application performance monitoring

### Configuration Management

- **Environment Variables** - Sensitive configuration
- **Feature Flags** - Enable/disable integrations
- **Rate Limits** - Configurable API limits
- **Retry Policies** - Configurable retry behavior

## Usage Examples

### Creating an Integration

```python
# Create Stripe integration
integration_data = IntegrationCreate(
    name="My Stripe Account",
    integration_type=IntegrationType.PAYMENT_PROCESSOR,
    provider="stripe",
    oauth_provider=OAuthProvider.STRIPE
)

integration = await integration_service.create_integration(
    db, user_id, integration_data
)
```

### OAuth Flow

```python
# Step 1: Get authorization URL
auth_response = await oauth_service.get_authorization_url(
    OAuthProvider.STRIPE,
    redirect_uri="https://myapp.com/callback"
)

# Step 2: Exchange code for tokens
token_response = await oauth_service.exchange_code_for_tokens(
    OAuthProvider.STRIPE,
    authorization_code,
    redirect_uri,
    state
)

# Step 3: Store tokens in integration
integration_crud.update_tokens(
    db, integration_id,
    token_response.access_token,
    token_response.refresh_token,
    token_response.expires_in
)
```

### Manual Sync

```python
# Sync specific integration
result = await integration_service.sync_integration(
    db, integration_id, force=True
)

if result.success:
    print(f"Synced {result.synced_records} records")
else:
    print(f"Sync failed: {result.message}")
```

### Webhook Handling

```python
# Handle incoming webhook
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    headers = dict(request.headers)
    payload = await request.body()
    
    result = await webhook_service.handle_webhook(
        db, "stripe", str(request.url), headers, payload
    )
    
    return {"status": "received"}
```

## Troubleshooting

### Common Issues

1. **Token Expiration** - Refresh tokens automatically
2. **Rate Limiting** - Implement exponential backoff
3. **Data Conflicts** - Handle duplicate detection
4. **Network Timeouts** - Increase timeout values
5. **Invalid Webhooks** - Verify signature validation

### Debug Tools

- **Integration Logs** - Detailed activity logs
- **Health Dashboard** - Real-time status monitoring
- **Test Connections** - Manual connection testing
- **Sync History** - Historical sync performance

## Future Enhancements

### Planned Features

- **Additional Providers** - More banks and services
- **Advanced Analytics** - Deeper integration insights
- **Automated Reconciliation** - Smart transaction matching
- **Custom Integrations** - User-defined API connections
- **Mobile SDK** - Native mobile integration support

### Performance Improvements

- **Caching Strategy** - Intelligent data caching
- **Parallel Processing** - Concurrent sync operations
- **Delta Sync** - Only sync changed data
- **Compression** - Reduce data transfer overhead

This integration framework provides a robust foundation for connecting with external financial services while maintaining security, reliability, and scalability.