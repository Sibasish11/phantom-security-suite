from typing import Any

import httpx

from ..config import AgentSettings
from .schemas import (
    TelemetryBatch,
    TelemetryResponse,
)


class TelemetryClient:
    def __init__(
        self,
        settings: AgentSettings,
    ):
        self.settings = settings

    def _headers(self) -> dict[str, str]:
        if not self.settings.registration_token:
            raise RuntimeError(
                "REGISTRATION_TOKEN is not configured"
            )

        return {
            "X-Agent-Token": (
                self.settings.registration_token
            ),
            "Content-Type": "application/json",
        }

    async def send_batch(
        self,
        events: list[dict[str, Any]],
    ) -> TelemetryResponse:
        if not events:
            return TelemetryResponse(
                accepted=0,
                rejected=0,
            )

        payload = TelemetryBatch(
            events=events,
        )

        async with httpx.AsyncClient(
            base_url=self.settings.phantomlayer_url,
            timeout=10.0,
        ) as client:
            response = await client.post(
                "/agents/telemetry",
                headers=self._headers(),
                json=payload.model_dump(
                    mode="json",
                ),
            )

        response.raise_for_status()

        return TelemetryResponse(
            **response.json()
        )