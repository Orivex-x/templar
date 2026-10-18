"""Authentication system for Templar."""

import sys
import hashlib
import hmac
import secrets
import json
from collections.abc import Mapping
from typing import Optional, Dict, Any

sys.dont_write_bytecode = True


class PasswordManager:
    """Password hashing and verification utilities. Uses PBKDF2-SHA256 for password hashing."""
    
    ALGORITHM = "pbkdf2_sha256"
    ITERATIONS = 260000  # OWASP recommended (as of 2024)
    MIN_ITERATIONS = 100_000
    MAX_ITERATIONS = 10_000_000
    
    @staticmethod
    def hash_password(
        password: str,
        salt: Optional[str] = None,
        iterations: Optional[int] = None,
    ) -> str:
        """
        Hash a password with PBKDF2-SHA256.
        
        Args:
            password: Plain text password
            salt: Optional salt (generates random if None)
            iterations: PBKDF2 work factor (uses the current policy if omitted)
            
        Returns:
            Formatted hash string: "algorithm$iterations$salt$hash"
        """
        if salt is None:
            salt = secrets.token_hex(32)

        iterations = PasswordManager.ITERATIONS if iterations is None else iterations

        if isinstance(iterations, bool) or not isinstance(iterations, int) or not PasswordManager.MIN_ITERATIONS <= iterations <= PasswordManager.MAX_ITERATIONS:
            raise ValueError(
                f"PBKDF2 iterations must be an integer between {PasswordManager.MIN_ITERATIONS} and {PasswordManager.MAX_ITERATIONS}"
            )
        
        hash_obj = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations
        )
        hash_hex = hash_obj.hex()
        
        return f"{PasswordManager.ALGORITHM}${iterations}${salt}${hash_hex}"
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password to verify
            hashed: Previously hashed password
            
        Returns:
            True if the password matches, False otherwise
        """
        try:
            parts = hashed.split("$")

            if len(parts) != 4:
                return False
            
            algorithm, iteration_text, salt, _ = parts
            
            if algorithm != PasswordManager.ALGORITHM:
                return False

            iterations = int(iteration_text)

            if not 0 < iterations <= PasswordManager.MAX_ITERATIONS:
                return False
            
            # Verify using the work factor stored alongside this hash. Do this directly instead of calling
            # ``hash_password``: new hashes must meet MIN_ITERATIONS, while safely bounded legacy hashes must remain
            # verifiable so users can upgrade on their next login.
            digest = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                iterations,
            ).hex()
            new_hash = f"{PasswordManager.ALGORITHM}${iterations}${salt}${digest}"
            
            # Use constant-time comparison to prevent timing attacks
            return hmac.compare_digest(hashed, new_hash)
        except Exception:
            return False


class Auth:
    """
    Central authentication manager for Templar.
    
    Handles login, logout, session management, and permission checks.
    """
    
    def __init__(self, secret_key: str):
        """
        Initialize authentication manager.
        
        Args:
            secret_key: Secret key for signing sessions
        """
        self.secret_key = secret_key
    
    def authenticate(
        self,
        username: str,
        password: str,
        user_loader,
        session: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Authenticate a user with a username and password.
        
        Args:
            username: User's username
            password: User's password
            user_loader: Callable that takes username and returns user dict or None
            
        Returns:
            True if authentication is successful, False otherwise
        """
        user = user_loader(username)
        
        if not user or not self._user_is_active(user):
            return False
        
        if not PasswordManager.verify_password(password, self._user_value(user, "password_hash", "")):
            return False
        
        if session is not None:
            user_id = self._user_value(user, "id")

            if user_id is None:
                return False

            session["user_id"] = user_id
            # The session middleware replaces the opaque ID after a successful login, preventing an attacker-supplied
            # pre-login ID from being retained by the authenticated user.
            session["_templar_rotate_session"] = True

        return True

    @staticmethod
    def _user_value(user: Any, key: str, default: Any = None) -> Any:
        if isinstance(user, Mapping):
            return user.get(key, default)

        return getattr(user, key, default)

    @classmethod
    def _user_is_active(cls, user: Any) -> bool:
        """Treat absent activity metadata as active but fail closed otherwise."""
        value = cls._user_value(user, "is_active", True)

        if isinstance(value, bool):
            return value

        if isinstance(value, int) and not isinstance(value, bool):
            return value == 1

        if isinstance(value, str):
            return value.strip().lower() in {"true", "1"}

        return False

    @staticmethod
    def normalize_claims(value: Any, label: str) -> list[str]:
        """Return only a valid list of authorization claim strings.

        Mapping-based loaders commonly expose SQL JSON columns as strings.
        Decode JSON arrays deliberately; never treat an arbitrary string as
        an iterable claim collection, because ``"not-admin"`` contains the
        substring ``"admin"``.
        """
        if value is None:
            return []

        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError(f"User {label} must be a JSON array or list of strings") from exc

        if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
            raise ValueError(f"User {label} must be a list of strings")

        return list(value)

    @classmethod
    def normalize_public_user(cls, user: Any, *, expected_id: Any = None) -> Dict[str, Any]:
        """Validate a loader result before it becomes request authentication.

        Loader mappings are an API boundary, so require an identity and give
        role/permission values one canonical list-of-strings representation.
        ``expected_id`` binds the returned user to the signed session value.
        """
        if not isinstance(user, Mapping):
            raise TypeError("A public user must be a mapping")

        normalized = dict(user)
        user_id = normalized.get("id")

        if isinstance(user_id, bool) or not isinstance(user_id, (int, str)) or (isinstance(user_id, str) and not user_id):
            raise ValueError("User loader results must include a non-empty string or integer id")

        if expected_id is not None and user_id != expected_id:
            raise ValueError("User loader result does not match the session user id")

        normalized["roles"] = cls.normalize_claims(normalized.get("roles"), "roles")
        normalized["permissions"] = cls.normalize_claims(normalized.get("permissions"), "permissions")
        normalized["is_active"] = cls._user_is_active(normalized)

        return normalized
    
    def get_current_user(self, context) -> Optional[Any]:
        """Get the user attached to the current request context."""
        return getattr(context, "user", None)
    
    def is_authenticated(self, context) -> bool:
        """Check if a user is currently authenticated."""
        return self.get_current_user(context) is not None
    
    def logout(self, session: Dict[str, Any]) -> None:
        """Log out the current user."""
        session.pop("user_id", None)
    
    def has_permission(self, context, permission: str) -> bool:
        """
        Check if the current user has a specific permission.
        
        Args:
            permission: Permission name
            
        Returns:
            True if the user has permission, False otherwise
        """
        user = self.get_current_user(context)
        if not user:
            return False
        
        try:
            user_permissions = self.normalize_claims(self._user_value(user, "permissions", []), "permissions")
        except ValueError:
            return False
        
        # Check direct permissions
        if permission in user_permissions:
            return True
        
        # Check role-based permissions (would be expanded with role system)
        return False
    
    def has_role(self, context, role: str) -> bool:
        """
        Check if the current user has a specific role.
        
        Args:
            role: Role name
            
        Returns:
            True if the user has a role, False otherwise
        """
        user = self.get_current_user(context)

        if not user:
            return False
        
        try:
            return role in self.normalize_claims(self._user_value(user, "roles", []), "roles")
        except ValueError:
            return False
