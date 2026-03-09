"""art.py — ASCII art for the flexcoder brand."""

# 5-row block-letter ASCII art for "FLEXCODER"
FLEXCODER = [
    "█████ ██    █████ ██ ██ █████ █████ ████  █████ ████ ",
    "██    ██    ██    ██ ██ ██    ██ ██ ██ ██ ██    ██ ██",
    "█████ ██    █████  ███  ██    ██ ██ ██ ██ █████ ████ ",
    "██    ██    ██    ██ ██ ██    ██ ██ ██ ██ ██    ██ █ ",
    "██    █████ █████ ██ ██ █████ █████ ████  █████ ██ ██",
]

FLEXCODER_STR = "\n".join(FLEXCODER)

GOODBYE = (
    "\n"
    + "\n".join(f"[#{'4a7fd4'}]{line}[/#{'4a7fd4'}]" for line in FLEXCODER)
    + "\n\nto resume this session:\nflexcoder continue\n"
)
