import asyncio
import logging

from .client import PhantomLayerClient
from .config import AgentSettings
from .health import check_databases

logger = logging.getLogger(__name__)


class HeartbeatWorker:
    def __init__(
        self,
        settings: AgentSettings,
        client: PhantomLayerClient,
    ):
        self.settings = settings
        self.client = client

        self.telemetry_events_sent = 0

    async def send_once(self) -> dict:
        real_ok, honeypot_ok = await check_databases(
            self.settings.real_database_url,
            self.settings.honeypot_database_url,
        )

        if real_ok and honeypot_ok:
            status = "healthy"
        elif real_ok or honeypot_ok:
            status = "degraded"
        else:
            status = "offline"

        result = await self.client.heartbeat(
            status=status,
            real_db_reachable=real_ok,
            honeypot_db_reachable=honeypot_ok,
            telemetry_events_sent=self.telemetry_events_sent,
        )

        logger.info(
            "Heartbeat sent: status=%s real_db=%s honeypot_db=%s",
            status,
            real_ok,
            honeypot_ok,
        )

        return result

    async def run(self) -> None:
        while True:
            try:
                await self.send_once()

            except Exception:
                logger.exception("Heartbeat failed")

            await asyncio.sleep(
                self.settings.heartbeat_interval_seconds
            )