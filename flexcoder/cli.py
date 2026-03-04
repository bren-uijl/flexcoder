"""CLI parser and command dispatch."""

from __future__ import annotations

import argparse

from .chatlog import ChatLogStore
from .providers import provider_help, set_model, set_ollama_model, set_provider
from .session import Session
from .settings_cmd import list_settings, set_setting


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flexcoder", description="FlexCoder CLI")
    subparsers = parser.add_subparsers(dest="command")

    providers_parser = subparsers.add_parser("providers", help="Set or show provider")
    providers_parser.add_argument("provider", nargs="?", help="Provider name")

    settings_parser = subparsers.add_parser("settings", help="View or set settings")
    settings_parser.add_argument("key", nargs="?", help="Setting key")
    settings_parser.add_argument("value", nargs="?", help="Setting value")

    ollama_parser = subparsers.add_parser("ollama", help="Use an Ollama model")
    ollama_parser.add_argument("model", help="Model name, e.g. gemma3:3b")

    subparsers.add_parser("continue", help="Resume latest session")

    model_parser = subparsers.add_parser("model", help="Set model directly")
    model_parser.add_argument("model", help="Model name")

    return parser


def dispatch(args: argparse.Namespace) -> int:
    command = args.command

    if command == "providers":
        if args.provider:
            print(set_provider(args.provider))
        else:
            print(provider_help())
        return 0

    if command == "settings":
        if args.key and args.value is not None:
            print(set_setting(args.key, args.value))
        else:
            print(list_settings())
        return 0

    if command == "ollama":
        print(set_ollama_model(args.model))
        return 0

    if command == "model":
        print(set_model(args.model))
        return 0

    if command == "continue":
        resume = ChatLogStore().latest()
        Session(resume_file=resume).run()
        return 0

    Session().run()
    return 0
