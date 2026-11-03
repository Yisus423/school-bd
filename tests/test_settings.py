"""Tests for file, environment, and schema validation of school branding."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from settings import SchoolSettings, load_school_settings


def test_load_school_settings_uses_defaults_when_config_is_missing(
    tmp_path: Path,
) -> None:
    loaded = load_school_settings(
        config_path=tmp_path / "missing-school.toml", environ={}
    )

    assert loaded.model_dump() == {
        "name": "School DB",
        "logo": "logo.svg",
        "color": "#0b57d0",
    }


def test_load_school_settings_reads_values_from_the_school_table(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "school.toml"
    config_path.write_text(
        """[school]
name = "Northside Academy"
logo = "northside-logo.svg"
color = "#ABCDEF"
""",
        encoding="utf-8",
    )

    loaded = load_school_settings(config_path=config_path, environ={})

    assert loaded.model_dump() == {
        "name": "Northside Academy",
        "logo": "northside-logo.svg",
        "color": "#abcdef",
    }


def test_load_school_settings_prefers_environment_overrides(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "school.toml"
    config_path.write_text(
        """[school]
name = "File School"
logo = "file-logo.svg"
color = "#111111"
""",
        encoding="utf-8",
    )
    environment = {
        "SCHOOL_NAME": "Environment School",
        "SCHOOL_LOGO": "environment-logo.svg",
        "SCHOOL_COLOR": "#654321",
    }

    loaded = load_school_settings(config_path=config_path, environ=environment)

    assert loaded.model_dump() == {
        "name": "Environment School",
        "logo": "environment-logo.svg",
        "color": "#654321",
    }


@pytest.mark.parametrize(
    "values",
    [
        pytest.param({"color": "red"}, id="invalid-color"),
        pytest.param({"name": "   "}, id="blank-name"),
        pytest.param({"logo": "../secret.png"}, id="relative-logo-escape"),
        pytest.param({"logo": "/etc/passwd"}, id="absolute-logo-escape"),
    ],
)
def test_school_settings_rejects_invalid_branding_values(
    values: dict[str, str],
) -> None:
    with pytest.raises(ValidationError):
        SchoolSettings(**values)
