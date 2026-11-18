"""Configurable school branding for the web UI.

The school name, logo, seed color and palette source come from ``school.toml``
and can be overridden with the ``SCHOOL_NAME``, ``SCHOOL_LOGO``, ``SCHOOL_COLOR``
and ``SCHOOL_PALETTE`` environment variables. BeerCSS derives the full Material
You palette used by every page from either the logo image or the seed color.
"""

import os
import re
import tempfile
import tomllib
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, field_validator

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "school.toml"
# Branding saved from the admin panel lives here, so the file school.toml ships with
# (and the project's git history) stays a readable default.
SAVED_PATH = BASE_DIR / "branding.toml"

ENVIRONMENT_VARIABLES = {
    "name": "SCHOOL_NAME",
    "logo": "SCHOOL_LOGO",
    "color": "SCHOOL_COLOR",
    "palette": "SCHOOL_PALETTE",
}

_SAFE_LOGO = re.compile(r"[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*\Z")
_HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}\Z")


class SchoolSettings(BaseModel):
    """Branding values rendered by the templates."""

    name: str = "School DB"
    logo: str = "logo.svg"
    color: str = "#0b57d0"
    palette: Literal["color", "logo"] = "logo"

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

    @property
    def theme_source(self) -> str:
        """Value the page hands to BeerCSS's ``ui("theme", ...)``.

        With ``palette = "logo"`` it is the logo path under the app's ``/static``
        mount, so changing the logo changes the whole colorscheme; with
        ``palette = "color"`` it is the seed color, which needs no image and does
        not depend on JavaScript running.
        """
        if self.palette == "logo":
            return f"/static/{self.logo}"
        return self.color


def load_school_settings(
    config_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
    saved_path: Path | None = None,
) -> SchoolSettings:
    """Read the branding files that exist, then apply environment overrides.

    Precedence, lowest to highest: ``school.toml``, then ``branding.toml`` (what the
    admin saved from the web), then the ``SCHOOL_*`` environment variables, which a
    deployment can use to pin a value the page must not change.
    """
    path = CONFIG_PATH if config_path is None else config_path
    values: dict[str, Any] = {}

    for source in (path, SAVED_PATH if saved_path is None else saved_path):
        if not source.is_file():
            continue
        with source.open("rb") as handle:
            document = tomllib.load(handle)
        table = document.get("school")
        if not isinstance(table, dict):
            raise ValueError(f"{source.name} must define a [school] table")
        values.update(table)

    environment = os.environ if environ is None else environ
    for field_name, variable in ENVIRONMENT_VARIABLES.items():
        override = environment.get(variable)
        if override is not None and override.strip():
            values[field_name] = override

    return SchoolSettings.model_validate(values)


def save_school_settings(
    values: Mapping[str, Any],
    saved_path: Path | None = None,
) -> SchoolSettings:
    """Validate branding, then write it where the next load will find it.

    The values are validated before anything touches the disk, so a rejected form
    never leaves a half-written file behind. The file is replaced atomically: a crash
    mid-write keeps the previous branding instead of a truncated one.
    """
    path = SAVED_PATH if saved_path is None else saved_path
    current = load_school_settings()
    candidate = SchoolSettings.model_validate({**current.model_dump(), **values})

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=str(path.parent), prefix=".branding-", suffix=".toml")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("[school]\n")
            for field_name in ("name", "logo", "color", "palette"):
                handle.write(f'{field_name} = "{getattr(candidate, field_name)}"\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise

    get_school_settings.cache_clear()
    return get_school_settings()


@lru_cache(maxsize=1)
def get_school_settings() -> SchoolSettings:
    """FastAPI dependency: the branding settings for this process."""
    return load_school_settings()
