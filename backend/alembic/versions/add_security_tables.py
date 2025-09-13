"""Add security tables for RBAC, MFA, and audit logging

Revision ID: add_security_tables
Revises: add_budget_tables
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_security_tables'
down_revision = 'add_budget_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_email', sa.String(), nullable=True),
        sa.Column('action', sa.Enum('LOGIN', 'LOGOUT', 'LOGIN_FAILED', 'PASSWORD_CHANGE', 'PASSWORD_RESET', 'MFA_ENABLED', 'MFA_DISABLED', 'USER_CREATED', 'USER_UPDATED', 'USER_DELETED', 'USER_ACTIVATED', 'USER_DEACTIVATED', 'TRANSACTION_CREATED', 'TRANSACTION_UPDATED', 'TRANSACTION_DELETED', 'TRANSACTION_IMPORTED', 'TRANSACTION_CATEGORIZED', 'ACCOUNT_CREATED', 'ACCOUNT_UPDATED', 'ACCOUNT_DELETED', 'CATEGORY_CREATED', 'CATEGORY_UPDATED', 'CATEGORY_DELETED', 'TAX_FILING_CREATED', 'TAX_FILING_SUBMITTED', 'TAX_FILING_UPDATED', 'KRA_API_CALL', 'TAX_PAYMENT', 'BUSINESS_ENTITY_CREATED', 'BUSINESS_ENTITY_UPDATED', 'INVOICE_CREATED', 'INVOICE_SENT', 'REPORT_GENERATED', 'REPORT_EXPORTED', 'DASHBOARD_VIEWED', 'INTEGRATION_CONNECTED', 'INTEGRATION_DISCONNECTED', 'BANK_SYNC', 'SECURITY_VIOLATION', 'RATE_LIMIT_EXCEEDED', 'UNAUTHORIZED_ACCESS', 'SYSTEM_ERROR', 'DATA_EXPORT', 'DATA_IMPORT', 'BACKUP_CREATED', name='auditaction'), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=True),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('endpoint', sa.String(), nullable=True),
        sa.Column('http_method', sa.String(), nullable=True),
        sa.Column('severity', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='auditseverity'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('success', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)

    # Create security_events table
    op.create_table('security_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('severity', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='auditseverity'), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('resolved', sa.String(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_security_events_created_at'), 'security_events', ['created_at'], unique=False)
    op.create_index(op.f('ix_security_events_event_type'), 'security_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_security_events_id'), 'security_events', ['id'], unique=False)
    op.create_index(op.f('ix_security_events_ip_address'), 'security_events', ['ip_address'], unique=False)
    op.create_index(op.f('ix_security_events_severity'), 'security_events', ['severity'], unique=False)
    op.create_index(op.f('ix_security_events_user_id'), 'security_events', ['user_id'], unique=False)

    # Create roles table
    op.create_table('roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system_role', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('parent_role_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['parent_role_id'], ['roles.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_roles_id'), 'roles', ['id'], unique=False)
    op.create_index(op.f('ix_roles_name'), 'roles', ['name'], unique=False)

    # Create permissions table
    op.create_table('permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('resource', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('is_system_permission', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_permissions_action'), 'permissions', ['action'], unique=False)
    op.create_index(op.f('ix_permissions_id'), 'permissions', ['id'], unique=False)
    op.create_index(op.f('ix_permissions_name'), 'permissions', ['name'], unique=False)
    op.create_index(op.f('ix_permissions_resource'), 'permissions', ['resource'], unique=False)

    # Create user_roles association table
    op.create_table('user_roles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'role_id')
    )

    # Create role_permissions association table
    op.create_table('role_permissions',
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )

    # Create user_permissions table
    op.create_table('user_permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_type', sa.String(), nullable=False),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_permissions_id'), 'user_permissions', ['id'], unique=False)
    op.create_index(op.f('ix_user_permissions_permission_id'), 'user_permissions', ['permission_id'], unique=False)
    op.create_index(op.f('ix_user_permissions_user_id'), 'user_permissions', ['user_id'], unique=False)

    # Create access_logs table
    op.create_table('access_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resource', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('access_granted', sa.Boolean(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('endpoint', sa.String(), nullable=True),
        sa.Column('accessed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_access_logs_accessed_at'), 'access_logs', ['accessed_at'], unique=False)
    op.create_index(op.f('ix_access_logs_action'), 'access_logs', ['action'], unique=False)
    op.create_index(op.f('ix_access_logs_id'), 'access_logs', ['id'], unique=False)
    op.create_index(op.f('ix_access_logs_resource'), 'access_logs', ['resource'], unique=False)
    op.create_index(op.f('ix_access_logs_user_id'), 'access_logs', ['user_id'], unique=False)

    # Create mfa_methods table
    op.create_table('mfa_methods',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('method_type', sa.String(), nullable=False),
        sa.Column('method_name', sa.String(), nullable=True),
        sa.Column('secret_key', sa.String(), nullable=True),
        sa.Column('phone_number', sa.String(), nullable=True),
        sa.Column('email_address', sa.String(), nullable=True),
        sa.Column('backup_codes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('last_used', sa.DateTime(timezone=True), nullable=True),
        sa.Column('use_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mfa_methods_id'), 'mfa_methods', ['id'], unique=False)
    op.create_index(op.f('ix_mfa_methods_user_id'), 'mfa_methods', ['user_id'], unique=False)

    # Create mfa_attempts table
    op.create_table('mfa_attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mfa_method_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('method_type', sa.String(), nullable=False),
        sa.Column('code_provided', sa.String(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('attempted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['mfa_method_id'], ['mfa_methods.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mfa_attempts_attempted_at'), 'mfa_attempts', ['attempted_at'], unique=False)
    op.create_index(op.f('ix_mfa_attempts_id'), 'mfa_attempts', ['id'], unique=False)
    op.create_index(op.f('ix_mfa_attempts_mfa_method_id'), 'mfa_attempts', ['mfa_method_id'], unique=False)
    op.create_index(op.f('ix_mfa_attempts_user_id'), 'mfa_attempts', ['user_id'], unique=False)

    # Create mfa_sessions table
    op.create_table('mfa_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_token', sa.String(), nullable=False),
        sa.Column('challenge_type', sa.String(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('is_expired', sa.Boolean(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_token')
    )
    op.create_index(op.f('ix_mfa_sessions_id'), 'mfa_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_mfa_sessions_session_token'), 'mfa_sessions', ['session_token'], unique=False)
    op.create_index(op.f('ix_mfa_sessions_user_id'), 'mfa_sessions', ['user_id'], unique=False)


def downgrade():
    # Drop tables in reverse order
    op.drop_index(op.f('ix_mfa_sessions_user_id'), table_name='mfa_sessions')
    op.drop_index(op.f('ix_mfa_sessions_session_token'), table_name='mfa_sessions')
    op.drop_index(op.f('ix_mfa_sessions_id'), table_name='mfa_sessions')
    op.drop_table('mfa_sessions')
    
    op.drop_index(op.f('ix_mfa_attempts_user_id'), table_name='mfa_attempts')
    op.drop_index(op.f('ix_mfa_attempts_mfa_method_id'), table_name='mfa_attempts')
    op.drop_index(op.f('ix_mfa_attempts_id'), table_name='mfa_attempts')
    op.drop_index(op.f('ix_mfa_attempts_attempted_at'), table_name='mfa_attempts')
    op.drop_table('mfa_attempts')
    
    op.drop_index(op.f('ix_mfa_methods_user_id'), table_name='mfa_methods')
    op.drop_index(op.f('ix_mfa_methods_id'), table_name='mfa_methods')
    op.drop_table('mfa_methods')
    
    op.drop_index(op.f('ix_access_logs_user_id'), table_name='access_logs')
    op.drop_index(op.f('ix_access_logs_resource'), table_name='access_logs')
    op.drop_index(op.f('ix_access_logs_id'), table_name='access_logs')
    op.drop_index(op.f('ix_access_logs_action'), table_name='access_logs')
    op.drop_index(op.f('ix_access_logs_accessed_at'), table_name='access_logs')
    op.drop_table('access_logs')
    
    op.drop_index(op.f('ix_user_permissions_user_id'), table_name='user_permissions')
    op.drop_index(op.f('ix_user_permissions_permission_id'), table_name='user_permissions')
    op.drop_index(op.f('ix_user_permissions_id'), table_name='user_permissions')
    op.drop_table('user_permissions')
    
    op.drop_table('role_permissions')
    op.drop_table('user_roles')
    
    op.drop_index(op.f('ix_permissions_resource'), table_name='permissions')
    op.drop_index(op.f('ix_permissions_name'), table_name='permissions')
    op.drop_index(op.f('ix_permissions_id'), table_name='permissions')
    op.drop_index(op.f('ix_permissions_action'), table_name='permissions')
    op.drop_table('permissions')
    
    op.drop_index(op.f('ix_roles_name'), table_name='roles')
    op.drop_index(op.f('ix_roles_id'), table_name='roles')
    op.drop_table('roles')
    
    op.drop_index(op.f('ix_security_events_user_id'), table_name='security_events')
    op.drop_index(op.f('ix_security_events_severity'), table_name='security_events')
    op.drop_index(op.f('ix_security_events_ip_address'), table_name='security_events')
    op.drop_index(op.f('ix_security_events_id'), table_name='security_events')
    op.drop_index(op.f('ix_security_events_event_type'), table_name='security_events')
    op.drop_index(op.f('ix_security_events_created_at'), table_name='security_events')
    op.drop_table('security_events')
    
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_timestamp'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_table('audit_logs')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS auditseverity')
    op.execute('DROP TYPE IF EXISTS auditaction')