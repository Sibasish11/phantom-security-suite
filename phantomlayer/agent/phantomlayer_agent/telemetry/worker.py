import asyncio
import logging

from ..config import AgentSettings
from .client import TelemetryClient
from .queue import telemetry_queue


logger = logging.getLogger(__name__)


class TelemetryWorker:
    def __init__(
        self,
        *,
        settings: AgentSettings,
    ):
        self.settings = settings
        self.client = TelemetryClient(settings)
        self.running = False

    async def run(self) -> None:
        self.running = True

        logger.info("Telemetry worker started")

        while self.running:
            events = telemetry_queue.drain(
                limit=self.settings.telemetry_batch_size
            )

            if not events:
                await asyncio.sleep(1)
                continue

            payload = [
                event.model_dump(mode="json")
                for event in events
            ]

            try:
                response = await self.client.send_batch(
                    payload
                )

                logger.info(
                    "Telemetry batch sent: accepted=%s rejected=%s",
                    response.accepted,
                    response.rejected,
                )

            except Exception:
                logger.exception(
                    "Telemetry batch delivery failed"
                )

                # Put events back into the queue so a temporary
                # cloud outage does not silently lose telemetry.
                for event in reversed(events):
                    telemetry_queue._events.appendleft(event)

                await asyncio.sleep(5)

    def stop(self) -> None:
        self.running = False
        logger.info("Telemetry worker stopped")