# flexcoder

FlexCoder is a dependency-free Python CLI AI coding assistant.

## Install

```bash
pip install -e .
```

## Configure providers

```bash
# OpenAI
flexcoder providers openai
flexcoder model gpt-4o-mini
export OPENAI_API_KEY="your-key"  # or: flexcoder settings openai_api_key your-key

# Ollama
flexcoder providers ollama
flexcoder ollama gemma3:3b
# optional: flexcoder settings ollama_base_url http://127.0.0.1:11434
```

## Usage

```bash
flexcoder
flexcoder settings
flexcoder settings temperature 0.4
flexcoder continue
```

Chat logs are stored in `$USERPROFILE/.flexcoder/chatlogs`.
