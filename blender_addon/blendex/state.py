import secrets
from dataclasses import dataclass, field
from typing import List

from .logs import OperationLog


@dataclass
class BlendexState:
    port: int = 8765
    service_running: bool = False
    client_connected: bool = False
    session_token: str = field(default_factory=lambda: secrets.token_urlsafe(18))
    recent_logs: List[OperationLog] = field(default_factory=list)
    max_logs: int = 50

    def record(self, log: OperationLog) -> None:
        self.recent_logs.insert(0, log)
        del self.recent_logs[self.max_logs :]


STATE = BlendexState()
