import asyncio
import logging

from .client import PhantomLayerClient
from .config import get_settings
from .heartbeat import HeartbeatWorker
from .telemetry.worker import TelemetryWorker


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("phantomlayer-agent")


async def main() -> None:
    settings = get_settings()

    logger.info(
        "Starting PhantomLayer Agent: %s v%s",
        settings.agent_name,
        settings.agent_version,
    )

    if not settings.agent_id:
        raise RuntimeError(
            "AGENT_ID must be configured before starting the agent"
        )

    if not settings.registration_token:
        raise RuntimeError(
            "REGISTRATION_TOKEN must be configured before starting the agent"
        )

    client = PhantomLayerClient(settings)

    heartbeat_worker = HeartbeatWorker(
        settings=settings,
        client=client,
    )

    telemetry_worker = TelemetryWorker(
        settings=settings,
    )

    await asyncio.gather(
        heartbeat_worker.run(),
        telemetry_worker.run(),
    )


if __name__ == "__main__":
    asyncio.run(main())