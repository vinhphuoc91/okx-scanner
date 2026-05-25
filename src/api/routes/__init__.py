"""FastAPI route modules.

Each submodule exposes a ``router: APIRouter`` that is mounted by
:func:`src.api.app.create_app`.
"""

from src.api.routes import health

__all__ = ["health"]
