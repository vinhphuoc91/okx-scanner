"""Application configuration package.

Exposes a single ``settings`` singleton built from environment variables and
.env files via :class:`config.settings.Settings`.

Usage::

    from config import settings
    print(settings.api_port)
"""

from config.settings import Settings, get_settings, settings

__all__ = ["Settings", "get_settings", "settings"]
