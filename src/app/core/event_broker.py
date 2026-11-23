import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RadarEvent:
    """Asynchronous telemetry event produced by radar stations."""

    object_code: str
    threat_type: str
    distance_km: float
    velocity_kms: float
    azimuth: float
    elevation: float
    owner_id: int
    radar_station_id: int | None = None
    description: str = ""
    received_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def evaluate_severity(distance_km: float, velocity_kms: float) -> str:
    """Classify cosmic threat severity from orbital distance and velocity."""
    if distance_km < 50_000 or velocity_kms > 40.0:
        return "critical"
    if distance_km < 250_000 or velocity_kms > 25.0:
        return "high"
    if distance_km < 1_000_000:
        return "medium"
    return "low"


class InMemoryEventBroker:
    """Async EDA broker buffering peak radar bursts before DB persistence."""

    def __init__(self, maxsize: int = 10_000) -> None:
        self._maxsize = maxsize
        self._queue: asyncio.Queue[RadarEvent] | None = None
        self._worker_task: asyncio.Task[None] | None = None
        self.ingested_count: int = 0
        self.processed_count: int = 0

    def _get_queue(self) -> asyncio.Queue[RadarEvent]:
        if self._queue is None:
            self._queue = asyncio.Queue(maxsize=self._maxsize)
        return self._queue

    async def publish(self, event: RadarEvent) -> int:
        """Push an incoming radar event onto the async queue."""
        queue = self._get_queue()
        await queue.put(event)
        self.ingested_count += 1
        return queue.qsize()

    def start(self, session_factory: Any) -> None:
        """Start background consumer coroutine in the active event loop."""
        self._queue = asyncio.Queue(maxsize=self._maxsize)
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._consume_loop(session_factory))

    async def stop(self) -> None:
        """Gracefully stop background consumer coroutine."""
        if self._worker_task is not None:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        self._queue = None

    async def _consume_loop(self, session_factory: Any) -> None:
        """Continuously consume queued radar events and persist analyzed threats."""
        from app.models.threat import ThreatSignal

        queue = self._get_queue()
        while True:
            event = await queue.get()
            try:
                severity = evaluate_severity(event.distance_km, event.velocity_kms)
                db = session_factory()
                try:
                    signal = ThreatSignal(
                        object_code=event.object_code,
                        threat_type=event.threat_type,
                        severity=severity,
                        distance_km=event.distance_km,
                        velocity_kms=event.velocity_kms,
                        azimuth=event.azimuth,
                        elevation=event.elevation,
                        description=event.description or "Auto-ingested radar telemetry",
                        status="pending",
                        radar_station_id=event.radar_station_id,
                        owner_id=event.owner_id,
                    )
                    db.add(signal)
                    db.commit()
                    self.processed_count += 1
                finally:
                    db.close()
            except Exception:
                logger.exception("Failed to process radar event %s", event.object_code)
            finally:
                queue.task_done()

    def stats(self) -> dict[str, int]:
        """Return current broker metrics."""
        return {
            "queue_size": self._queue.qsize() if self._queue is not None else 0,
            "ingested_total": self.ingested_count,
            "processed_total": self.processed_count,
        }


event_broker = InMemoryEventBroker()
