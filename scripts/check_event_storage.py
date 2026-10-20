"""Exercise actual private event persistence with a retained failed attempt."""

import tempfile
from pathlib import Path

from hallmark.errors import HallmarkError
from hallmark.events import EventLog, inspect_events
from hallmark.wire import decode, encode


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="hallmark-events-") as directory:
        path = Path(directory) / "events"
        with EventLog(path, max_bytes=16384) as log:
            try:
                with log.attempt(), log.stage("execute"):
                    raise HallmarkError("RESOURCE_EXHAUSTED", "execute", retryable=True)
            except HallmarkError as error:
                assert error.code == "RESOURCE_EXHAUSTED"
            with log.attempt():
                with log.stage("parse"):
                    raw = encode({"fixture": 1})
                with log.stage("verify"):
                    assert decode(raw) == {"fixture": 1}
        result = inspect_events(path, max_bytes=16384)
        assert result.status == "complete" and result.event_count == 6
        assert [record.status for record in result.attempts] == ["failed", "complete"]
        assert result.attempts[0].code == "RESOURCE_EXHAUSTED"
    print("Private event storage: failed attempt retained, explicit retry completed; 6 events.")


if __name__ == "__main__":
    main()
