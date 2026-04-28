"""Fit4Academy REST API v1.

This blueprint exposes JSON endpoints used by the mobile app (Expo / React Native)
and any external integrators. The Flask web admin (Jinja templates) keeps its
session-based auth — these endpoints use JWT bearer tokens instead.
"""

from flask import Blueprint

api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# Import sub-modules so their routes attach to the blueprint
from . import auth       # noqa: F401, E402
from . import me         # noqa: F401, E402
from . import member     # noqa: F401, E402
from . import staff      # noqa: F401, E402
from . import leads      # noqa: F401, E402
