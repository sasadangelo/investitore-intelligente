# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, computed_field

# Resolve config.yaml relative to this file's location (src/intelligent_investor/)
_CONFIG_PATH: Path = Path(__file__).parent.parent / "config.yaml"


# ---------------------------------------------------------------------------
# Section models
# All fields are required; the values below are the documented defaults.
# A missing or invalid config.yaml will raise ValidationError at startup.
# ---------------------------------------------------------------------------

class AppSettings(BaseModel):
    debug: bool = Field(default=False)          # default: false
    host: str = Field(default="0.0.0.0")        # default: "0.0.0.0"
    port: int = Field(default=5001, ge=1, le=65535)  # default: 5001


class SQLiteSettings(BaseModel):
    relative_path: str = Field(default="data/investor.db")  # default: "data/investor.db"
    echo: bool = Field(default=False)                        # default: false
    pool_pre_ping: bool = Field(default=True)                # default: true

    @computed_field  # type: ignore[prop-decorator]
    @property
    def absolute_path(self) -> Path:
        return Path(self.relative_path).resolve()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.absolute_path}"


class DatabaseSettings(BaseModel):
    sqlite: SQLiteSettings = Field(default_factory=SQLiteSettings)


class LogSettings(BaseModel):
    level: str = Field(default="INFO")          # default: "INFO"
    console: bool = Field(default=True)         # default: true
    file: str = Field(default="logs/investor.log")   # default: "logs/investor.log"
    rotation: str = Field(default="10 MB")      # default: "10 MB"
    retention: str = Field(default="7 days")    # default: "7 days"
    compression: str = Field(default="zip")     # default: "zip"


# ---------------------------------------------------------------------------
# Root config model
# ---------------------------------------------------------------------------

class Config(BaseModel):
    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    log: LogSettings = Field(default_factory=LogSettings)


def _load() -> Config:
    """
    Load and validate config.yaml.

    Raises:
        FileNotFoundError: if config.yaml does not exist.
        yaml.YAMLError: if the file is not valid YAML.
        pydantic.ValidationError: if any field has an invalid value.
    """
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {_CONFIG_PATH}\n"
            "Create 'src/intelligent_investor/config.yaml' before starting the application."
        )

    with _CONFIG_PATH.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    # config.yaml uses database.relative_path; nest it under 'sqlite' for the model
    db_raw = raw.get("database", {})
    raw["database"] = {"sqlite": db_raw}

    return Config.model_validate(raw)


# Loaded once at import time — raises on missing/invalid config.yaml.
config: Config = _load()
