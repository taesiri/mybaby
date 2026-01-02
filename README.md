# mybaby

Minimal Flask project scaffold using uv, ruff, and Gemini.

## Setup (uv only)

```bash
uv venv
uv pip install -e '.[dev]'
```

Create a `.env` file with your Gemini credentials:

```bash
cp .env.example .env
```

Set `GEMINI_API_KEY` in `.env` (do not commit it).

## Run

```bash
uv run python -m mybaby.app
```

Then open http://127.0.0.1:5000 and upload 1-5 ultrasound images.

The app uses fixed Gemini models: `gemini-3-pro-preview` (chat/prompting) and
`gemini-3-pro-image-preview` (image generation).

## Standalone sample

```bash
uv run python scripts/run_sample.py
```

## Lint

```bash
uv run ruff check .
```
