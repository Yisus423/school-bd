"""Configurable school branding for the web UI.

The school name, logo file and seed color come from ``school.toml`` and can be
overridden with the ``SCHOOL_NAME``, ``SCHOOL_LOGO`` and ``SCHOOL_COLOR``
environment variables. The seed color feeds BeerCSS's dynamic theme, which
derives the full Material You palette used by every page.
"""

import os
import re
import tomllib
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, field_validator

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "school.toml"

ENVIRONMENT_VARIABLES = {
    "name": "SCHOOL_NAME",
    "logo": "SCHOOL_LOGO",
    "color": "SCHOOL_COLOR",
}

_SAFE_LOGO = re.compile(r"[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*\Z")
_HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}\Z")


class SchoolSettings(BaseModel):
    """Branding values rendered by the templates."""

    name: str = "School DB"
    logo: str = "logo.svg"
    color: str = "#0b57d0"

    @field_validator("name")
    @classmethod
    def _require_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("school name must not be blank")
        return value

    @field_validator("logo")
    @classmethod
    def _require_safe_logo(cls, value: str) -> str:
        value = value.strip()
        # `.` is allowed inside a name but a segment made only of dots is a
        # traversal attempt, so segments are checked one by one.
        segments = value.split("/")
        if not _SAFE_LOGO.fullmatch(value) or any(
            segment in {"", ".", ".."} for segment in segments
        ):
            raise ValueError(
                "school logo must be a relative path inside static/ without '..'"
            )
        return value

    @field_validator("color")
    @classmethod
    def _require_hex_color(cls, value: str) -> str:
        value = value.strip()
        if not _HEX_COLOR.fullmatch(value):
            raise ValueError("school color must use the #RRGGBB format")
        return value.lower()


def load_school_settings(
    config_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> SchoolSettings:
    """Read ``school.toml`` when it exists, then apply environment overrides."""
    path = CONFIG_PATH if config_path is None else config_path
    values: dict[str, Any] = {}

    if path.is_file():
        with path.open("rb") as handle:
            document = tomllib.load(handle)
        table = document.get("school", {})
        if not isinstance(table, dict):
            raise ValueError("school.toml must define a [school] table")
        values.update(table)

    environment = os.environ if environ is None else environ
    for field_name, variable in ENVIRONMENT_VARIABLES.items():
        override = environment.get(variable)
        if override is not None and override.strip():
            values[field_name] = override

    return SchoolSettings.model_validate(values)


@lru_cache(maxsize=1)
def get_school_settings() -> SchoolSettings:
    """FastAPI dependency: the branding settings for this process."""
    return load_school_settings()
