from collections import deque

from .schemas import TelemetryEvent


class TelemetryQueue:
    def __init__(
        self,
        *,
        max_size: int = 1000,
    ):
        self._events: deque[TelemetryEvent] = deque(
            maxlen=max_size,
        )

    def put(
        self,
        event: TelemetryEvent,
    ) -> None:
        self._events.append(event)

    def drain(
        self,
        *,
        limit: int = 100,
    ) -> list[TelemetryEvent]:
        events: list[TelemetryEvent] = []

        for _ in range(
            min(limit, len(self._events))
        ):
            events.append(
                self._events.popleft()
            )

        return events

    def size(self) -> int:
        return len(self._events)


telemetry_queue = TelemetryQueue()