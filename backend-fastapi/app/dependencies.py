"""
Backwards-compatible re-export of the real auth dependencies.

Previously defined a placeholder user with a hardcoded UUID; identity now
comes from a verified token. See app/auth.py.
"""

from app.auth import User, get_current_user, get_current_user_id

__all__ = ["User", "get_current_user", "get_current_user_id"]
