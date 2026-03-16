import shutil
from abc import ABC, abstractmethod
from typing import Any


class AuthProvider(ABC):
    name: str
    display_name: str
    required_binary: str

    def __init__(self, config: dict[str, Any]):
        self.config = config

    @abstractmethod
    def setup(self, dry_run: bool = False) -> bool:
        """Run auth setup. Returns True on success."""
        ...

    @abstractmethod
    def status(self) -> list[tuple[str, bool, str]]:
        """Check auth status. Returns list of (label, is_ok, detail_message)."""
        ...

    def is_installed(self) -> bool:
        return shutil.which(self.required_binary) is not None

    @abstractmethod
    def validate_config(self) -> list[str]:
        """Return list of missing/invalid config keys."""
        ...
