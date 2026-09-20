"""Raw wire-format builders for tests.

Deliberately hand-written JSON, *not* built with the contracts codec: tests that consume a
service's output must prove the consumer accepts what the contract says is on the wire, so the
expected bytes are spelled out independently of the code under test.
"""

import json
from datetime import UTC, datetime
from typing import Any


def stream_event_bytes(event_type: str, sequence: int, payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            {
                "type": event_type,
                "sequence": sequence,
                "timestamp": datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z"),
                "payload": payload,
            },
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
