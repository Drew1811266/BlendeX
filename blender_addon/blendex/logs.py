from dataclasses import dataclass
from time import time
from typing import Optional


@dataclass
class OperationLog:
    request_id: str
    operation: str
    ok: bool
    message: str
    timestamp: float = 0.0
    error_code: Optional[str] = None

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time()
