"""Add KRA e-filing tables

Revision ID: add_kra_efiling_tables
Revises: add_kra_tax_tables
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_kra_efiling_tables'
down_revision = 'add_kra_tax_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create KRA Tax Amendment table
    op.create_table('kra_tax_amendments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('original_filing_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amendment_reference', sa.String(length=50), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('original_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('amended_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('changes_summary', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('submission_date', sa.DateTime(), nullable=True),
        sa.Column('processing_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['original_filing_id'], ['kra_tax_filings.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('amendment_reference')
    )
    op.create_index(op.f('ix_kra_tax_amendments_original_filing_id'), 'kra_tax_amendments', ['original_filing_id'], unique=False)
    op.create_index(op.f('ix_kra_tax_amendments_user_id'), 'kra_tax_amendments', ['user_id'], unique=False)
    op.create_index(op.f('ix_kra_tax_amendments_status'), 'kra_tax_amendments', ['status'], unique=False)

    # Create KRA Tax Document table
    op.create_table('kra_tax_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filing_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('kra_document_id', sa.String(length=50), nullable=True),
        sa.Column('upload_date', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('verification_status', sa.String(length=20), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['filing_id'], ['kra_tax_filings.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kra_tax_documents_filing_id'), 'kra_tax_documents', ['filing_id'], unique=False)
    op.create_index(op.f('ix_kra_tax_documents_user_id'), 'kra_tax_documents', ['user_id'], unique=False)
    op.create_index(op.f('ix_kra_tax_documents_document_type'), 'kra_tax_documents', ['document_type'], unique=False)
    op.create_index(op.f('ix_kra_tax_documents_verification_status'), 'kra_tax_documents', ['verification_status'], unique=False)

    # Create KRA Filing Validation table
    op.create_table('kra_filing_validations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filing_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('validation_id', sa.String(length=50), nullable=True),
        sa.Column('is_valid', sa.Boolean(), nullable=False),
        sa.Column('errors', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('warnings', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('validation_date', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['filing_id'], ['kra_tax_filings.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kra_filing_validations_filing_id'), 'kra_filing_validations', ['filing_id'], unique=False)
    op.create_index(op.f('ix_kra_filing_validations_is_valid'), 'kra_filing_validations', ['is_valid'], unique=False)
    op.create_index(op.f('ix_kra_filing_validations_validation_date'), 'kra_filing_validations', ['validation_date'], unique=False)


def downgrade():
    # Drop tables in reverse order
    op.drop_table('kra_filing_validations')
    op.drop_table('kra_tax_documents')
    op.drop_table('kra_tax_amendments')