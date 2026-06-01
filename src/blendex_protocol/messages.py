from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .errors import BlendexError


@dataclass
class OperationRequest:
    id: str
    type: str
    target: Dict[str, Any] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "OperationRequest":
        request_id = payload.get("id")
        request_type = payload.get("type")
        if not isinstance(request_id, str) or not request_id:
            raise BlendexError("VALIDATION_FAILED", "Request id must be a non-empty string.")
        if not isinstance(request_type, str) or not request_type:
            raise BlendexError("VALIDATION_FAILED", "Request type must be a non-empty string.")
        target = payload.get("target", {})
        params = payload.get("params", {})
        if not isinstance(target, dict):
            raise BlendexError("VALIDATION_FAILED", "Request target must be an object.")
        if not isinstance(params, dict):
            raise BlendexError("VALIDATION_FAILED", "Request params must be an object.")
        return cls(id=request_id, type=request_type, target=target, params=params)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "target": self.target,
            "params": self.params,
        }


@dataclass
class OperationResponse:
    id: str
    ok: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

    @classmethod
    def success(cls, request_id: str, result: Optional[Dict[str, Any]] = None) -> "OperationResponse":
        return cls(id=request_id, ok=True, result=result or {})

    @classmethod
    def error(cls, request_id: str, error: BlendexError) -> "OperationResponse":
        return cls(id=request_id, ok=False, error=error.to_dict())

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"id": self.id, "ok": self.ok}
        if self.ok:
            data["result"] = self.result or {}
        else:
            data["error"] = self.error or {}
        return data
