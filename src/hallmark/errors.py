"""Allowlisted errors for trust boundaries; never stringify external exceptions."""

import subprocess
import uuid
from collections.abc import Sequence
from typing import Literal, get_args

type ErrorCode = Literal[
    "INPUT_INVALID",
    "LIMIT_EXCEEDED",
    "TRUST_MISSING",
    "REGISTRY_INVALID",
    "ARTIFACT_RETIRED",
    "REQUEST_MISMATCH",
    "STALE_EVIDENCE",
    "SIGNATURE_INVALID",
    "ATTESTATION_INVALID",
    "MEASUREMENT_UNKNOWN",
    "OPENING_FAILED",
    "INPUT_BINDING_FAILED",
    "PROOF_INVALID",
    "VERDICT_MISMATCH",
    "POLICY_BLOCKED",
    "PROOF_PENDING",
    "RESOURCE_EXHAUSTED",
    "STORAGE_FAILED",
    "INTERNAL_ERROR",
]
type Stage = Literal["parse", "enroll", "attest", "bind", "execute", "prove", "verify", "store"]

ERROR_CODES: frozenset[ErrorCode] = frozenset(get_args(ErrorCode.__value__))
STAGES: tuple[Stage, ...] = get_args(Stage.__value__)
_CONFIG_ERRORS = frozenset(("INPUT_INVALID", "LIMIT_EXCEEDED", "TRUST_MISSING"))
_EXECUTION_ERRORS = frozenset(
    ("PROOF_PENDING", "RESOURCE_EXHAUSTED", "STORAGE_FAILED", "INTERNAL_ERROR")
)


class HallmarkError(ValueError):
    """A finite code/stage with a local random ID for unexpected failures."""

    def __init__(self, code: ErrorCode, stage: Stage, retryable: bool = False) -> None:
        if (
            type(code) is not str
            or code not in ERROR_CODES
            or type(stage) is not str
            or stage not in STAGES
            or type(retryable) is not bool
        ):
            raise ValueError("invalid error metadata")
        self.code: ErrorCode = code
        self.stage: Stage = stage
        self.retryable: bool = retryable
        self.diagnostic_id: str | None = uuid.uuid4().hex if code == "INTERNAL_ERROR" else None
        super().__init__(code)

    @property
    def exit_code(self) -> int:
        if self.code in _CONFIG_ERRORS:
            return 2
        if self.code in _EXECUTION_ERRORS:
            return 3
        return 1

    def as_dict(self) -> dict[str, str | bool | None]:
        """Allowlist the error record rather than serializing exception attributes."""
        return {
            "schema_id": "hallmark/error/1",
            "code": self.code,
            "stage": self.stage,
            "retryable": self.retryable,
            "diagnostic_id": self.diagnostic_id,
        }


def sanitize_exception(error: Exception, *, stage: Stage) -> HallmarkError:
    """Translate known baseline failures; discard messages, causes and process output."""
    if isinstance(error, HallmarkError):
        return error
    if isinstance(error, (TimeoutError, MemoryError, subprocess.TimeoutExpired)):
        return HallmarkError("RESOURCE_EXHAUSTED", stage)
    if isinstance(error, (ValueError, FileNotFoundError, NotADirectoryError, IsADirectoryError)):
        return HallmarkError("INPUT_INVALID", "parse")
    if isinstance(error, OSError):
        return HallmarkError("STORAGE_FAILED", "store")
    return HallmarkError("INTERNAL_ERROR", stage)


def first_stage_errors(errors: Sequence[HallmarkError]) -> tuple[HallmarkError, ...]:
    """Return sorted errors from the earliest stage, bounded like result code lists."""
    if not 1 <= len(errors) <= 64 or any(not isinstance(e, HallmarkError) for e in errors):
        raise HallmarkError("INPUT_INVALID", "parse")
    stage = min(STAGES.index(error.stage) for error in errors)
    return tuple(
        sorted(
            (error for error in errors if STAGES.index(error.stage) == stage),
            key=lambda error: (error.code, error.retryable),
        )
    )
