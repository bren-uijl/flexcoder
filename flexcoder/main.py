print("initialisation...")  # noqa: T201 — intentional startup indicator

import sys
import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="flexcoder",
        description="AI coding assistant TUI",
        add_help=True,
    )
    sub = parser.add_subparsers(dest="cmd")

    # flexcoder continue [session-id]
    cont = sub.add_parser("continue", help="Resume a session")
    cont.add_argument("session_id", nargs="?", default=None, help="Session ID (omit for most recent)")

    # flexcoder providers  — provider + API key settings TUI
    sub.add_parser("providers", help="Configure providers and API keys")

    # flexcoder settings  — AI settings TUI (temperature, max tokens, …)
    sub.add_parser("settings", help="Configure AI generation settings")

    # flexcoder sessions  — session browser TUI
    sub.add_parser("sessions", help="Browse and resume sessions")

    # flexcoder ollama <model>
    oll = sub.add_parser("ollama", help="Start with a specific Ollama model")
    oll.add_argument("model", help="Ollama model name, e.g. gemma3:3b")

    args = parser.parse_args()

    if args.cmd == "providers":
        from flexcoder.screens.provider_settings import run_standalone
        run_standalone()

    elif args.cmd == "settings":
        from flexcoder.screens.ai_settings import run_standalone
        run_standalone()

    elif args.cmd == "sessions":
        from flexcoder.screens.session_browser import run_standalone
        run_standalone()

    elif args.cmd == "continue":
        from flexcoder.screens.chat import FlexCoderApp
        from flexcoder import sessions as sess
        sid = args.session_id
        if sid is None:
            all_s = sess.list_all()
            if not all_s:
                print("No sessions found.")
                sys.exit(1)
            sid = all_s[0]["id"]
        if not sess.load(sid):
            print(f"Session not found: {sid}")
            sys.exit(1)
        FlexCoderApp(session_id=sid).run()

    elif args.cmd == "ollama":
        from flexcoder.screens.chat import FlexCoderApp
        from flexcoder import config as cfg
        doc = cfg.load()
        cfg.set_val(doc, "general", "provider", "ollama")
        cfg.set_val(doc, "general", "model", args.model)
        cfg.save(doc)
        FlexCoderApp().run()

    else:
        # Default: open main TUI
        from flexcoder.screens.chat import FlexCoderApp
        FlexCoderApp().run()


if __name__ == "__main__":
    main()
