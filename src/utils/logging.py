from __future__ import annotations

import logging
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from utils.text import redact_secrets

MEDIA_LEVEL = 25
RPC_LEVEL = 24
API_LEVEL = 23

logging.addLevelName(MEDIA_LEVEL, "MEDIA")
logging.addLevelName(RPC_LEVEL, "RPC")
logging.addLevelName(API_LEVEL, "API")


def media(logger: logging.Logger, message: str, *args, **kwargs) -> None:
    logger.log(MEDIA_LEVEL, message, *args, **kwargs)


def rpc(logger: logging.Logger, message: str, *args, **kwargs) -> None:
    logger.log(RPC_LEVEL, message, *args, **kwargs)


def api(logger: logging.Logger, message: str, *args, **kwargs) -> None:
    logger.log(API_LEVEL, message, *args, **kwargs)


@dataclass(frozen=True, slots=True)
class LogRecordView:
    timestamp: datetime
    level: str
    message: str

    @property
    def line(self) -> str:
        return f"{self.timestamp:%H:%M:%S}  {self.level:<8} {self.message}"


class SecretRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_secrets(record.getMessage())
        record.args = ()
        return True


class ObservableLogHandler(logging.Handler):
    def __init__(self, capacity: int = 2000) -> None:
        super().__init__()
        self.records: deque[LogRecordView] = deque(maxlen=capacity)
        self.subscribers: list[Callable[[LogRecordView], None]] = []

    def emit(self, record: logging.LogRecord) -> None:
        try:
            view = LogRecordView(
                timestamp=datetime.fromtimestamp(record.created),
                level=record.levelname,
                message=redact_secrets(record.getMessage()),
            )
            self.records.append(view)
            for subscriber in tuple(self.subscribers):
                subscriber(view)
        except Exception:
            self.handleError(record)


class CurrentDayFileHandler(logging.FileHandler):
    def __init__(self, path: Path, encoding: str = "utf-8") -> None:
        self._log_path = Path(path)
        self._day = date.today()
        mode = "a"
        try:
            if self._log_path.exists():
                modified_day = datetime.fromtimestamp(self._log_path.stat().st_mtime).date()
                if modified_day != self._day:
                    mode = "w"
        except OSError:
            pass
        super().__init__(self._log_path, mode=mode, encoding=encoding)
        self._remove_old_rotated_files()

    def _remove_old_rotated_files(self) -> None:
        try:
            for candidate in self._log_path.parent.glob(self._log_path.name + ".*"):
                if candidate.is_file():
                    candidate.unlink(missing_ok=True)
        except OSError:
            pass

    def emit(self, record: logging.LogRecord) -> None:
        today = date.today()
        if today != self._day:
            self.acquire()
            try:
                if self.stream:
                    self.stream.close()
                    self.stream = None
                self._log_path.parent.mkdir(parents=True, exist_ok=True)
                self._log_path.write_text("", encoding=self.encoding or "utf-8")
                self._day = today
                self.stream = self._open()
                self._remove_old_rotated_files()
            finally:
                self.release()
        super().emit(record)


def configure_logging(
    path: Path,
    level: str = "INFO",
    retention_days: int = 1,
) -> ObservableLogHandler:
    path.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    redaction = SecretRedactionFilter()

    _ = retention_days
    file_handler = CurrentDayFileHandler(path, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s  %(levelname)-8s %(name)s: %(message)s")
    )
    file_handler.addFilter(redaction)
    root.addHandler(file_handler)

    observable = ObservableLogHandler()
    observable.addFilter(redaction)
    root.addHandler(observable)
    return observable
