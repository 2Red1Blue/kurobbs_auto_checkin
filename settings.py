import os
from dataclasses import dataclass
from typing import List, Optional


class SettingsError(Exception):
    """Raised when required settings are missing or invalid."""


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


VALID_TOKEN_SOURCES = ("android", "h5")


@dataclass
class Settings:
    token: str
    debug: bool = False
    token_source: str = "android"
    bark_device_key: Optional[str] = None
    bark_server_url: Optional[str] = None
    server3_send_key: Optional[str] = None

    @classmethod
    def load(cls) -> "Settings":
        token = os.getenv("TOKEN")
        if not token:
            raise SettingsError("TOKEN is required but missing.")

        token_source = (os.getenv("TOKEN_SOURCE") or "android").strip().lower()
        if token_source not in VALID_TOKEN_SOURCES:
            raise SettingsError(
                f"TOKEN_SOURCE must be one of {list(VALID_TOKEN_SOURCES)}, got {token_source!r}."
            )

        return cls(
            token=token,
            debug=parse_bool(os.getenv("DEBUG", "")),
            token_source=token_source,
            bark_device_key=os.getenv("BARK_DEVICE_KEY"),
            bark_server_url=os.getenv("BARK_SERVER_URL"),
            server3_send_key=os.getenv("SERVER3_SEND_KEY"),
        )

    def sensitive_values(self) -> List[str]:
        """Values that should be redacted from logs."""
        return [value for value in [self.token, self.bark_device_key, self.bark_server_url, self.server3_send_key] if value]
