from pathlib import Path

from .client import PhantomLayerClient
from .config import AgentSettings


class AgentRegistrationError(RuntimeError):
    """Raised when PhantomLayer agent registration fails."""


class AgentRegistrationManager:
    def __init__(
        self,
        *,
        settings: AgentSettings,
        client: PhantomLayerClient,
    ):
        self.settings = settings
        self.client = client

    async def get_verified_domain(
        self,
        *,
        admin_access_token: str,
    ) -> dict:
        try:
            domains = await self.client.list_domains(
                admin_access_token=admin_access_token,
            )
        except Exception as exc:
            raise AgentRegistrationError(
                f"Failed to retrieve domains: {exc}"
            ) from exc

        verified_domains = [
            domain
            for domain in domains
            if domain.get("verified") is True
        ]

        if not verified_domains:
            raise AgentRegistrationError(
                "No verified domain exists for this organization"
            )

        return verified_domains[0]

    async def register(
        self,
        *,
        admin_access_token: str | None = None,
        domain_id: str | None = None,
    ) -> dict:
        if not admin_access_token:
            raise AgentRegistrationError(
                "admin_access_token is required for agent registration"
            )

        if not domain_id:
            domain = await self.get_verified_domain(
                admin_access_token=admin_access_token,
            )
            domain_id = domain["id"]

        try:
            response = await self.client.register(
                name=self.settings.agent_name,
                version=self.settings.agent_version,
                capabilities=[
                    "api-protection",
                    "database-protection",
                    "honeypot-routing",
                    "telemetry",
                ],
                admin_access_token=admin_access_token,
                domain_id=domain_id,
            )
        except Exception as exc:
            raise AgentRegistrationError(
                f"Agent registration failed: {exc}"
            ) from exc

        if not response.get("agent_id"):
            raise AgentRegistrationError(
                "Registration response did not contain agent_id"
            )

        if not response.get("registration_token"):
            raise AgentRegistrationError(
                "Registration response did not contain registration_token"
            )

        return response

    @staticmethod
    def persist_credentials(
        *,
        response: dict,
        path: str | Path,
    ) -> None:
        credentials_path = Path(path)

        credentials_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        credentials_path.write_text(
            f"AGENT_ID={response['agent_id']}\n"
            f"REGISTRATION_TOKEN={response['registration_token']}\n",
            encoding="utf-8",
        )

        credentials_path.chmod(0o600)