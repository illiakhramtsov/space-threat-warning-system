from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.threat import ThreatSeverity, ThreatStatus, ThreatType


class RadarCreate(BaseModel):
    code: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=2, max_length=120)
    region: str = Field(min_length=2, max_length=80)


class RadarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    region: str
    is_online: bool
    owner_id: int
    created_at: datetime


class ThreatCreate(BaseModel):
    object_code: str = Field(min_length=2, max_length=64)
    threat_type: ThreatType = ThreatType.ASTEROID
    distance_km: float = Field(gt=0)
    velocity_kms: float = Field(ge=0)
    azimuth: float = Field(default=0.0, ge=0.0, le=360.0)
    elevation: float = Field(default=0.0, ge=-90.0, le=90.0)
    description: str = Field(default="", max_length=1000)
    radar_station_id: int | None = None


class ThreatUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=1000)
    distance_km: float | None = Field(default=None, gt=0)
    velocity_kms: float | None = Field(default=None, ge=0)
    severity: ThreatSeverity | None = None


class ThreatStatusUpdate(BaseModel):
    status: ThreatStatus


class ThreatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    object_code: str
    threat_type: str
    severity: str
    distance_km: float
    velocity_kms: float
    azimuth: float
    elevation: float
    description: str
    status: str
    radar_station_id: int | None
    owner_id: int
    created_at: datetime


class SignalIngestAccepted(BaseModel):
    status: str
    object_code: str
    queued_messages: int
    server_id: str
