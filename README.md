> [!NOTE]
> There's a error after fechting models, i am fixing it.
# flexcoder

AI coding assistant TUI — alternative to opencode / claude code / codex.

## Install

```bash
pip install flexcoder
```

## File structure

```
flexcoder/
├── pyproject.toml
├── config.toml.default          template for ~/.flexcoder/config.toml
└── flexcoder/
    ├── main.py                  CLI entry point  (print("initialisation...") line 1)
    ├── config.py                TOML config loader/saver
    ├── providers.py             provider registry + verified fetch endpoints
    ├── sessions.py              session persistence → ~/.flexcoder/sessions/
    ├── ai.py                    AI backends (all 6 providers)
    ├── tools.py                 tool execution (create_file, shell, etc.)
    ├── system_prompt.py         dynamic system prompt (OS, shell, tree, tools)
    ├── art.py                   ASCII art
    ├── flexcoder.tcss           TUI stylesheet
    └── screens/
        ├── chat.py              main chat TUI
        ├── help.py              Ctrl+H help overlay
        ├── selector.py          Ctrl+P provider/model picker
        ├── provider_settings.py Ctrl+E API keys + Fetch Models
        ├── ai_settings.py       Ctrl+T temperature / max tokens / …
        └── session_browser.py   Ctrl+S session browser
```

## Usage

```bash
flexcoder                           # start with saved config
flexcoder ollama gemma3:3b          # start with Ollama gemma3:3b
flexcoder continue                  # resume most recent session
flexcoder continue <session-id>     # resume specific session
flexcoder providers                 # provider settings TUI (standalone)
flexcoder settings                  # AI settings TUI (standalone)
flexcoder sessions                  # session browser TUI (standalone)
```

## First-time setup

1. `flexcoder`  →  press **Ctrl+E**
2. Select provider, paste API key, click **Save Key**
3. Click **Fetch Models**  (queries the provider's live API)
4. Click **Done**
5. Press **Ctrl+P** → select model → Confirm
6. Start chatting

## Keyboard shortcuts

| Key    | Action                           |
|--------|----------------------------------|
| Ctrl+A | Toggle auto-approve (AUTO/MANUAL)|
| Ctrl+O | Toggle output (OUT/QUIET)        |
| Ctrl+H | Help                             |
| Ctrl+N | New session                      |
| Ctrl+S | Session browser                  |
| Ctrl+P | Provider / model selector        |
| Ctrl+E | Provider settings (API keys)     |
| Ctrl+T | AI generation settings           |
| Ctrl+L | Clear chat                       |
| Esc    | Interrupt / cancel               |
| Ctrl+C | Quit                             |

## Model fetch endpoints (verified March 2026)

| Provider   | Endpoint                                                              |
|------------|-----------------------------------------------------------------------|
| Ollama     | `GET http://localhost:11434/api/tags`                                 |
| Claude     | `GET https://api.anthropic.com/v1/models`  (x-api-key header)        |
| ChatGPT    | `GET https://api.openai.com/v1/models`     (Bearer token)            |
| Gemini     | `GET https://generativelanguage.googleapis.com/v1beta/models?key=…`  |
| Mistral    | `GET https://api.mistral.ai/v1/models`     (Bearer token)            |
| OpenRouter | `GET https://openrouter.ai/api/v1/models`  (Bearer token)            |

## AI tools available to the model

| Tool             | Syntax                                                        |
|------------------|---------------------------------------------------------------|
| Create file      | `<create_file=[path]>content</create_file>`                  |
| Move file        | `<move_file source=[old] destination=[new] />`               |
| Read file        | `<read_file=[path] />`                                       |
| Create directory | `<create_directory=[path] />`                                |
| Search & replace | `<search_replace=[file]><search>…</search><replace>…</replace></search_replace>` |
| Shell command    | `<shell>command</shell>`                                     |
| Insert text      | `<insert=[file]><for>…</for><after>…</after><text>…</text></insert>` |

## Session storage

Sessions live in `~/.flexcoder/sessions/<session-id>.json`.  
Resume any session: `flexcoder continue 20250306-143022-a1b2c3`
