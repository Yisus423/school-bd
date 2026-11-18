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
        "palette": "logo",
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
palette = "color"
""",
        encoding="utf-8",
    )

    loaded = load_school_settings(config_path=config_path, environ={})

    assert loaded.model_dump() == {
        "name": "Northside Academy",
        "logo": "northside-logo.svg",
        "color": "#abcdef",
        "palette": "color",
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
palette = "logo"
""",
        encoding="utf-8",
    )
    environment = {
        "SCHOOL_NAME": "Environment School",
        "SCHOOL_LOGO": "environment-logo.svg",
        "SCHOOL_COLOR": "#654321",
        "SCHOOL_PALETTE": "color",
    }

    loaded = load_school_settings(config_path=config_path, environ=environment)

    assert loaded.model_dump() == {
        "name": "Environment School",
        "logo": "environment-logo.svg",
        "color": "#654321",
        "palette": "color",
    }


@pytest.mark.parametrize(
    "values",
    [
        pytest.param({"color": "red"}, id="invalid-color"),
        pytest.param({"palette": "rainbow"}, id="invalid-palette"),
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


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        pytest.param(
            {"palette": "logo", "logo": "northside.svg"},
            "/static/northside.svg",
            id="logo-source",
        ),
        pytest.param(
            {"palette": "color", "color": "#abcdef"},
            "#abcdef",
            id="color-source",
        ),
    ],
)
def test_theme_source_follows_the_palette_setting(
    values: dict[str, str], expected: str
) -> None:
    assert SchoolSettings(**values).theme_source == expected


# --- Branding saved from the web (odd/tasks/role-panels.md T3) ---


def test_load_school_settings_reads_the_saved_branding(tmp_path) -> None:
    """Web values sit above school.toml but below nothing: env is read after them."""
    config = tmp_path / "school.toml"
    config.write_text('[school]\nname = "From the file"\ncolor = "#111111"\n')
    saved = tmp_path / "branding.toml"
    saved.write_text('[school]\nname = "Saved from the web"\ncolor = "#222222"\n')

    loaded = load_school_settings(
        config_path=config, saved_path=saved, environ={}
    )

    assert loaded.name == "Saved from the web"
    assert loaded.color == "#222222"


def test_the_environment_still_wins_over_the_saved_branding(tmp_path) -> None:
    config = tmp_path / "school.toml"
    config.write_text('[school]\nname = "From the file"\n')
    saved = tmp_path / "branding.toml"
    saved.write_text('[school]\nname = "Saved from the web"\n')

    loaded = load_school_settings(
        config_path=config,
        saved_path=saved,
        environ={"SCHOOL_NAME": "From the environment"},
    )

    assert loaded.name == "From the environment"


def test_a_saved_file_with_no_school_table_is_refused(tmp_path) -> None:
    saved = tmp_path / "branding.toml"
    saved.write_text("[other]\nname = 'nope'\n")

    with pytest.raises(ValueError, match=r"\[school\]"):
        load_school_settings(
            config_path=tmp_path / "missing.toml", saved_path=saved, environ={}
        )


def test_an_absent_saved_file_changes_nothing(tmp_path) -> None:
    loaded = load_school_settings(
        config_path=tmp_path / "missing.toml",
        saved_path=tmp_path / "branding.toml",
        environ={},
    )

    assert loaded.name == "School DB"
