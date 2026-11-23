"""Seed initial admin, demo operator, radar stations, and sample threats."""

import os
import sys

sys.path.insert(0, os.path.abspath("src"))

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.threat import RadarStation, ThreatSignal
from app.models.user import User, UserRole


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if admin is None:
            admin = User(
                username="admin",
                email="admin@space-defense.org",
                full_name="Space Defense Commander",
                hashed_password=hash_password(os.getenv("SEED_ADMIN_PASSWORD", "AdminSpace2026!")),
                role=UserRole.ADMIN.value,
            )
            db.add(admin)

        operator = db.query(User).filter(User.username == "operator1").first()
        if operator is None:
            operator = User(
                username="operator1",
                email="operator1@radar-net.org",
                full_name="Primary Radar Operator",
                hashed_password=hash_password("Operator2026!"),
                role=UserRole.USER.value,
            )
            db.add(operator)

        db.commit()
        db.refresh(operator)

        if db.query(RadarStation).count() == 0:
            radar = RadarStation(
                code="RAD-ODS-01",
                name="Black Sea Deep Space Radar",
                region="South-UA",
                owner_id=operator.id,
            )
            db.add(radar)
            db.commit()
            db.refresh(radar)

            db.add(
                ThreatSignal(
                    object_code="NEO-2026-ALPHA",
                    threat_type="asteroid",
                    severity="high",
                    distance_km=185000.0,
                    velocity_kms=27.4,
                    azimuth=142.5,
                    elevation=38.0,
                    description="Initial cataloged near-Earth asteroid",
                    radar_station_id=radar.id,
                    owner_id=operator.id,
                )
            )
            db.commit()
        print("Seed completed successfully (users: admin / operator1).")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
