"""Model package — import all models so Alembic and Base.metadata see them."""

from app.models.tenant import Tenant  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.camera import Camera  # noqa: F401
from app.models.case import Case  # noqa: F401
from app.models.scan import Scan  # noqa: F401
