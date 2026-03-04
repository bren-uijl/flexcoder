"""Entrypoint for FlexCoder."""

from __future__ import annotations

from .cli import build_parser, dispatch


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return dispatch(args)


if __name__ == "__main__":
    raise SystemExit(main())
