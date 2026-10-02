from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import dns.resolver
from sqlalchemy import select

from app.config import settings
from app.database import get_sync_control_db_manager
from app.models.control_plane import Domain
from app.domains.schemas import (
    DomainCreateRequest,
    DomainResponse,
    DomainVerificationResponse,
)


class DomainService:
    VERIFICATION_TTL_HOURS = 24

    @staticmethod
    def normalize_domain(domain: str) -> str:
        import re
        name = domain.strip().lower().rstrip(".")
        try:
            name = name.encode('idna').decode('ascii')
        except UnicodeError:
            raise ValueError('Enter a DNS hostname, not a URL or path') from None
        if (len(name) > 253 or '.' not in name or any(
            not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label)
            for label in name.split('.')
        )):
            raise ValueError('Enter a DNS hostname, not a URL or path')
        return name

    @staticmethod
    def _to_response(record: Domain) -> DomainResponse:
        return DomainResponse(
            id=record.id,
            domain=record.domain,
            verification_record_name=record.verification_record_name,
            verification_token=record.verification_token,
            token_expires_at=record.token_expires_at,
            verified=record.verified,
            verified_at=record.verified_at,
        )

    def create(
        self,
        request: DomainCreateRequest,
        organization_id: UUID,
    ) -> DomainResponse:
        domain_name = self.normalize_domain(request.domain)

        verification_token = uuid4().hex
        verification_record_name = (
            f"_phantomlayer-verification.{domain_name}"
        )
        token_expires_at = (
            datetime.now(timezone.utc)
            + timedelta(hours=self.VERIFICATION_TTL_HOURS)
        )

        db = get_sync_control_db_manager()

        with db.session() as session:
            existing = session.execute(
                select(Domain).where(
                    Domain.organization_id == organization_id,
                    Domain.domain == domain_name,
                )
            ).scalar_one_or_none()

            if existing is not None:
                raise ValueError(
                    "Domain already exists in this organization"
                )

            record = Domain(
                organization_id=organization_id,
                domain=domain_name,
                verification_record_name=verification_record_name,
                verification_token=verification_token,
                token_expires_at=token_expires_at,
                verified=False,
                verified_at=None,
            )

            session.add(record)
            session.flush()

            response = self._to_response(record)

            session.commit()

            return response

    def list(
        self,
        organization_id: UUID,
    ) -> list[DomainResponse]:
        db = get_sync_control_db_manager()

        with db.session() as session:
            records = session.execute(
                select(Domain)
                .where(
                    Domain.organization_id == organization_id
                )
                .order_by(Domain.created_at.desc())
            ).scalars().all()

            return [
                self._to_response(record)
                for record in records
            ]

    def get(
        self,
        domain_id: UUID,
        organization_id: UUID,
    ) -> DomainResponse | None:
        db = get_sync_control_db_manager()

        with db.session() as session:
            record = session.execute(
                select(Domain).where(
                    Domain.id == domain_id,
                    Domain.organization_id == organization_id,
                )
            ).scalar_one_or_none()

            if record is None:
                return None

            return self._to_response(record)

    def verify(
        self,
        domain_id: UUID,
        organization_id: UUID,
    ) -> DomainVerificationResponse:
        db = get_sync_control_db_manager()

        with db.session() as session:
            record = session.execute(
                select(Domain).where(
                    Domain.id == domain_id,
                    Domain.organization_id == organization_id,
                )
            ).scalar_one_or_none()

            if record is None:
                raise KeyError("Domain not found")

            if record.verified:
                return DomainVerificationResponse(
                    id=record.id,
                    domain=record.domain,
                    verified=True,
                    verified_at=record.verified_at,
                    detail="Domain is already verified",
                )

            now = datetime.now(timezone.utc)

            if (
                record.token_expires_at is not None
                and record.token_expires_at < now
            ):
                raise ValueError(
                    "Domain verification token has expired"
                )

            try:
                answers = dns.resolver.resolve(
                    record.verification_record_name,
                    "TXT",
                )

                txt_values: list[str] = []

                for answer in answers:
                    for part in answer.strings:
                        if isinstance(part, bytes):
                            txt_values.append(
                                part.decode("utf-8")
                            )
                        else:
                            txt_values.append(str(part))

            except Exception as exc:
                raise ValueError(
                    "Unable to resolve domain verification TXT record"
                ) from exc

            if record.verification_token not in txt_values:
                raise ValueError(
                    "Domain verification TXT record does not match"
                )

            record.verified = True
            record.verified_at = now

            session.commit()

            return DomainVerificationResponse(
                id=record.id,
                domain=record.domain,
                verified=True,
                verified_at=record.verified_at,
                detail="Domain ownership verified successfully",
            )

    def demo_verify(
        self,
        domain_id: UUID,
        organization_id: UUID,
    ) -> DomainVerificationResponse:
        if not settings.demo_mode:
            raise PermissionError(
                "Demo verification is disabled"
            )

        db = get_sync_control_db_manager()

        with db.session() as session:
            record = session.execute(
                select(Domain).where(
                    Domain.id == domain_id,
                    Domain.organization_id == organization_id,
                )
            ).scalar_one_or_none()

            if record is None:
                raise KeyError("Domain not found")

            if record.verified:
                return DomainVerificationResponse(
                    id=record.id,
                    domain=record.domain,
                    verified=True,
                    verified_at=record.verified_at,
                    detail="Domain is already verified",
                )

            now = datetime.now(timezone.utc)

            record.verified = True
            record.verified_at = now

            session.commit()

            return DomainVerificationResponse(
                id=record.id,
                domain=record.domain,
                verified=True,
                verified_at=record.verified_at,
                detail="Domain ownership verified in demo mode",
            )

    def clear(self) -> None:
        db = get_sync_control_db_manager()

        with db.session() as session:
            records = session.execute(
                select(Domain)
            ).scalars().all()

            for record in records:
                session.delete(record)

            session.flush()
            session.commit()


domain_service = DomainService()