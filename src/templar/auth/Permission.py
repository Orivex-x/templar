"""Permission and authorization decorators."""

import sys
from functools import wraps
from collections.abc import Mapping
from typing import Callable, Any

from templar.auth import Auth
from templar.core.Exceptions import PermissionDeniedError, UnauthorizedError

sys.dont_write_bytecode = True


def _current_user(args, kwargs):
    """Resolve the request-scoped user, retaining legacy controller support."""
    candidates = [kwargs.get("request"), *args]

    for candidate in candidates:
        if candidate is None:
            continue

        user = getattr(candidate, "user", None)

        if user is not None:
            return user

        user = getattr(candidate, "current_user", None)

        if user is not None:
            return user

    return None


def _user_values(user: Any, key: str):
    value = user.get(key, []) if isinstance(user, Mapping) else getattr(user, key, [])

    try:
        return Auth.normalize_claims(value, key)
    except ValueError:
        return []


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication for a function.
    
    Usage:
        @require_auth
        def admin_only():
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not _current_user(args, kwargs):
            raise UnauthorizedError("Authentication required")
        
        return func(*args, **kwargs)
    
    return wrapper


def require_permission(*permissions: str) -> Callable:
    """
    Decorator to require specific permissions.
    
    Usage:
        @require_permission('admin', 'edit_posts')
        def moderate():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_user = _current_user(args, kwargs)

            if not current_user:
                raise UnauthorizedError("Authentication required")
            
            user_permissions = _user_values(current_user, "permissions")
            
            # Check if user has any of the required permissions
            if not any(p in user_permissions for p in permissions):
                raise PermissionDeniedError(
                    f"Required permissions: {', '.join(permissions)}"
                )
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def require_role(*roles: str) -> Callable:
    """
    Decorator to require specific roles.
    
    Usage:
        @require_role('admin', 'moderator')
        def admin_panel():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_user = _current_user(args, kwargs)

            if not current_user:
                raise UnauthorizedError("Authentication required")
            
            user_roles = _user_values(current_user, "roles")
            
            # Check if user has any of the required roles
            if not any(r in user_roles for r in roles):
                raise PermissionDeniedError(
                    f"Required roles: {', '.join(roles)}"
                )
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


class Permission:
    """Permission constants."""
    
    # User permissions
    VIEW_PROFILE = "user:view_profile"
    EDIT_PROFILE = "user:edit_profile"
    DELETE_ACCOUNT = "user:delete_account"
    
    # Post permissions
    CREATE_POST = "post:create"
    EDIT_POST = "post:edit"
    DELETE_POST = "post:delete"
    PUBLISH_POST = "post:publish"
    
    # Admin permissions
    MANAGE_USERS = "admin:manage_users"
    MANAGE_POSTS = "admin:manage_posts"
    MANAGE_SETTINGS = "admin:manage_settings"
    VIEW_LOGS = "admin:view_logs"
    
    # Common permission sets
    MODERATOR_PERMISSIONS = [
        EDIT_POST,
        DELETE_POST,
        PUBLISH_POST,
        VIEW_LOGS,
    ]
    
    ADMIN_PERMISSIONS = [
        MANAGE_USERS,
        MANAGE_POSTS,
        MANAGE_SETTINGS,
        VIEW_LOGS,
    ] + MODERATOR_PERMISSIONS


class Role:
    """Role constants."""
    
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    STAFF = "staff"
