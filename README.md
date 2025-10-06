## gpt-realtime-starter

## Overview

This starter demonstrates how to connect to OpenAI's gpt-realtime speech-to-speech API using Python and the OpenAI SDK. It includes:

- Basic realtime connection and event logging (`connect.py`)
- Microphone capture and transcription of model output (`connect_and_record.py`)
- Full duplex audio: capture microphone and play assistant audio (`connect_record_and_playback.py`)
- Remote MCP tool usage with GitHub (read-only by default)  (`connect_and_use_a_tool.py`)
- Remote MCP tool usage with approvals (`connect_and_use_a_tool_with_approval.py`)

For background, context, and walkthrough, see the accompanying article: "Creating a realtime voice agent using OpenAI's new gpt-realtime speech-to-speech model" published on dev.to.

## Requirements

- Python 3.10+
- An OpenAI API key with access to gpt-realtime
- Audio I/O:
  - macOS: CoreAudio (works out of the box). For reliability, install PortAudio with Homebrew: `brew install portaudio`.
  - Linux: Ensure ALSA/PulseAudio and PortAudio development libraries are installed.
  - Windows: Uses WASAPI, consider installing PortAudio via your package manager or wheels.

## Installation

You can use either uv or pip.

### Using uv (recommended)

```bash
uv sync
```

### Using pip

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -U pip
pip install -e .
```

## Environment variables

- `OPENAI_API_KEY` (required): Your OpenAI API key.
- `GITHUB_PAT` (optional): GitHub Personal Access Token (read-only recommended) to enable the GitHub MCP server in `connect_and_use_a_tool.py` and `connect_and_use_a_tool_with_approval.py`.

## Quick start

### Basic connection (log events only)

```bash
OPENAI_API_KEY=... python connect.py
```

### Microphone capture

```bash
OPENAI_API_KEY=... python connect_and_record.py
```

### Full duplex (record and playback)

Use headphones to avoid echo/feedback.

```bash
OPENAI_API_KEY=... python connect_record_and_playback.py
```

### Use a remote MCP tool (GitHub)

Provides read-only GitHub queries via the GitHub MCP server.

```bash
OPENAI_API_KEY=... GITHUB_PAT=... python connect_and_use_a_tool.py
```
or with additional interactive approvals:

```shell
OPENAI_API_KEY=... GITHUB_PAT=... python connect_and_use_a_tool_with_approval.py

```

## Project structure

- `connect.py`: Creates a realtime session, logs server events.
- `connect_and_record.py`: Streams microphone audio to the model, logs transcript segments.
- `connect_record_and_playback.py`: Adds audio playback for assistant audio deltas.
- `connect_and_use_a_tool.py`: Enables an MCP server (GitHub).
- `connect_and_use_a_tool_with_approval.py`: Demonstrates allow/deny lists and interactive approvals.
- `pyproject.toml`: Dependencies (`openai`, `numpy`, `sounddevice`, `websockets`).

## Audio notes

- Sample rate: 24kHz, mono, 16-bit PCM to match `gpt-realtime`.
- Headphones strongly recommended to avoid the model hearing itself (no echo cancellation).
- If your default device is incorrect, set input/output device explicitly with `sounddevice` or system settings.

## Remote GitHub MCP integration

`connect_and_use_a_tool.py` configures the GitHub MCP server via:

- `server_url`: `https://api.githubcopilot.com/mcp/`
- `authorization`: your `GITHUB_PAT` (recommend read-only scopes)
- `allowed_tools`: explicit list of read-only tools the agent may use
- `require_approval`: allow read-only tools without approval, require approval for sensitive tools

A simple interactive approval loop has been implemented:

- When the server emits an approval request, a prompt asks you to confirm.
- Your approval/denial is sent back using a `conversation.item.create` event containing an `mcp_approval_response`.
- On successful tool completion, the code triggers a `response.create` so the assistant speaks back with the result.

## Caveats and limitations

- Echo/feedback: No echo cancellation is implemented. Use headphones, otherwise the model will interrupt itself.
- Backpressure: Audio queues may grow if the network stalls. For long sessions, use bounded queues and drop/merge oldest chunks under pressure.
- Graceful shutdown: Pressing Ctrl-C stops the program, but background tasks and audio streams may not close gracefully. For production, use try/finally and cancel tasks on shutdown.
- Devices and rates: If default devices fail, set them explicitly. Ensure the device supports 24 kHz mono PCM or adjust accordingly.
- Security and logs: Use a read-only GitHub PAT. In production, avoid logging sensitive tool arguments or redact/truncate logs.

## Troubleshooting

- "No default input/output device": specify devices via `sounddevice.default.device` or system settings.
- "Invalid sample rate": ensure 24000 Hz is supported, try 48000 and resample if needed.
- No assistant audio: ensure headphones are used and your output device is active.
- Import or wheels errors for `sounddevice`: install PortAudio (e.g., `brew install portaudio` on macOS) and reinstall `sounddevice`.

## License

Apache License 2.0

