import json
from uuid import UUID

from sqlalchemy import select

from app.database import get_sync_control_db_manager
from app.readiness import protection_readiness
from app.models.control_plane import (
    Domain,
    ProtectionConfiguration,
    ProtectionLayer,
    ProtectionStatus,
)
from app.protections.schemas import (
    ProtectionCreateRequest,
    ProtectionResponse,
    ProtectionUpdateRequest,
)


class ProtectionService:

    @staticmethod
    def _to_response(
        record: ProtectionConfiguration,
        session,
    ) -> ProtectionResponse:
        try:
            configuration = json.loads(record.configuration_json or "{}")
        except (TypeError, json.JSONDecodeError):
            configuration = {}

        state, blockers = protection_readiness(session, record)
        return ProtectionResponse(
            id=record.id,
            organization_id=record.organization_id,
            domain_id=record.domain_id,
            layer=record.layer,
            status=state,
            readiness_blockers=blockers,
            enabled=record.enabled,
            configuration=configuration,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def create(
        self,
        request: ProtectionCreateRequest,
        organization_id: UUID,
    ) -> ProtectionResponse:

        db = get_sync_control_db_manager()

        with db.session() as session:
            domain = session.execute(
                select(Domain).where(
                    Domain.id == request.domain_id,
                    Domain.organization_id == organization_id,
                )
            ).scalar_one_or_none()

            if domain is None:
                raise KeyError("Domain not found")

            if not domain.verified:
                raise ValueError(
                    "Domain must be verified before protection can be configured"
                )

            existing = session.execute(
                select(ProtectionConfiguration).where(
                    ProtectionConfiguration.domain_id == request.domain_id,
                    ProtectionConfiguration.organization_id == organization_id,
                )
            ).scalar_one_or_none()

            if existing is not None:
                raise ValueError(
                    "Protection configuration already exists for this domain"
                )

            record = ProtectionConfiguration(
                organization_id=organization_id,
                domain_id=request.domain_id,
                layer=request.layer,
                status=ProtectionStatus.CONFIGURING,
                enabled=True,
                configuration_json=json.dumps(request.configuration),
            )

            session.add(record)
            session.flush()

            response = self._to_response(record, session)

            session.commit()

            return response

    def list(
        self,
        organization_id: UUID,
    ) -> list[ProtectionResponse]:

        db = get_sync_control_db_manager()

        with db.session() as session:
            records = session.execute(
                select(ProtectionConfiguration)
                .where(
                    ProtectionConfiguration.organization_id
                    == organization_id
                )
                .order_by(ProtectionConfiguration.created_at)
            ).scalars().all()

            return [
                self._to_response(record, session)
                for record in records
            ]

    def get(
        self,
        protection_id: UUID,
        organization_id: UUID,
    ) -> ProtectionResponse | None:

        db = get_sync_control_db_manager()

        with db.session() as session:
            record = session.execute(
                select(ProtectionConfiguration).where(
                    ProtectionConfiguration.id == protection_id,
                    ProtectionConfiguration.organization_id
                    == organization_id,
                )
            ).scalar_one_or_none()

            if record is None:
                return None

            return self._to_response(record, session)

    def update(
        self,
        protection_id: UUID,
        request: ProtectionUpdateRequest,
        organization_id: UUID,
    ) -> ProtectionResponse:

        db = get_sync_control_db_manager()

        with db.session() as session:
            record = session.execute(
                select(ProtectionConfiguration).where(
                    ProtectionConfiguration.id == protection_id,
                    ProtectionConfiguration.organization_id
                    == organization_id,
                )
            ).scalar_one_or_none()

            if record is None:
                raise KeyError("Protection configuration not found")

            if request.layer is not None:
                record.layer = request.layer

            if request.enabled is not None:
                record.enabled = request.enabled

            if request.configuration is not None:
                record.configuration_json = json.dumps(
                    request.configuration
                )

            session.flush()

            response = self._to_response(record, session)

            session.commit()

            return response

    def delete(
        self,
        protection_id: UUID,
        organization_id: UUID,
    ) -> None:

        db = get_sync_control_db_manager()

        with db.session() as session:
            record = session.execute(
                select(ProtectionConfiguration).where(
                    ProtectionConfiguration.id == protection_id,
                    ProtectionConfiguration.organization_id
                    == organization_id,
                )
            ).scalar_one_or_none()

            if record is None:
                raise KeyError("Protection configuration not found")

            session.delete(record)
            session.flush()
            session.commit()


protection_service = ProtectionService()
