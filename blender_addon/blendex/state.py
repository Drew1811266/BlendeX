import secrets
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .history import BatchHistory, BatchRecord
from .logs import OperationLog


@dataclass
class BlendexState:
    port: int = 8765
    service_running: bool = False
    client_connected: bool = False
    client_authenticated: bool = False
    last_auth_error: str = ""
    session_token: str = field(default_factory=lambda: secrets.token_urlsafe(18))
    recent_logs: List[OperationLog] = field(default_factory=list)
    max_logs: int = 50
    batch_history: BatchHistory = field(default_factory=BatchHistory)
    undo_callback: Optional[Callable[[BatchRecord], None]] = None

    def record(self, log: OperationLog) -> None:
        self.recent_logs.insert(0, log)
        del self.recent_logs[self.max_logs :]

    def record_batch(self, record: BatchRecord) -> None:
        self.batch_history.record(record)

    def recent_batches(self, limit: int = 5) -> List[BatchRecord]:
        return self.batch_history.recent(limit)


STATE = BlendexState()
