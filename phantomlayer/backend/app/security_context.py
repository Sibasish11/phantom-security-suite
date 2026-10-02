"""Trusted request context for integrations that sit inside a customer's network.

The context is populated only after PhantomLayer authenticates a registered
agent. It is deliberately separate from request JSON: customer-provided
organization, tenant, and role fields are never accepted as authorization
inputs.
"""

from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Iterator
from uuid import UUID
from contextlib import contextmanager


@dataclass(frozen=True)
class TrustedContext:
    organization_id: UUID
    domain_id: UUID | None = None
    agent_id: UUID | None = None
    client_ip: str | None = None
    user_agent: str | None = None


_context: ContextVar[TrustedContext | None] = ContextVar(
    "phantomlayer_trusted_context",
    default=None,
)


def current_context() -> TrustedContext | None:
    """Return the authenticated integration context for this request."""
    return _context.get()


@contextmanager
def use_context(context: TrustedContext) -> Iterator[None]:
    token: Token[TrustedContext | None] = _context.set(context)
    try:
        yield
    finally:
        _context.reset(token)
