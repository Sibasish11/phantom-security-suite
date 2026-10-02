from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class SessionInteraction:
    step: int
    operation: str
    target: str
    risk_score: int
    suspicious: bool
    attack_stage: str
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class AttackSession:
    session_id: str
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_seen_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    interaction_count: int = 0
    attack_stage: str = "unknown"
    interactions: list[SessionInteraction] = field(
        default_factory=list
    )

    def record(
        self,
        *,
        operation: str,
        target: str,
        risk_score: int,
        suspicious: bool,
        attack_stage: str,
    ) -> SessionInteraction:
        now = datetime.now(timezone.utc)

        self.interaction_count += 1
        self.last_seen_at = now
        self.attack_stage = attack_stage

        interaction = SessionInteraction(
            step=self.interaction_count,
            operation=operation,
            target=target,
            risk_score=risk_score,
            suspicious=suspicious,
            attack_stage=attack_stage,
            timestamp=now,
        )

        self.interactions.append(interaction)

        return interaction