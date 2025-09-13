"""Add budget and financial planning tables

Revision ID: add_budget_tables
Revises: add_integration_tables
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_budget_tables'
down_revision = 'add_integration_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types
    budget_period_enum = postgresql.ENUM('weekly', 'monthly', 'quarterly', 'yearly', name='budgetperiod')
    budget_status_enum = postgresql.ENUM('active', 'inactive', 'archived', name='budgetstatus')
    goal_type_enum = postgresql.ENUM('savings', 'debt_payoff', 'investment', 'emergency_fund', 'custom', name='goaltype')
    goal_status_enum = postgresql.ENUM('active', 'completed', 'paused', 'cancelled', name='goalstatus')
    alert_type_enum = postgresql.ENUM('budget_exceeded', 'budget_warning', 'goal_milestone', 'cash_flow_warning', name='alerttype')
    alert_status_enum = postgresql.ENUM('pending', 'sent', 'read', 'dismissed', name='alertstatus')
    
    budget_period_enum.create(op.get_bind())
    budget_status_enum.create(op.get_bind())
    goal_type_enum.create(op.get_bind())
    goal_status_enum.create(op.get_bind())
    alert_type_enum.create(op.get_bind())
    alert_status_enum.create(op.get_bind())

    # Create budgets table
    op.create_table('budgets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('period', budget_period_enum, nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('status', budget_status_enum, nullable=False),
        sa.Column('is_template', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_budgets_id'), 'budgets', ['id'], unique=False)
    op.create_index(op.f('ix_budgets_user_id'), 'budgets', ['user_id'], unique=False)

    # Create budget_categories table
    op.create_table('budget_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('budget_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('allocated_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('warning_threshold', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['budget_id'], ['budgets.id'], ),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_budget_categories_budget_id'), 'budget_categories', ['budget_id'], unique=False)
    op.create_index(op.f('ix_budget_categories_category_id'), 'budget_categories', ['category_id'], unique=False)
    op.create_index(op.f('ix_budget_categories_id'), 'budget_categories', ['id'], unique=False)

    # Create financial_goals table
    op.create_table('financial_goals',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('goal_type', goal_type_enum, nullable=False),
        sa.Column('target_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('current_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('target_date', sa.Date(), nullable=True),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', goal_status_enum, nullable=False),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('auto_contribute', sa.Boolean(), nullable=True),
        sa.Column('contribution_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('contribution_frequency', budget_period_enum, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_financial_goals_id'), 'financial_goals', ['id'], unique=False)
    op.create_index(op.f('ix_financial_goals_user_id'), 'financial_goals', ['user_id'], unique=False)

    # Create goal_milestones table
    op.create_table('goal_milestones',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('goal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('target_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('target_date', sa.Date(), nullable=True),
        sa.Column('achieved_date', sa.Date(), nullable=True),
        sa.Column('is_achieved', sa.Boolean(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['goal_id'], ['financial_goals.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_goal_milestones_goal_id'), 'goal_milestones', ['goal_id'], unique=False)
    op.create_index(op.f('ix_goal_milestones_id'), 'goal_milestones', ['id'], unique=False)

    # Create cash_flow_forecasts table
    op.create_table('cash_flow_forecasts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('forecast_date', sa.Date(), nullable=False),
        sa.Column('predicted_income', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('predicted_expenses', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('predicted_balance', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('confidence_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('model_version', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cash_flow_forecasts_forecast_date'), 'cash_flow_forecasts', ['forecast_date'], unique=False)
    op.create_index(op.f('ix_cash_flow_forecasts_id'), 'cash_flow_forecasts', ['id'], unique=False)
    op.create_index(op.f('ix_cash_flow_forecasts_user_id'), 'cash_flow_forecasts', ['user_id'], unique=False)

    # Create budget_alerts table
    op.create_table('budget_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('budget_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('goal_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('alert_type', alert_type_enum, nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(), nullable=True),
        sa.Column('status', alert_status_enum, nullable=False),
        sa.Column('triggered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['budget_id'], ['budgets.id'], ),
        sa.ForeignKeyConstraint(['goal_id'], ['financial_goals.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_budget_alerts_budget_id'), 'budget_alerts', ['budget_id'], unique=False)
    op.create_index(op.f('ix_budget_alerts_goal_id'), 'budget_alerts', ['goal_id'], unique=False)
    op.create_index(op.f('ix_budget_alerts_id'), 'budget_alerts', ['id'], unique=False)
    op.create_index(op.f('ix_budget_alerts_user_id'), 'budget_alerts', ['user_id'], unique=False)


def downgrade():
    # Drop tables
    op.drop_index(op.f('ix_budget_alerts_user_id'), table_name='budget_alerts')
    op.drop_index(op.f('ix_budget_alerts_id'), table_name='budget_alerts')
    op.drop_index(op.f('ix_budget_alerts_goal_id'), table_name='budget_alerts')
    op.drop_index(op.f('ix_budget_alerts_budget_id'), table_name='budget_alerts')
    op.drop_table('budget_alerts')
    
    op.drop_index(op.f('ix_cash_flow_forecasts_user_id'), table_name='cash_flow_forecasts')
    op.drop_index(op.f('ix_cash_flow_forecasts_id'), table_name='cash_flow_forecasts')
    op.drop_index(op.f('ix_cash_flow_forecasts_forecast_date'), table_name='cash_flow_forecasts')
    op.drop_table('cash_flow_forecasts')
    
    op.drop_index(op.f('ix_goal_milestones_id'), table_name='goal_milestones')
    op.drop_index(op.f('ix_goal_milestones_goal_id'), table_name='goal_milestones')
    op.drop_table('goal_milestones')
    
    op.drop_index(op.f('ix_financial_goals_user_id'), table_name='financial_goals')
    op.drop_index(op.f('ix_financial_goals_id'), table_name='financial_goals')
    op.drop_table('financial_goals')
    
    op.drop_index(op.f('ix_budget_categories_id'), table_name='budget_categories')
    op.drop_index(op.f('ix_budget_categories_category_id'), table_name='budget_categories')
    op.drop_index(op.f('ix_budget_categories_budget_id'), table_name='budget_categories')
    op.drop_table('budget_categories')
    
    op.drop_index(op.f('ix_budgets_user_id'), table_name='budgets')
    op.drop_index(op.f('ix_budgets_id'), table_name='budgets')
    op.drop_table('budgets')

    # Drop enum types
    postgresql.ENUM(name='alertstatus').drop(op.get_bind())
    postgresql.ENUM(name='alerttype').drop(op.get_bind())
    postgresql.ENUM(name='goalstatus').drop(op.get_bind())
    postgresql.ENUM(name='goaltype').drop(op.get_bind())
    postgresql.ENUM(name='budgetstatus').drop(op.get_bind())
    postgresql.ENUM(name='budgetperiod').drop(op.get_bind())