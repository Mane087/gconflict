from pathlib import Path

import gconflict.ui


STYLESHEET = Path(gconflict.ui.__file__).parent / "app.tcss"


def test_stylesheet_ships_with_the_package() -> None:
    assert STYLESHEET.is_file()


def test_stylesheet_defines_every_design_token() -> None:
    text = STYLESHEET.read_text(encoding="utf-8")
    for token, value in [
        ("$surface-0", "#0b0d12"),
        ("$surface-1", "#10131a"),
        ("$surface-2", "#12151d"),
        ("$surface-3", "#1c202b"),
        ("$line", "#272c39"),
        ("$text-1", "#d6dae3"),
        ("$text-2", "#a4abba"),
        ("$text-3", "#79808f"),
        ("$text-4", "#4d5462"),
        ("$text-5", "#343b48"),
        ("$current", "#e8a44c"),
        ("$current-bg", "#241c10"),
        ("$current-line", "#8a6b34"),
        ("$current-text", "#f0d3a4"),
        ("$incoming", "#4ca8e8"),
        ("$incoming-bg", "#10202c"),
        ("$incoming-line", "#35708f"),
        ("$incoming-text", "#a8d6f5"),
        ("$ok", "#6fbf73"),
        ("$danger", "#d9645f"),
    ]:
        assert f"{token}: {value};" in text
