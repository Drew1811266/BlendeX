from dataclasses import dataclass
from typing import Any, Dict, Optional


ERROR_CODES = {
    "BLENDER_NOT_CONNECTED",
    "AUTH_REQUIRED",
    "AUTH_FAILED",
    "BATCH_NOT_FOUND",
    "UNSUPPORTED_OPERATION",
    "OBJECT_NOT_FOUND",
    "OBJECT_NOT_SELECTED",
    "MODIFIER_NOT_FOUND",
    "NODE_TREE_NOT_FOUND",
    "NODE_TYPE_NOT_FOUND",
    "SOCKET_NOT_FOUND",
    "SOCKET_TYPE_MISMATCH",
    "LINK_NOT_ALLOWED",
    "VALUE_TYPE_MISMATCH",
    "OWNERSHIP_REQUIRED",
    "CONFIRMATION_REQUIRED",
    "VALIDATION_FAILED",
    "EXECUTION_FAILED",
    "UNDO_UNAVAILABLE",
    "UNDO_FAILED",
}


@dataclass
class BlendexError(Exception):
    code: str
    message: str
    retry_hint: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.code not in ERROR_CODES:
            raise ValueError(f"Unknown BlendeX error code: {self.code}")
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"code": self.code, "message": self.message}
        if self.retry_hint:
            data["retry_hint"] = self.retry_hint
        if self.details:
            data["details"] = self.details
        return data
