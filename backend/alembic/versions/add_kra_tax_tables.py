"""Add KRA tax tables

Revision ID: add_kra_tax_tables
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_kra_tax_tables'
down_revision = None  # Update this to the latest revision
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types
    kra_filing_type = postgresql.ENUM(
        'individual', 'corporate', 'vat', 'withholding', 'turnover', 'rental', 'capital_gains',
        name='krafilingtype'
    )
    kra_filing_status = postgresql.ENUM(
        'draft', 'submitted', 'accepted', 'rejected', 'paid', 'overdue',
        name='krafilingstatus'
    )
    kra_taxpayer_type = postgresql.ENUM(
        'individual', 'corporate', 'partnership', 'trust',
        name='krataxpayertype'
    )
    
    kra_filing_type.create(op.get_bind())
    kra_filing_status.create(op.get_bind())
    kra_taxpayer_type.create(op.get_bind())
    
    # Create kra_taxpayers table
    op.create_table(
        'kra_taxpayers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('kra_pin', sa.String(20), nullable=False, index=True),
        sa.Column('taxpayer_name', sa.String(255), nullable=False),
        sa.Column('taxpayer_type', kra_taxpayer_type, nullable=False),
        sa.Column('registration_date', sa.DateTime, nullable=True),
        sa.Column('tax_office', sa.String(100), nullable=True),
        sa.Column('is_verified', sa.Boolean, default=False),
        sa.Column('last_sync', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create kra_tax_filings table
    op.create_table(
        'kra_tax_filings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('taxpayer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('kra_taxpayers.id'), nullable=False),
        sa.Column('tax_year', sa.Integer, nullable=False),
        sa.Column('filing_type', kra_filing_type, nullable=False),
        sa.Column('forms_data', postgresql.JSON, nullable=True),
        sa.Column('calculated_tax', sa.Numeric(15, 2), nullable=True),
        sa.Column('tax_due', sa.Numeric(15, 2), nullable=True),
        sa.Column('payments_made', sa.Numeric(15, 2), default=0),
        sa.Column('filing_date', sa.DateTime, nullable=True),
        sa.Column('due_date', sa.DateTime, nullable=True),
        sa.Column('kra_reference', sa.String(50), nullable=True, unique=True),
        sa.Column('status', kra_filing_status, default='draft'),
        sa.Column('submission_receipt', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create kra_tax_payments table
    op.create_table(
        'kra_tax_payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('filing_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('kra_tax_filings.id'), nullable=False),
        sa.Column('payment_reference', sa.String(50), nullable=False, unique=True),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('payment_date', sa.DateTime, nullable=False),
        sa.Column('payment_method', sa.String(50), nullable=True),
        sa.Column('kra_receipt', sa.String(100), nullable=True),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create kra_tax_deductions table
    op.create_table(
        'kra_tax_deductions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('tax_year', sa.Integer, nullable=False),
        sa.Column('deduction_type', sa.String(100), nullable=False),
        sa.Column('description', sa.String(255), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('supporting_documents', postgresql.JSON, nullable=True),
        sa.Column('is_verified', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create indexes
    op.create_index('idx_kra_taxpayers_user_id', 'kra_taxpayers', ['user_id'])
    op.create_index('idx_kra_taxpayers_kra_pin', 'kra_taxpayers', ['kra_pin'])
    op.create_index('idx_kra_tax_filings_user_id', 'kra_tax_filings', ['user_id'])
    op.create_index('idx_kra_tax_filings_tax_year', 'kra_tax_filings', ['tax_year'])
    op.create_index('idx_kra_tax_filings_status', 'kra_tax_filings', ['status'])
    op.create_index('idx_kra_tax_payments_filing_id', 'kra_tax_payments', ['filing_id'])
    op.create_index('idx_kra_tax_deductions_user_year', 'kra_tax_deductions', ['user_id', 'tax_year'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_kra_tax_deductions_user_year')
    op.drop_index('idx_kra_tax_payments_filing_id')
    op.drop_index('idx_kra_tax_filings_status')
    op.drop_index('idx_kra_tax_filings_tax_year')
    op.drop_index('idx_kra_tax_filings_user_id')
    op.drop_index('idx_kra_taxpayers_kra_pin')
    op.drop_index('idx_kra_taxpayers_user_id')
    
    # Drop tables
    op.drop_table('kra_tax_deductions')
    op.drop_table('kra_tax_payments')
    op.drop_table('kra_tax_filings')
    op.drop_table('kra_taxpayers')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS krataxpayertype')
    op.execute('DROP TYPE IF EXISTS krafilingstatus')
    op.execute('DROP TYPE IF EXISTS krafilingtype')