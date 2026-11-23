from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.config import get_settings
from app.core.database import get_db
from app.core.event_broker import event_broker
from app.models.threat import RadarStation, ThreatSeverity, ThreatSignal
from app.models.user import User
from app.schemas.threat import ThreatOut, ThreatStatusUpdate
from app.schemas.user import UserOut

router = APIRouter(prefix="/api/v1/admin", tags=["Admin Command Center"])


@router.get("/overview")
def admin_system_overview(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
) -> dict:
    """Return global metrics across users, radar stations, threats, and EDA broker."""
    total_users = db.query(User).count()
    total_radars = db.query(RadarStation).count()
    total_threats = db.query(ThreatSignal).count()
    critical_threats = (
        db.query(ThreatSignal)
        .filter(ThreatSignal.severity == ThreatSeverity.CRITICAL.value)
        .count()
    )
    return {
        "administrator": admin_user.username,
        "server_id": get_settings().INSTANCE_NAME,
        "environment": get_settings().APP_ENV,
        "metrics": {
            "total_users": total_users,
            "total_radars": total_radars,
            "total_threats": total_threats,
            "critical_threats": critical_threats,
        },
        "event_broker": event_broker.stats(),
    }


@router.get("/users", response_model=list[UserOut])
def list_all_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[User]:
    """List all registered system accounts (admin only)."""
    return db.query(User).order_by(User.id.asc()).all()


@router.patch("/threats/{threat_id}/status", response_model=ThreatOut)
def update_threat_status(
    threat_id: int,
    payload: ThreatStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> ThreatSignal:
    """Verify a threat signal or broadcast a planetary alert (admin only)."""
    signal = db.query(ThreatSignal).filter(ThreatSignal.id == threat_id).first()
    if signal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Threat signal not found")
    signal.status = payload.status.value
    db.commit()
    db.refresh(signal)
    return signal
