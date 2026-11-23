from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.event_broker import RadarEvent, evaluate_severity, event_broker
from app.models.threat import RadarStation, ThreatSignal
from app.models.user import User, UserRole
from app.schemas.threat import (
    RadarCreate,
    RadarOut,
    SignalIngestAccepted,
    ThreatCreate,
    ThreatOut,
    ThreatUpdate,
)

router = APIRouter(prefix="/api/v1", tags=["Space Threats & Radar EDA"])


def _ensure_owner_or_admin(owner_id: int, current_user: User) -> None:
    """Prevent horizontal privilege escalation (IDOR) on domain entities."""
    if current_user.role != UserRole.ADMIN.value and owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify your own radar stations or threat reports",
        )


@router.post("/radars", response_model=RadarOut, status_code=status.HTTP_201_CREATED)
def register_radar(
    payload: RadarCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RadarStation:
    """Register a new radar station owned by the current operator."""
    existing = db.query(RadarStation).filter(RadarStation.code == payload.code).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Radar station with this code already exists",
        )

    radar = RadarStation(
        code=payload.code,
        name=payload.name,
        region=payload.region,
        owner_id=current_user.id,
    )
    db.add(radar)
    db.commit()
    db.refresh(radar)
    return radar


@router.get("/radars", response_model=list[RadarOut])
def list_radars(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RadarStation]:
    """Return radar stations owned by current user (or all for admin)."""
    query = db.query(RadarStation)
    if current_user.role != UserRole.ADMIN.value:
        query = query.filter(RadarStation.owner_id == current_user.id)
    return query.order_by(RadarStation.id.desc()).all()


@router.post("/threats", response_model=ThreatOut, status_code=status.HTTP_201_CREATED)
def create_threat_signal(
    payload: ThreatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ThreatSignal:
    """Create a space threat record synchronously with automatic severity scoring."""
    severity = evaluate_severity(payload.distance_km, payload.velocity_kms)
    signal = ThreatSignal(
        object_code=payload.object_code,
        threat_type=payload.threat_type.value,
        severity=severity,
        distance_km=payload.distance_km,
        velocity_kms=payload.velocity_kms,
        azimuth=payload.azimuth,
        elevation=payload.elevation,
        description=payload.description,
        radar_station_id=payload.radar_station_id,
        owner_id=current_user.id,
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


@router.post(
    "/signals/ingest",
    response_model=SignalIngestAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_radar_signal_async(
    payload: ThreatCreate,
    current_user: User = Depends(get_current_user),
) -> SignalIngestAccepted:
    """EDA ingestion endpoint accepting peak bursts of asynchronous radar signals."""
    event = RadarEvent(
        object_code=payload.object_code,
        threat_type=payload.threat_type.value,
        distance_km=payload.distance_km,
        velocity_kms=payload.velocity_kms,
        azimuth=payload.azimuth,
        elevation=payload.elevation,
        description=payload.description,
        radar_station_id=payload.radar_station_id,
        owner_id=current_user.id,
    )
    qsize = await event_broker.publish(event)
    return SignalIngestAccepted(
        status="accepted",
        object_code=payload.object_code,
        queued_messages=qsize,
        server_id=get_settings().INSTANCE_NAME,
    )


@router.get("/threats", response_model=list[ThreatOut])
def list_threats(
    severity: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ThreatSignal]:
    """List space threats with optional severity filtering."""
    query = db.query(ThreatSignal)
    if severity:
        query = query.filter(ThreatSignal.severity == severity)
    return query.order_by(ThreatSignal.id.desc()).limit(limit).all()


@router.get("/threats/{threat_id}", response_model=ThreatOut)
def get_threat(
    threat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ThreatSignal:
    """Retrieve detailed information about a single threat signal."""
    signal = db.query(ThreatSignal).filter(ThreatSignal.id == threat_id).first()
    if signal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Threat signal not found")
    return signal


@router.patch("/threats/{threat_id}", response_model=ThreatOut)
def update_threat(
    threat_id: int,
    payload: ThreatUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ThreatSignal:
    """Update a threat signal (owner or admin only — IDOR protected)."""
    signal = db.query(ThreatSignal).filter(ThreatSignal.id == threat_id).first()
    if signal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Threat signal not found")
    _ensure_owner_or_admin(signal.owner_id, current_user)

    if payload.description is not None:
        signal.description = payload.description
    if payload.distance_km is not None:
        signal.distance_km = payload.distance_km
    if payload.velocity_kms is not None:
        signal.velocity_kms = payload.velocity_kms
    if payload.severity is not None:
        signal.severity = payload.severity.value

    db.commit()
    db.refresh(signal)
    return signal


@router.delete("/threats/{threat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_threat(
    threat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a threat signal (owner or admin only — IDOR protected)."""
    signal = db.query(ThreatSignal).filter(ThreatSignal.id == threat_id).first()
    if signal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Threat signal not found")
    _ensure_owner_or_admin(signal.owner_id, current_user)
    db.delete(signal)
    db.commit()
