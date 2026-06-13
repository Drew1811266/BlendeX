from dataclasses import dataclass, field
import math
from time import time
from typing import Any, Dict, List, Optional


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return str(value)


@dataclass
class BatchRecord:
    batch_id: str
    status: str
    operation_count: int
    target: Dict[str, Any]
    summary: str
    operations: List[Dict[str, Any]]
    preview: Dict[str, Any]
    timestamp: float = field(default_factory=time)
    error: Optional[Dict[str, Any]] = None
    undo_status: str = "not_requested"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "status": self.status,
            "operation_count": self.operation_count,
            "timestamp": self.timestamp,
            "target": _json_safe(self.target),
            "summary": self.summary,
            "operations": _json_safe(self.operations),
            "preview": _json_safe(self.preview),
            "error": _json_safe(self.error),
            "undo_status": self.undo_status,
        }


@dataclass
class BatchHistory:
    max_batches: int = 20
    records: List[BatchRecord] = field(default_factory=list)

    def record(self, batch: BatchRecord) -> None:
        self.records.insert(0, batch)
        del self.records[self.max_batches :]

    def recent(self, limit: Optional[int] = None) -> List[BatchRecord]:
        if limit is None:
            return list(self.records)
        return list(self.records[:limit])

    def latest(self) -> Optional[BatchRecord]:
        if not self.records:
            return None
        return self.records[0]

    def find(self, batch_id: str) -> Optional[BatchRecord]:
        for record in self.records:
            if record.batch_id == batch_id:
                return record
        return None
