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
    + FLEXCODER_STR
    + "\n\nto resume this session:\nflexcoder continue\n"
)
