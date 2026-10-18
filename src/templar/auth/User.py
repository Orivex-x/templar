"""User model and authentication utilities."""

import json
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime

from templar.db.Models import Model

sys.dont_write_bytecode = True


class User(Model):
    """
    Base User model for authentication.
    
    Extend this class to add custom fields.
    """
    
    _table = "users"
    _fields = {
        "id": int,
        "username": str,
        "email": str,
        "password_hash": str,
        "is_active": bool,
        "roles": str,  # JSON list stored as string
        "permissions": str,  # JSON list stored as string
        "created_at": str,
        "updated_at": str,
        "last_login": str,
    }
    __unique_fields__ = ("username", "email")
    __required_fields__ = (
        "username", "email", "password_hash", "is_active", "roles",
        "permissions", "created_at", "updated_at",
    )
    
    def __init__(
        self,
        username: str,
        email: str,
        password_hash: str,
        is_active: bool = True,
        roles: Optional[List[str] | str] = None,
        permissions: Optional[List[str] | str] = None,
        **kwargs
    ):
        """
        Initialize User.
        
        Args:
            username: Unique username
            email: User's email address
            password_hash: Hashed password
            is_active: Whether a user account is active
            roles: List of roles
            permissions: List of permissions
        """
        super().__init__(**kwargs)
        
        self.username = self._required_text(username, "username")
        self.email = self._required_text(email, "email")
        self.password_hash = self._required_text(password_hash, "password_hash")
        self.is_active = self._activity_flag(is_active)
        self.roles = self._membership_list(roles, "roles")
        self.permissions = self._membership_list(permissions, "permissions")

        now = datetime.now().isoformat()

        # QuerySet passes persisted timestamp fields through ``kwargs``. Do not turn a read into a silent timestamp
        # rewrite on the next save.
        self.created_at = kwargs.get("created_at") or now
        self.updated_at = kwargs.get("updated_at") or now
        self.last_login = kwargs.get("last_login")

    @staticmethod
    def _membership_list(value: Optional[List[str] | str], label: str) -> List[str]:
        if value is None:
            return []

        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Stored user {label} must be a JSON list") from exc

        if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
            raise TypeError(f"User {label} must be a list of strings")

        return list(value)

    @staticmethod
    def _required_text(value: Any, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"User {label} must be a non-empty string")

        return value

    @staticmethod
    def _activity_flag(value: Any) -> bool:
        """Normalize persisted activity values without truthiness coercion."""
        if isinstance(value, bool):
            return value

        if isinstance(value, int) and value in (0, 1):
            return bool(value)

        if isinstance(value, str):
            normalized = value.strip().lower()

            if normalized in {"true", "1"}:
                return True

            if normalized in {"false", "0"}:
                return False

        raise ValueError("User is_active must be a boolean or 0/1 value")
    
    @classmethod
    def get_by_username(cls, username: str) -> Optional["User"]:
        """
        Get user by username.
        
        Args:
            username: Username to search for
            
        Returns:
            User instance or None
        """
        return cls.objects().filter(username=username).first()
    
    @classmethod
    def get_by_email(cls, email: str) -> Optional["User"]:
        """
        Get user by email.
        
        Args:
            email: Email to search for
            
        Returns:
            User instance or None
        """
        return cls.objects().filter(email=email).first()
    
    def has_role(self, role: str) -> bool:
        """Check if a user has a specific role."""
        return role in self.roles
    
    def has_permission(self, permission: str) -> bool:
        """Check if the user has a specific permission."""
        return permission in self.permissions
    
    def add_role(self, role: str) -> None:
        """Add a role to the user."""
        if role not in self.roles:
            self.roles.append(role)
            self.updated_at = datetime.now().isoformat()
    
    def remove_role(self, role: str) -> None:
        """Remove a role from the user."""
        if role in self.roles:
            self.roles.remove(role)
            self.updated_at = datetime.now().isoformat()
    
    def add_permission(self, permission: str) -> None:
        """Add a permission to user."""
        if permission not in self.permissions:
            self.permissions.append(permission)
            self.updated_at = datetime.now().isoformat()
    
    def remove_permission(self, permission: str) -> None:
        """Remove a permission from user."""
        if permission in self.permissions:
            self.permissions.remove(permission)
            self.updated_at = datetime.now().isoformat()
    
    def update_last_login(self) -> None:
        """Update last login timestamp."""
        self.last_login = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

    def save(self) -> None:
        """Persist the user and refresh its modification timestamp on updates."""
        if getattr(self, "id", None) is not None:
            self.updated_at = datetime.now().isoformat()

        super().save()
    
    def to_record(self) -> Dict[str, Any]:
        """Serialize membership lists for the database without redacting secrets."""
        self.username = self._required_text(self.username, "username")
        self.email = self._required_text(self.email, "email")
        self.password_hash = self._required_text(self.password_hash, "password_hash")
        self.is_active = self._activity_flag(self.is_active)
        self.roles = self._membership_list(self.roles, "roles")
        self.permissions = self._membership_list(self.permissions, "permissions")

        data = super().to_record()
        data["roles"] = json.dumps(self.roles, separators=(",", ":"))
        data["permissions"] = json.dumps(self.permissions, separators=(",", ":"))

        return data

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary (excluding password hash)."""
        data = super().to_record()
        data.pop("password_hash", None)
        data["roles"] = list(self.roles)
        data["permissions"] = list(self.permissions)

        return data
