"""
Role-Based Access Control (RBAC) models.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, Table, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from ..db.database import Base


# Association table for many-to-many relationship between users and roles
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True),
    Column('assigned_at', DateTime(timezone=True), server_default=func.now()),
    Column('assigned_by', UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
)

# Association table for many-to-many relationship between roles and permissions
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('permissions.id'), primary_key=True),
    Column('granted_at', DateTime(timezone=True), server_default=func.now()),
    Column('granted_by', UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
)


class Role(Base):
    """User roles for access control."""
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Role details
    name = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Role properties
    is_system_role = Column(Boolean, default=False, nullable=False)  # System roles can't be deleted
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Hierarchy
    parent_role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    parent_role = relationship("Role", remote_side=[id], backref="child_roles")

    def __repr__(self):
        return f"<Role(id={self.id}, name={self.name})>"


class Permission(Base):
    """Permissions that can be granted to roles."""
    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Permission details
    name = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Permission categorization
    resource = Column(String, nullable=False, index=True)  # e.g., "transaction", "account", "user"
    action = Column(String, nullable=False, index=True)    # e.g., "create", "read", "update", "delete"
    
    # Permission properties
    is_system_permission = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

    def __repr__(self):
        return f"<Permission(id={self.id}, name={self.name})>"


class UserPermission(Base):
    """Direct user permissions (overrides role permissions)."""
    __tablename__ = "user_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("permissions.id"), nullable=False, index=True)
    
    # Permission type
    permission_type = Column(String, nullable=False)  # "grant" or "deny"
    
    # Context (optional - for resource-specific permissions)
    resource_id = Column(String, nullable=True)  # Specific resource ID
    
    # Timestamps
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    permission = relationship("Permission")
    granted_by_user = relationship("User", foreign_keys=[granted_by])

    def __repr__(self):
        return f"<UserPermission(id={self.id}, user_id={self.user_id}, permission_type={self.permission_type})>"


class AccessLog(Base):
    """Log of access control decisions for auditing."""
    __tablename__ = "access_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Access details
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    resource = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False, index=True)
    resource_id = Column(String, nullable=True)
    
    # Decision
    access_granted = Column(Boolean, nullable=False)
    reason = Column(Text, nullable=True)  # Why access was granted/denied
    
    # Request context
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    endpoint = Column(String, nullable=True)
    
    # Timestamps
    accessed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<AccessLog(id={self.id}, user_id={self.user_id}, access_granted={self.access_granted})>"