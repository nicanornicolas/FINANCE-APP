"""Add integration tables

Revision ID: add_integration_tables
Revises: add_business_tables
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_integration_tables'
down_revision = 'add_business_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types
    integration_type_enum = postgresql.ENUM(
        'bank_api', 'accounting_software', 'payment_processor', 'investment_platform', 'kra_itax',
        name='integrationtype'
    )
    integration_type_enum.create(op.get_bind())
    
    integration_status_enum = postgresql.ENUM(
        'active', 'inactive', 'error', 'pending_auth', 'expired',
        name='integrationstatus'
    )
    integration_status_enum.create(op.get_bind())
    
    oauth_provider_enum = postgresql.ENUM(
        'open_banking', 'quickbooks', 'xero', 'paypal', 'stripe', 'kra_itax',
        name='oauthprovider'
    )
    oauth_provider_enum.create(op.get_bind())
    
    # Create integrations table
    op.create_table(
        'integrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('integration_type', integration_type_enum, nullable=False),
        sa.Column('provider', sa.String(100), nullable=False),
        sa.Column('status', integration_status_enum, nullable=False, default='inactive'),
        sa.Column('oauth_provider', oauth_provider_enum, nullable=True),
        sa.Column('access_token', sa.Text, nullable=True),
        sa.Column('refresh_token', sa.Text, nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('config', postgresql.JSON, nullable=True),
        sa.Column('metadata', postgresql.JSON, nullable=True),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_frequency_minutes', sa.String(50), default='60'),
        sa.Column('last_error', sa.Text, nullable=True),
        sa.Column('error_count', sa.String(10), default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('is_active', sa.Boolean, default=True)
    )
    
    # Create webhook_endpoints table
    op.create_table(
        'webhook_endpoints',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('integration_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('endpoint_url', sa.String(500), nullable=False),
        sa.Column('webhook_secret', sa.String(255), nullable=True),
        sa.Column('event_types', postgresql.JSON, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create webhook_events table
    op.create_table(
        'webhook_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('webhook_endpoint_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_data', postgresql.JSON, nullable=False),
        sa.Column('processed', sa.Boolean, default=False),
        sa.Column('processing_error', sa.Text, nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True)
    )
    
    # Create integration_logs table
    op.create_table(
        'integration_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('integration_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('message', sa.Text, nullable=True),
        sa.Column('details', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    
    # Create indexes
    op.create_index('idx_integrations_user_type', 'integrations', ['user_id', 'integration_type'])
    op.create_index('idx_integrations_provider', 'integrations', ['provider'])
    op.create_index('idx_integrations_status', 'integrations', ['status'])
    op.create_index('idx_integrations_next_sync', 'integrations', ['next_sync_at'])
    op.create_index('idx_webhook_events_processed', 'webhook_events', ['processed'])
    op.create_index('idx_integration_logs_action', 'integration_logs', ['action'])
    op.create_index('idx_integration_logs_status', 'integration_logs', ['status'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_integration_logs_status')
    op.drop_index('idx_integration_logs_action')
    op.drop_index('idx_webhook_events_processed')
    op.drop_index('idx_integrations_next_sync')
    op.drop_index('idx_integrations_status')
    op.drop_index('idx_integrations_provider')
    op.drop_index('idx_integrations_user_type')
    
    # Drop tables
    op.drop_table('integration_logs')
    op.drop_table('webhook_events')
    op.drop_table('webhook_endpoints')
    op.drop_table('integrations')
    
    # Drop enum types
    op.execute('DROP TYPE oauthprovider')
    op.execute('DROP TYPE integrationstatus')
    op.execute('DROP TYPE integrationtype')