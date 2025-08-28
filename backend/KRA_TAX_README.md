# KRA Tax Integration

This document describes the KRA (Kenya Revenue Authority) tax integration implementation for the finance application.

## Overview

The KRA tax integration provides comprehensive tax preparation, calculation, and filing capabilities for Kenyan taxpayers. It integrates with the KRA iTax system to enable electronic filing and payment processing.

## Features

### Core Features
- **KRA PIN Validation**: Validate taxpayer PINs with KRA iTax system
- **Taxpayer Registration**: Register and verify taxpayers
- **Tax Calculation**: Calculate taxes according to current KRA rates and rules
- **Electronic Filing**: Submit tax returns directly to KRA iTax
- **Payment Processing**: Process tax payments through KRA-approved channels
- **Status Tracking**: Monitor filing and payment status

### Supported Tax Types
- Individual Income Tax (IT1)
- Value Added Tax (VAT 3)
- Withholding Tax
- Turnover Tax (for small businesses)
- Rental Income Tax
- Capital Gains Tax

### Tax Deductions Supported
- Insurance Relief (limited to KES 60,000)
- Mortgage Interest Relief (limited to KES 300,000)
- Pension Contributions
- NHIF Contributions
- NSSF Contributions

## Architecture

### Components

1. **KRA API Client** (`app/services/kra_api_client.py`)
   - Handles OAuth authentication with KRA iTax
   - Manages API communication
   - Implements retry logic and error handling

2. **Tax Calculator** (`app/services/kra_tax_calculator.py`)
   - Implements Kenyan tax calculation logic
   - Supports progressive tax brackets
   - Handles various tax types (Individual, VAT, WHT)

3. **Tax Service** (`app/services/kra_tax_service.py`)
   - Orchestrates tax preparation workflow
   - Manages taxpayer registration and verification
   - Handles filing creation and submission

4. **Database Models** (`app/models/kra_tax.py`)
   - KRATaxpayer: Taxpayer information
   - KRATaxFiling: Tax filing records
   - KRATaxPayment: Payment tracking
   - KRATaxDeduction: Tax deductions

5. **API Endpoints** (`app/api/routers/kra_tax.py`)
   - RESTful API for tax operations
   - Authentication and authorization
   - Input validation and error handling

## Configuration

### Environment Variables

```bash
# KRA API Configuration
KRA_API_BASE_URL=https://itax.kra.go.ke/api/v1
KRA_CLIENT_ID=your_client_id
KRA_CLIENT_SECRET=your_client_secret
USE_MOCK_KRA=true  # Set to false in production

# Encryption for sensitive data
ENCRYPTION_KEY=your_encryption_key
```

### Development Setup

1. **Install Dependencies**
   ```bash
   pip install httpx cryptography
   ```

2. **Run Database Migrations**
   ```bash
   alembic upgrade head
   ```

3. **Configure KRA API Credentials**
   - Obtain credentials from KRA developer portal
   - Update environment variables

## API Endpoints

### Authentication
All endpoints require authentication via JWT token.

### Taxpayer Management
- `POST /api/kra/validate-pin` - Validate KRA PIN
- `POST /api/kra/taxpayer` - Register taxpayer
- `GET /api/kra/taxpayer` - Get taxpayer info
- `POST /api/kra/taxpayer/{id}/verify` - Verify taxpayer with KRA

### Tax Filing
- `POST /api/kra/filings` - Create tax filing
- `GET /api/kra/filings` - Get user's filings
- `POST /api/kra/filings/{id}/calculate` - Calculate tax
- `POST /api/kra/filings/{id}/submit` - Submit to KRA
- `GET /api/kra/filings/{id}/status` - Get filing status

### Tax Deductions
- `POST /api/kra/deductions` - Add tax deduction
- `GET /api/kra/deductions/{year}` - Get deductions for year

### Utilities
- `GET /api/kra/forms/{year}` - Get available tax forms
- `GET /api/kra/tax-rates/{year}` - Get tax rates
- `GET /api/kra/dashboard` - Get tax dashboard data

## Usage Examples

### 1. Register Taxpayer
```python
# Validate PIN first
pin_validation = await kra_service.validate_kra_pin("P051234567Z")

if pin_validation.is_valid:
    # Register taxpayer
    taxpayer_data = KRATaxpayerCreate(
        kra_pin="P051234567Z",
        taxpayer_name="John Doe",
        taxpayer_type=KRATaxpayerType.INDIVIDUAL,
        tax_office="Nairobi South"
    )
    taxpayer = kra_service.register_taxpayer(db, taxpayer_data=taxpayer_data, user_id=user_id)
```

