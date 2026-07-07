# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from pathlib import Path

import yaml
from pydantic import BaseModel, computed_field

# Resolve config.yaml relative to this file's location (src/intelligent-investor/)
_CONFIG_PATH: Path = Path(__file__).parent.parent / "config.yaml"


# ---------------------------------------------------------------------------
# Section models
# ---------------------------------------------------------------------------

class AppSettings(BaseModel):
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 5001


class SQLiteSettings(BaseModel):
    relative_path: str = "data/investitore.db"
    echo: bool = False
    pool_pre_ping: bool = True

    @computed_field  # type: ignore[prop-decorator]
    @property
    def absolute_path(self) -> Path:
        return Path(self.relative_path).resolve()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.absolute_path}"


class DatabaseSettings(BaseModel):
    sqlite: SQLiteSettings = SQLiteSettings()


class LogSettings(BaseModel):
    level: str = "INFO"
    console: bool = True
    file: str = "logs/investitore.log"
    rotation: str = "10 MB"
    retention: str = "7 days"
    compression: str = "zip"


# ---------------------------------------------------------------------------
# Root config model
# ---------------------------------------------------------------------------

class Config(BaseModel):
    app: AppSettings = AppSettings()
    database: DatabaseSettings = DatabaseSettings()
    log: LogSettings = LogSettings()


def _load_config() -> Config:
    """Load config.yaml and return a validated Config instance."""
    if not _CONFIG_PATH.exists():
        return Config()

    with _CONFIG_PATH.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    # config.yaml uses database.relative_path; nest it under 'sqlite' for the model
    db_raw = raw.get("database", {})
    raw["database"] = {"sqlite": db_raw}

    return Config.model_validate(raw)


# Global configuration instance
config = _load_config()
