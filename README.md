# flexcoder-non-release

FlexCoder is a Python CLI coding assistant prototype.

## Install

```bash
pip install -e .
```

## Usage

```bash
flexcoder
flexcoder providers ollama
flexcoder model gemma3:3b
flexcoder ollama gemma3:3b
flexcoder settings
flexcoder settings temperature 0.4
flexcoder continue
```

Chat logs are stored in `$USERPROFILE/.flexcoder/chatlogs`.
