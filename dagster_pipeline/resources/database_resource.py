"""Simple database resource placeholder

Replace with an actual resource (e.g., SQLAlchemy engine, connection factory)
"""

from typing import Any


class DatabaseResource:
    """Simple example resource wrapper."""

    def __init__(self, conn_str: str):
        self.conn_str = conn_str
        self._conn = None

    def connect(self) -> Any:
        # Placeholder connect method
        self._conn = f"connected to {self.conn_str}"
        return self._conn

    def close(self) -> None:
        self._conn = None

    def __repr__(self) -> str:
        return f"DatabaseResource(conn_str={self.conn_str})\n"
