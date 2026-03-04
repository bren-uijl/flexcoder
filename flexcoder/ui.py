"""Terminal user interface rendering."""

from __future__ import annotations

import os
from typing import Iterable

from .config import Settings

HEADER = r"""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                                                ┃
┃ █████ ██    █████ ██ ██ █████ █████ ████  █████ ████      Selected provider:  Ctrl+P           ┃
┃ ██    ██    ██    ██ ██ ██    ██ ██ ██ ██ ██    ██ ██     {provider:<35}┃
┃ █████ ██    █████  ███  ██    ██ ██ ██ ██ █████ ████                                           ┃
┃ ██    ██    ██    ██ ██ ██    ██ ██ ██ ██ ██    ██ █      Selected model:     Ctrl+M           ┃
┃ ██    █████ █████ ██ ██ █████ █████ ████  █████ ██ ██     {model:<35}┃
┃                                                                                                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
"""

FOOTER = r"""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                                                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
esc = interrupt                                                                      ctrl+c = quit
"""

EXIT_BANNER = r"""
█████ ██    █████ ██ ██ █████ █████ ████  █████ ████
██    ██    ██    ██ ██ ██    ██ ██ ██ ██ ██    ██ ██
█████ ██    █████  ███  ██    ██ ██ ██ ██ █████ ████
██    ██    ██    ██ ██ ██    ██ ██ ██ ██ ██    ██ █
██    █████ █████ ██ ██ █████ █████ ████  █████ ██ ██


to resume this session:

flexcoder continue
"""


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def render(settings: Settings, history: Iterable[str]) -> None:
    clear_screen()
    print(HEADER.format(provider=settings.provider, model=settings.model))
    for line in history:
        print(line)
    print(FOOTER)
