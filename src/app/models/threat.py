from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ThreatType(StrEnum):
    ASTEROID = "asteroid"
    SPACE_DEBRIS = "space_debris"
    SOLAR_FLARE = "solar_flare"
    UNKNOWN = "unknown"


class ThreatSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    FALSE_ALARM = "false_alarm"
    ALERT_BROADCASTED = "alert_broadcasted"


class RadarStation(Base):
    """Ground or orbital radar station sending cosmic telemetry signals."""

    __tablename__ = "radar_stations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    region: Mapped[str] = mapped_column(String(80))
    is_online: Mapped[bool] = mapped_column(Boolean, default=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    owner = relationship("User", back_populates="radars")
    signals = relationship("ThreatSignal", back_populates="radar_station")


class ThreatSignal(Base):
    """Detected space threat record created directly or via EDA ingestion."""

    __tablename__ = "threat_signals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    object_code: Mapped[str] = mapped_column(String(64), index=True)
    threat_type: Mapped[str] = mapped_column(String(32), default=ThreatType.ASTEROID.value)
    severity: Mapped[str] = mapped_column(String(20), default=ThreatSeverity.LOW.value, index=True)
    distance_km: Mapped[float] = mapped_column(Float)
    velocity_kms: Mapped[float] = mapped_column(Float)
    azimuth: Mapped[float] = mapped_column(Float, default=0.0)
    elevation: Mapped[float] = mapped_column(Float, default=0.0)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default=ThreatStatus.PENDING.value, index=True)
    radar_station_id: Mapped[int | None] = mapped_column(
        ForeignKey("radar_stations.id"), nullable=True
    )
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    owner = relationship("User", back_populates="threats")
    radar_station = relationship("RadarStation", back_populates="signals")
