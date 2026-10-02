from typing import Any

import httpx

from .config import AgentSettings


class PhantomLayerClient:
    def __init__(self, settings: AgentSettings):
        self.settings = settings

    def _headers(self) -> dict[str, str]:
        if not self.settings.registration_token:
            raise RuntimeError("REGISTRATION_TOKEN is not configured")

        return {
            "Authorization": f"Bearer {self.settings.registration_token}",
            "Content-Type": "application/json",
        }

    def _agent_headers(self) -> dict[str, str]:
        if not self.settings.registration_token:
            raise RuntimeError("REGISTRATION_TOKEN is not configured")

        return {
            "X-Agent-Token": self.settings.registration_token,
            "Content-Type": "application/json",
        }

    async def login(
        self,
        *,
        email: str,
        password: str,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self.settings.phantomlayer_url,
            timeout=10.0,
        ) as client:
            response = await client.post(
                "/auth/login",
                json={
                    "email": email,
                    "password": password,
                },
            )

        response.raise_for_status()
        return response.json()

    async def list_domains(
        self,
        *,
        admin_access_token: str,
    ) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(
            base_url=self.settings.phantomlayer_url,
            timeout=10.0,
        ) as client:
            response = await client.get(
                "/domains",
                headers={
                    "Authorization": f"Bearer {admin_access_token}",
                },
            )

        response.raise_for_status()
        return response.json()

    async def register(
        self,
        *,
        name: str,
        version: str,
        capabilities: list[str],
        admin_access_token: str | None = None,
        domain_id: str | None = None,
    ) -> dict[str, Any]:
        if not admin_access_token:
            raise RuntimeError(
                "admin_access_token is required for agent registration"
            )

        if not domain_id:
            raise RuntimeError(
                "domain_id is required for agent registration"
            )

        payload = {
            "name": name,
            "version": version,
            "capabilities": capabilities,
            "domain_id": domain_id,
        }

        async with httpx.AsyncClient(
            base_url=self.settings.phantomlayer_url,
            timeout=10.0,
        ) as client:
            response = await client.post(
                "/agents/register",
                headers={
                    "Authorization": f"Bearer {admin_access_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        response.raise_for_status()
        return response.json()

    async def heartbeat(
        self,
        *,
        status: str,
        real_db_reachable: bool,
        honeypot_db_reachable: bool,
        telemetry_events_sent: int = 0,
    ) -> dict[str, Any]:
        if not self.settings.agent_id:
            raise RuntimeError("AGENT_ID is not configured")

        async with httpx.AsyncClient(
            base_url=self.settings.phantomlayer_url,
            timeout=10.0,
        ) as client:
            response = await client.post(
                f"/agents/{self.settings.agent_id}/heartbeat",
                headers=self._agent_headers(),
                json={
                    "status": status,
                    "real_db_reachable": real_db_reachable,
                    "honeypot_db_reachable": honeypot_db_reachable,
                    "telemetry_events_sent": telemetry_events_sent,
                },
            )

        response.raise_for_status()
        return response.json()

    async def get_agent(self) -> dict[str, Any]:
        if not self.settings.agent_id:
            raise RuntimeError("AGENT_ID is not configured")

        async with httpx.AsyncClient(
            base_url=self.settings.phantomlayer_url,
            timeout=10.0,
        ) as client:
            response = await client.get(
                f"/agents/{self.settings.agent_id}",
                headers=self._headers(),
            )

        response.raise_for_status()
        return response.json()