### 2. Create and Submit Tax Filing
```python
# Create filing
filing_data = KRATaxFilingCreate(
    taxpayer_id=taxpayer.id,
    tax_year=2024,
    filing_type=KRAFilingType.INDIVIDUAL,
    due_date=datetime(2025, 6, 30)
)
filing = kra_service.create_tax_filing(db, filing_data=filing_data, user_id=user_id)

# Calculate tax
calculation = await kra_service.calculate_tax(db, user_id=user_id, filing_id=filing.id)

# Submit to KRA
submission = await kra_service.submit_tax_filing(db, user_id=user_id, filing_id=filing.id)
```

### 3. Add Tax Deductions
```python
# Add insurance deduction
deduction = KRATaxDeductionCreate(
    tax_year=2024,
    deduction_type="insurance",
    description="Life insurance premium",
    amount=Decimal("50000")
)
kra_service.add_tax_deduction(db, deduction_data=deduction, user_id=user_id)
```

## Tax Calculation Logic

### Individual Income Tax (2024 Rates)
- KES 0 - 288,000: 10%
- KES 288,001 - 388,000: 25%
- KES 388,001 - 6,000,000: 30%
- KES 6,000,001 - 9,600,000: 32.5%
- Above KES 9,600,000: 35%

### Personal Relief
- KES 28,800 per year

### VAT
- Standard rate: 16%
- Zero-rated and exempt supplies supported

### Withholding Tax Rates
- Dividends: 5%
- Interest: 15%
- Rent: 10%
- Professional fees: 5%

## Testing

### Unit Tests
```bash
pytest backend/tests/test_kra_tax.py -v
```

### Integration Tests
```bash
pytest backend/tests/test_kra_tax.py::TestKRATaxIntegration -v
```

### Mock vs Real API
- Development uses mock KRA API client
- Production uses real KRA iTax API
- Controlled by `USE_MOCK_KRA` environment variable

## Security Considerations

### Data Protection
- KRA PINs are encrypted at rest
- Sensitive data transmitted over HTTPS
- API tokens have limited lifespan
- Audit trails for all tax operations

### Compliance
- Follows KRA data protection requirements
- Implements proper authentication and authorization
- Maintains data integrity and consistency

## Error Handling

### Common Errors
- Invalid KRA PIN format
- Taxpayer not verified
- Duplicate filing attempts
- KRA API connectivity issues
- Tax calculation errors

### Error Responses
All errors return structured JSON responses:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid KRA PIN format",
    "details": {
      "field": "kra_pin",
      "reason": "PIN must start with P and be 11 characters"
    }
  }
}
```

## Monitoring and Logging

### Logging
- All KRA API interactions are logged
- Tax calculations are audited
- Filing submissions tracked
- Payment processing monitored

### Metrics
- API response times
- Success/failure rates
- Filing completion rates
- Payment processing status

## Deployment

### Production Checklist
- [ ] Configure real KRA API credentials
- [ ] Set `USE_MOCK_KRA=false`
- [ ] Configure encryption keys
- [ ] Run database migrations
- [ ] Set up monitoring and alerting
- [ ] Configure backup procedures
- [ ] Test KRA API connectivity

### Environment-Specific Settings
- **Development**: Mock KRA API, debug logging
- **Staging**: Real KRA sandbox, full logging
- **Production**: Real KRA API, error logging only

## Support and Maintenance

### KRA API Updates
- Monitor KRA developer portal for API changes
- Update tax rates annually
- Test new KRA features in sandbox

### Regular Maintenance
- Update tax brackets and rates
- Refresh KRA API credentials
- Monitor system performance
- Review and update test cases

## Troubleshooting

### Common Issues
1. **KRA API Authentication Failures**
   - Check client credentials
   - Verify API endpoint URLs
   - Check network connectivity

2. **Tax Calculation Discrepancies**
   - Verify tax rates are current
   - Check deduction limits
   - Review calculation logic

3. **Filing Submission Errors**
   - Ensure taxpayer is verified
   - Check required form fields
   - Verify KRA reference format

### Debug Mode
Enable debug logging to troubleshoot issues:
```python
import logging
logging.getLogger('app.services.kra_api_client').setLevel(logging.DEBUG)
```

## Contributing

### Code Standards
- Follow PEP 8 style guidelines
- Add type hints to all functions
- Write comprehensive tests
- Document all public APIs

### Testing Requirements
- Unit tests for all calculation logic
- Integration tests for API endpoints
- Mock tests for KRA API interactions
- Performance tests for large datasets

### Documentation
- Update this README for new features
- Add docstrings to all functions
- Include usage examples
- Document configuration changes