from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, require_admin
from app.core.config import get_settings
from app.models.user import User

router = APIRouter(prefix="/home", tags=["Role Dashboards"])


@router.get("/user")
def user_home_dashboard(current_user: User = Depends(get_current_user)) -> dict:
    """Stub home page for authenticated radar station operators."""
    return {
        "page": "Operator Home Dashboard",
        "message": f"Welcome, operator {current_user.username}!",
        "role": current_user.role,
        "available_actions": [
            "Register radar stations (/api/v1/radars)",
            "Submit & track cosmic threats (/api/v1/threats)",
            "Stream async radar telemetry (/api/v1/signals/ingest)",
        ],
        "server_id": get_settings().INSTANCE_NAME,
    }


@router.get("/admin")
def admin_home_dashboard(admin_user: User = Depends(require_admin)) -> dict:
    """Stub home page restricted exclusively to system administrators."""
    return {
        "page": "Space Defense Command Center (Admin)",
        "message": f"Welcome, administrator {admin_user.username}!",
        "role": admin_user.role,
        "available_actions": [
            "Inspect global EDA broker & threat metrics (/api/v1/admin/overview)",
            "Verify threats & broadcast planetary alerts (/api/v1/admin/threats/{id}/status)",
            "Manage registered operators (/api/v1/admin/users)",
        ],
        "server_id": get_settings().INSTANCE_NAME,
    }
