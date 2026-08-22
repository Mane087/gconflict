from pathlib import Path

import gconflict.ui
from gconflict.ui.tokens import TOKENS, TokenApp


STYLESHEET = Path(gconflict.ui.__file__).parent / "app.tcss"


def test_stylesheet_ships_with_the_package() -> None:
    assert STYLESHEET.is_file()


def test_tokens_carry_every_design_value() -> None:
    assert TOKENS == {
        "surface-0": "#0b0d12",
        "surface-1": "#10131a",
        "surface-2": "#12151d",
        "surface-3": "#1c202b",
        "line": "#272c39",
        "text-1": "#d6dae3",
        "text-2": "#a4abba",
        "text-3": "#79808f",
        "text-4": "#4d5462",
        "text-5": "#343b48",
        "current": "#e8a44c",
        "current-bg": "#241c10",
        "current-line": "#8a6b34",
        "current-text": "#f0d3a4",
        "incoming": "#4ca8e8",
        "incoming-bg": "#10202c",
        "incoming-line": "#35708f",
        "incoming-text": "#a8d6f5",
        "ok": "#6fbf73",
        "danger": "#d9645f",
    }


async def test_token_app_publishes_the_tokens_as_css_variables() -> None:
    async with TokenApp().run_test() as pilot:
        variables = pilot.app.get_css_variables()
    for name, value in TOKENS.items():
        assert variables[name] == value
