import asyncio
import getpass
import os
from pathlib import Path

from phantomlayer_agent.client import PhantomLayerClient
from phantomlayer_agent.config import AgentSettings
from phantomlayer_agent.registration import AgentRegistrationError
from phantomlayer_agent.registration import AgentRegistrationManager


async def main() -> None:
    settings = AgentSettings(
        phantomlayer_url=os.getenv(
            "PHANTOMLAYER_URL",
            "http://localhost:8000",
        ),
        agent_name=os.getenv(
            "AGENT_NAME",
            "local-test-agent",
        ),
        agent_version=os.getenv(
            "AGENT_VERSION",
            "0.1.0",
        ),
    )

    admin_email = os.getenv("PHANTOMLAYER_ADMIN_EMAIL")

    if not admin_email:
        admin_email = input(
            "PhantomLayer admin email: "
        ).strip()

    admin_password = getpass.getpass(
        "PhantomLayer admin password: "
    )

    client = PhantomLayerClient(settings)

    print()
    print("Authenticating PhantomLayer admin...")

    try:
        login_response = await client.login(
            email=admin_email,
            password=admin_password,
        )
    except Exception as exc:
        print(f"Admin authentication failed: {exc}")
        return

    admin_access_token = login_response.get("access_token")

    if not admin_access_token:
        print("Login response did not contain an access token.")
        return

    role = login_response.get("user", {}).get("role")

    if role != "admin":
        print(
            f"Authenticated user has role '{role}', "
            "but agent registration requires an admin."
        )
        return

    manager = AgentRegistrationManager(
        settings=settings,
        client=client,
    )

    print("Admin authenticated.")
    print("Registering PhantomLayer Agent...")

    try:
        response = await manager.register(
            admin_access_token=admin_access_token,
        )
    except AgentRegistrationError as exc:
        print(str(exc))
        return

    credentials_path = Path(
        os.getenv(
            "AGENT_CREDENTIALS_PATH",
            ".agent_credentials.env",
        )
    )

    manager.persist_credentials(
        response=response,
        path=credentials_path,
    )

    print()
    print("✅ Agent registered successfully.")
    print(f"Agent ID: {response['agent_id']}")
    print(f"Status: {response['status']}")
    print(f"Credentials saved to: {credentials_path}")
    print()
    print(
        "The admin access token was kept only in memory "
        "and was NOT saved."
    )


if __name__ == "__main__":
    asyncio.run(main())