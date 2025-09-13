"""
Role-Based Access Control (RBAC) service.
"""
from typing import List, Optional, Dict, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_
from datetime import datetime
import logging

from ..models.rbac import Role, Permission, UserPermission, AccessLog, user_roles, role_permissions
from ..models.user import User
from ..core.config import settings


logger = logging.getLogger(__name__)


class RBACService:
    """Service for managing Role-Based Access Control."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # Role Management
    def create_role(
        self,
        name: str,
        display_name: str,
        description: Optional[str] = None,
        parent_role_id: Optional[str] = None,
        is_system_role: bool = False
    ) -> Optional[Role]:
        """Create a new role."""
        try:
            role = Role(
                name=name,
                display_name=display_name,
                description=description,
                parent_role_id=parent_role_id,
                is_system_role=is_system_role
            )
            
            self.db.add(role)
            self.db.commit()
            self.db.refresh(role)
            
            return role
            
        except SQLAlchemyError as e:
            logger.error(f"Error creating role: {e}")
            self.db.rollback()
            return None
    
    def get_role(self, role_id: str) -> Optional[Role]:
        """Get role by ID."""
        return self.db.query(Role).filter(Role.id == role_id).first()
    
    def get_role_by_name(self, name: str) -> Optional[Role]:
        """Get role by name."""
        return self.db.query(Role).filter(Role.name == name).first()
    
    def get_all_roles(self, include_inactive: bool = False) -> List[Role]:
        """Get all roles."""
        query = self.db.query(Role)
        if not include_inactive:
            query = query.filter(Role.is_active == True)
        return query.all()
    
    def update_role(
        self,
        role_id: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Role]:
        """Update role details."""
        try:
            role = self.get_role(role_id)
            if not role:
                return None
            
            if display_name is not None:
                role.display_name = display_name
            if description is not None:
                role.description = description
            if is_active is not None:
                role.is_active = is_active
            
            self.db.commit()
            self.db.refresh(role)
            
            return role
            
        except SQLAlchemyError as e:
            logger.error(f"Error updating role: {e}")
            self.db.rollback()
            return None
    
    def delete_role(self, role_id: str) -> bool:
        """Delete a role (only if not system role and no users assigned)."""
        try:
            role = self.get_role(role_id)
            if not role:
                return False
            
            if role.is_system_role:
                logger.warning(f"Cannot delete system role: {role.name}")
                return False
            
            # Check if role has users
            user_count = self.db.query(user_roles).filter(
                user_roles.c.role_id == role_id
            ).count()
            
            if user_count > 0:
                logger.warning(f"Cannot delete role with assigned users: {role.name}")
                return False
            
            self.db.delete(role)
            self.db.commit()
            
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Error deleting role: {e}")
            self.db.rollback()
            return False
    
    # Permission Management
    def create_permission(
        self,
        name: str,
        display_name: str,
        resource: str,
        action: str,
        description: Optional[str] = None,
        is_system_permission: bool = False
    ) -> Optional[Permission]:
        """Create a new permission."""
        try:
            permission = Permission(
                name=name,
                display_name=display_name,
                description=description,
                resource=resource,
                action=action,
                is_system_permission=is_system_permission
            )
            
            self.db.add(permission)
            self.db.commit()
            self.db.refresh(permission)
            
            return permission
            
        except SQLAlchemyError as e:
            logger.error(f"Error creating permission: {e}")
            self.db.rollback()
            return None
    
    def get_permission(self, permission_id: str) -> Optional[Permission]:
        """Get permission by ID."""
        return self.db.query(Permission).filter(Permission.id == permission_id).first()
    
    def get_permission_by_name(self, name: str) -> Optional[Permission]:
        """Get permission by name."""
        return self.db.query(Permission).filter(Permission.name == name).first()
    
    def get_permissions_by_resource_action(self, resource: str, action: str) -> List[Permission]:
        """Get permissions by resource and action."""
        return self.db.query(Permission).filter(
            Permission.resource == resource,
            Permission.action == action,
            Permission.is_active == True
        ).all()
    
    def get_all_permissions(self, include_inactive: bool = False) -> List[Permission]:
        """Get all permissions."""
        query = self.db.query(Permission)
        if not include_inactive:
            query = query.filter(Permission.is_active == True)
        return query.all()
    
    # Role-Permission Management
    def assign_permission_to_role(self, role_id: str, permission_id: str) -> bool:
        """Assign permission to role."""
        try:
            # Check if assignment already exists
            existing = self.db.query(role_permissions).filter(
                role_permissions.c.role_id == role_id,
                role_permissions.c.permission_id == permission_id
            ).first()
            
            if existing:
                return True  # Already assigned
            
            # Create assignment
            stmt = role_permissions.insert().values(
                role_id=role_id,
                permission_id=permission_id
            )
            self.db.execute(stmt)
            self.db.commit()
            
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Error assigning permission to role: {e}")
            self.db.rollback()
            return False
    
    def remove_permission_from_role(self, role_id: str, permission_id: str) -> bool:
        """Remove permission from role."""
        try:
            stmt = role_permissions.delete().where(
                and_(
                    role_permissions.c.role_id == role_id,
                    role_permissions.c.permission_id == permission_id
                )
            )
            result = self.db.execute(stmt)
            self.db.commit()
            
            return result.rowcount > 0
            
        except SQLAlchemyError as e:
            logger.error(f"Error removing permission from role: {e}")
            self.db.rollback()
            return False
    
    def get_role_permissions(self, role_id: str) -> List[Permission]:
        """Get all permissions for a role."""
        return self.db.query(Permission).join(role_permissions).filter(
            role_permissions.c.role_id == role_id,
            Permission.is_active == True
        ).all()
    
    # User-Role Management
    def assign_role_to_user(self, user_id: str, role_id: str, assigned_by: Optional[str] = None) -> bool:
        """Assign role to user."""
        try:
            # Check if assignment already exists
            existing = self.db.query(user_roles).filter(
                user_roles.c.user_id == user_id,
                user_roles.c.role_id == role_id
            ).first()
            
            if existing:
                return True  # Already assigned
            
            # Create assignment
            stmt = user_roles.insert().values(
                user_id=user_id,
                role_id=role_id,
                assigned_by=assigned_by
            )
            self.db.execute(stmt)
            self.db.commit()
            
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Error assigning role to user: {e}")
            self.db.rollback()
            return False
    
    def remove_role_from_user(self, user_id: str, role_id: str) -> bool:
        """Remove role from user."""
        try:
            stmt = user_roles.delete().where(
                and_(
                    user_roles.c.user_id == user_id,
                    user_roles.c.role_id == role_id
                )
            )
            result = self.db.execute(stmt)
            self.db.commit()
            
            return result.rowcount > 0
            
        except SQLAlchemyError as e:
            logger.error(f"Error removing role from user: {e}")
            self.db.rollback()
            return False
    
    def get_user_roles(self, user_id: str) -> List[Role]:
        """Get all roles for a user."""
        return self.db.query(Role).join(user_roles).filter(
            user_roles.c.user_id == user_id,
            Role.is_active == True
        ).all()
    
    # User Permission Management
    def grant_user_permission(
        self,
        user_id: str,
        permission_id: str,
        granted_by: Optional[str] = None,
        resource_id: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> Optional[UserPermission]:
        """Grant direct permission to user."""
        try:
            user_permission = UserPermission(
                user_id=user_id,
                permission_id=permission_id,
                permission_type="grant",
                resource_id=resource_id,
                granted_by=granted_by,
                expires_at=expires_at
            )
            
            self.db.add(user_permission)
            self.db.commit()
            self.db.refresh(user_permission)
            
            return user_permission
            
        except SQLAlchemyError as e:
            logger.error(f"Error granting user permission: {e}")
            self.db.rollback()
            return None
    
    def deny_user_permission(
        self,
        user_id: str,
        permission_id: str,
        granted_by: Optional[str] = None,
        resource_id: Optional[str] = None
    ) -> Optional[UserPermission]:
        """Deny permission to user (overrides role permissions)."""
        try:
            user_permission = UserPermission(
                user_id=user_id,
                permission_id=permission_id,
                permission_type="deny",
                resource_id=resource_id,
                granted_by=granted_by
            )
            
            self.db.add(user_permission)
            self.db.commit()
            self.db.refresh(user_permission)
            
            return user_permission
            
        except SQLAlchemyError as e:
            logger.error(f"Error denying user permission: {e}")
            self.db.rollback()
            return None
    
    def revoke_user_permission(self, user_permission_id: str) -> bool:
        """Revoke direct user permission."""
        try:
            user_permission = self.db.query(UserPermission).filter(
                UserPermission.id == user_permission_id
            ).first()
            
            if not user_permission:
                return False
            
            self.db.delete(user_permission)
            self.db.commit()
            
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Error revoking user permission: {e}")
            self.db.rollback()
            return False
    
    # Access Control
    def check_permission(
        self,
        user_id: str,
        resource: str,
        action: str,
        resource_id: Optional[str] = None,
        log_access: bool = True
    ) -> bool:
        """
        Check if user has permission to perform action on resource.
        
        Args:
            user_id: User ID
            resource: Resource type (e.g., "transaction", "account")
            action: Action type (e.g., "create", "read", "update", "delete")
            resource_id: Specific resource ID (optional)
            log_access: Whether to log the access attempt
        
        Returns:
            True if access granted, False otherwise
        """
        try:
            # Get user
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or not user.is_active:
                if log_access:
                    self._log_access(user_id, resource, action, resource_id, False, "User not found or inactive")
                return False
            
            # Check direct user permissions first (they override role permissions)
            user_permission = self._check_user_permission(user_id, resource, action, resource_id)
            if user_permission is not None:
                if log_access:
                    reason = f"Direct user permission: {user_permission}"
                    self._log_access(user_id, resource, action, resource_id, user_permission, reason)
                return user_permission
            
            # Check role-based permissions
            role_permission = self._check_role_permissions(user_id, resource, action)
            
            if log_access:
                reason = "Role-based permission" if role_permission else "No matching permissions found"
                self._log_access(user_id, resource, action, resource_id, role_permission, reason)
            
            return role_permission
            
        except Exception as e:
            logger.error(f"Error checking permission: {e}")
            if log_access:
                self._log_access(user_id, resource, action, resource_id, False, f"Error: {str(e)}")
            return False
    
    def _check_user_permission(
        self,
        user_id: str,
        resource: str,
        action: str,
        resource_id: Optional[str] = None
    ) -> Optional[bool]:
        """Check direct user permissions."""
        # Get permissions for the resource and action
        permissions = self.db.query(Permission).filter(
            Permission.resource == resource,
            Permission.action == action,
            Permission.is_active == True
        ).all()
        
        if not permissions:
            return None
        
        permission_ids = [str(p.id) for p in permissions]
        
        # Check user permissions
        user_permissions = self.db.query(UserPermission).filter(
            UserPermission.user_id == user_id,
            UserPermission.permission_id.in_(permission_ids),
            or_(
                UserPermission.expires_at.is_(None),
                UserPermission.expires_at > datetime.utcnow()
            )
        ).all()
        
        # Filter by resource_id if specified
        if resource_id:
            user_permissions = [
                up for up in user_permissions
                if up.resource_id is None or up.resource_id == resource_id
            ]
        
        # Check for explicit deny first
        for up in user_permissions:
            if up.permission_type == "deny":
                return False
        
        # Check for explicit grant
        for up in user_permissions:
            if up.permission_type == "grant":
                return True
        
        return None  # No direct user permission found
    
    def _check_role_permissions(self, user_id: str, resource: str, action: str) -> bool:
        """Check role-based permissions."""
        # Get user roles
        user_roles_query = self.db.query(Role).join(user_roles).filter(
            user_roles.c.user_id == user_id,
            Role.is_active == True
        )
        
        roles = user_roles_query.all()
        if not roles:
            return False
        
        role_ids = [str(r.id) for r in roles]
        
        # Get permissions for the resource and action
        permissions = self.db.query(Permission).filter(
            Permission.resource == resource,
            Permission.action == action,
            Permission.is_active == True
        ).all()
        
        if not permissions:
            return False
        
        permission_ids = [str(p.id) for p in permissions]
        
        # Check if any role has the required permission
        role_permission_count = self.db.query(role_permissions).filter(
            role_permissions.c.role_id.in_(role_ids),
            role_permissions.c.permission_id.in_(permission_ids)
        ).count()
        
        return role_permission_count > 0
    
    def get_user_permissions(self, user_id: str) -> Set[str]:
        """Get all effective permissions for a user."""
        permissions = set()
        
        # Get role-based permissions
        user_roles_query = self.db.query(Role).join(user_roles).filter(
            user_roles.c.user_id == user_id,
            Role.is_active == True
        )
        
        for role in user_roles_query.all():
            role_permissions_query = self.db.query(Permission).join(role_permissions).filter(
                role_permissions.c.role_id == role.id,
                Permission.is_active == True
            )
            
            for permission in role_permissions_query.all():
                permissions.add(f"{permission.resource}:{permission.action}")
        
        # Apply direct user permissions
        user_permissions = self.db.query(UserPermission).join(Permission).filter(
            UserPermission.user_id == user_id,
            Permission.is_active == True,
            or_(
                UserPermission.expires_at.is_(None),
                UserPermission.expires_at > datetime.utcnow()
            )
        ).all()
        
        for up in user_permissions:
            permission_key = f"{up.permission.resource}:{up.permission.action}"
            if up.permission_type == "grant":
                permissions.add(permission_key)
            elif up.permission_type == "deny":
                permissions.discard(permission_key)
        
        return permissions
    
    def _log_access(
        self,
        user_id: str,
        resource: str,
        action: str,
        resource_id: Optional[str],
        access_granted: bool,
        reason: str
    ):
        """Log access control decision."""
        try:
            access_log = AccessLog(
                user_id=user_id,
                resource=resource,
                action=action,
                resource_id=resource_id,
                access_granted=access_granted,
                reason=reason
            )
            
            self.db.add(access_log)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error logging access: {e}")
            # Don't raise exception as this is just logging
    
    # System Initialization
    def initialize_default_roles_and_permissions(self):
        """Initialize default roles and permissions for the system."""
        try:
            # Create default permissions
            default_permissions = [
                # User management
                ("user:create", "Create User", "user", "create"),
                ("user:read", "Read User", "user", "read"),
                ("user:update", "Update User", "user", "update"),
                ("user:delete", "Delete User", "user", "delete"),
                
                # Account management
                ("account:create", "Create Account", "account", "create"),
                ("account:read", "Read Account", "account", "read"),
                ("account:update", "Update Account", "account", "update"),
                ("account:delete", "Delete Account", "account", "delete"),
                
                # Transaction management
                ("transaction:create", "Create Transaction", "transaction", "create"),
                ("transaction:read", "Read Transaction", "transaction", "read"),
                ("transaction:update", "Update Transaction", "transaction", "update"),
                ("transaction:delete", "Delete Transaction", "transaction", "delete"),
                ("transaction:import", "Import Transactions", "transaction", "import"),
                
                # Category management
                ("category:create", "Create Category", "category", "create"),
                ("category:read", "Read Category", "category", "read"),
                ("category:update", "Update Category", "category", "update"),
                ("category:delete", "Delete Category", "category", "delete"),
                
                # Report access
                ("report:generate", "Generate Reports", "report", "generate"),
                ("report:export", "Export Reports", "report", "export"),
                
                # Tax management
                ("tax:file", "File Tax Returns", "tax", "file"),
                ("tax:read", "Read Tax Data", "tax", "read"),
                
                # Business features
                ("business:create", "Create Business Entity", "business", "create"),
                ("business:read", "Read Business Data", "business", "read"),
                ("business:update", "Update Business Data", "business", "update"),
                
                # System administration
                ("system:admin", "System Administration", "system", "admin"),
                ("system:audit", "View Audit Logs", "system", "audit"),
            ]
            
            for name, display_name, resource, action in default_permissions:
                if not self.get_permission_by_name(name):
                    self.create_permission(
                        name=name,
                        display_name=display_name,
                        resource=resource,
                        action=action,
                        is_system_permission=True
                    )
            
            # Create default roles
            default_roles = [
                ("admin", "Administrator", "Full system access"),
                ("user", "Regular User", "Standard user access"),
                ("business_user", "Business User", "Business features access"),
                ("readonly", "Read Only", "Read-only access"),
            ]
            
            for name, display_name, description in default_roles:
                if not self.get_role_by_name(name):
                    self.create_role(
                        name=name,
                        display_name=display_name,
                        description=description,
                        is_system_role=True
                    )
            
            # Assign permissions to roles
            self._assign_default_role_permissions()
            
            self.db.commit()
            logger.info("Default roles and permissions initialized")
            
        except Exception as e:
            logger.error(f"Error initializing default roles and permissions: {e}")
            self.db.rollback()
    
    def _assign_default_role_permissions(self):
        """Assign default permissions to roles."""
        # Admin role - all permissions
        admin_role = self.get_role_by_name("admin")
        if admin_role:
            all_permissions = self.get_all_permissions()
            for permission in all_permissions:
                self.assign_permission_to_role(str(admin_role.id), str(permission.id))
        
        # Regular user role - basic permissions
        user_role = self.get_role_by_name("user")
        if user_role:
            user_permissions = [
                "account:create", "account:read", "account:update", "account:delete",
                "transaction:create", "transaction:read", "transaction:update", "transaction:delete", "transaction:import",
                "category:create", "category:read", "category:update", "category:delete",
                "report:generate", "report:export",
                "tax:file", "tax:read"
            ]
            for perm_name in user_permissions:
                permission = self.get_permission_by_name(perm_name)
                if permission:
                    self.assign_permission_to_role(str(user_role.id), str(permission.id))
        
        # Business user role - user permissions + business features
        business_role = self.get_role_by_name("business_user")
        if business_role:
            business_permissions = [
                "account:create", "account:read", "account:update", "account:delete",
                "transaction:create", "transaction:read", "transaction:update", "transaction:delete", "transaction:import",
                "category:create", "category:read", "category:update", "category:delete",
                "report:generate", "report:export",
                "tax:file", "tax:read",
                "business:create", "business:read", "business:update"
            ]
            for perm_name in business_permissions:
                permission = self.get_permission_by_name(perm_name)
                if permission:
                    self.assign_permission_to_role(str(business_role.id), str(permission.id))
        
        # Read-only role - only read permissions
        readonly_role = self.get_role_by_name("readonly")
        if readonly_role:
            readonly_permissions = [
                "account:read", "transaction:read", "category:read", "report:generate", "tax:read", "business:read"
            ]
            for perm_name in readonly_permissions:
                permission = self.get_permission_by_name(perm_name)
                if permission:
                    self.assign_permission_to_role(str(readonly_role.id), str(permission.id))