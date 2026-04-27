# 🗼 The Earful Tower

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Whisper large-v3](https://img.shields.io/badge/Whisper-large--v3-green.svg)](https://github.com/openai/whisper)
[![pyannote 3.1](https://img.shields.io/badge/pyannote-3.1-green.svg)](https://github.com/pyannote/pyannote-audio)

Local audio transcription with speaker diarization. Runs entirely on your machine — no cloud, no uploads, no data shared.

## What it does

- Converts any audio file to a clean transcript with speaker labels
- Detects and separates speakers automatically using **pyannote.audio 3.1**
- Transcribes in **Canadian French** or **English** using **Whisper large-v3**
- Outputs: timestamped `.txt`, `.md`, `.srt`, or a waveform `.mkv` video with embedded subtitles
- GPU-accelerated on CUDA; falls back to CPU automatically
- Multilingual UI — currently English and French Canadian (add your language by dropping a JSON file in `src/locales/`)

## Platform

**Windows 10/11 only.** The setup script is PowerShell and the GUI uses Windows-specific features. macOS and Linux are not currently supported.

## Before you download — size and time expectations

This app is powerful but heavy. Please read before starting:

| Step | What happens | Download | Disk space | Time (estimate) |
|---|---|---|---|---|
| `setup.ps1` | Installs Python packages incl. PyTorch CUDA | ~2.5 GB | ~5 GB | 5–20 min |
| First launch | Downloads Whisper large-v3 + pyannote models | ~3.3 GB | ~3.3 GB | 5–15 min |
| **Total** | | **~5.8 GB** | **~8.5 GB** | **~30 min** |

After the first launch everything is cached locally. All subsequent runs are **fully offline** and start in seconds.

**GPU strongly recommended.** An NVIDIA GPU (CUDA 12.1) is required for reasonable speed:

| Hardware | 90-minute audio |
|---|---|
| RTX 4090 | ~20–35 min |
| RTX 3060 / 3070 | ~45–75 min |
| CPU only | 3–6 hours |

## Requirements

- Windows 10/11
- Python 3.11 — [download here](https://www.python.org/downloads/releases/python-3119/)
- NVIDIA GPU with CUDA 12.1 drivers (CPU works but see speed table above)
- [ffmpeg](https://ffmpeg.org/download.html) on your system PATH
- ~9 GB free disk space
- A free [HuggingFace](https://huggingface.co) account (for model downloads)

## First-time setup (manual / developer path)

> **End users:** use `setup.ps1` instead — it does all of this for you. See the [latest release](https://github.com/MedEvent-DevGroup/The-Earful-Tower/releases/latest).

**1. Clone and create the virtual environment**
```powershell
git clone https://github.com/MedEvent-DevGroup/The-Earful-Tower.git
cd The-Earful-Tower
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install torch==2.4.1 torchaudio==2.4.1 --index-url https://download.pytorch.org/whl/cu121
pip install -r src\requirements.txt
```

**2. Add your HuggingFace token**

Create the `connectors/` folder and a token file inside it:
```
connectors\huggingface-read.md
```
See `_template.md` for the exact format. Get a free read-only token at [huggingface.co](https://huggingface.co) → Settings → Access Tokens → New token.

**3. Accept pyannote model terms** (one-time, in browser while signed into HuggingFace)
- https://huggingface.co/pyannote/speaker-diarization-3.1
- https://huggingface.co/pyannote/segmentation-3.0

**4. Launch**
```powershell
.\.venv\Scripts\Activate.ps1
python src\app.py
```
Or create a desktop shortcut pointing to `python src\app.py` in the project folder.

## Project structure

```
The-Earful-Tower/
├── README.md
├── AGENT_PROMPT.md            — onboarding prompt for AI coding assistants
├── _template.md               — template for connector credential files
├── .gitignore
├── icon.ico                   — app icon
├── connectors/                — API credentials (gitignored, never committed)
│   └── huggingface-read.md    — your HF token
├── .venv/                     — Python environment (gitignored)
└── src/
    ├── app.py                 — GUI (CustomTkinter + splash screen)
    ├── transcribe_3speakers.py — full pipeline (also usable as CLI)
    ├── i18n.py                — UI translation helper
    ├── locales/
    │   ├── en.json            — English strings
    │   ├── fr.json            — French Canadian strings
    │   └── _template.json     — template for adding a new language
    ├── make_icon.py           — icon generator (one-time use)
    └── requirements.txt       — pinned dependencies
```

## CLI usage

The pipeline can be run without the GUI:

```powershell
.\.venv\Scripts\Activate.ps1
python src\transcribe_3speakers.py "path\to\audio.m4a" `
    --speakers 3 `
    --names "Alice,Bob,Charlie" `
    --lang fr `
    --formats txt,srt
```

| Flag | Default | Description |
|---|---|---|
| `--speakers` | `3` | Number of speakers (1–8) |
| `--names` | — | Speaker names, most talkative first, comma-separated |
| `--lang` | `fr` | Language: `fr` (Canadian French) or `en` |
| `--no-timestamps` | — | Omit timestamps from `.txt` / `.md` |
| `--formats` | `txt` | Comma-separated: `txt`, `md`, `srt`, `mkv`, `json` |
| `--out-dir` | same as audio | Output folder |
| `--preview` | — | Process only the first N seconds (for testing) |
| `--initial-prompt` | — | Custom context hint for Whisper (e.g. domain vocabulary) |

## Adding a language

1. Copy `src/locales/_template.json` → `src/locales/<lang>.json` (e.g. `es.json`)
2. Fill in every string value — do not change key names
3. Relaunch the app — your language appears in the 🌐 selector automatically

## Privacy

All processing happens locally on your machine.

- **Audio data**: never transmitted anywhere
- **Model downloads**: on first launch, pyannote model weights (~1 GB) are fetched from HuggingFace. Their servers log your token and IP for that request. No audio is involved. All subsequent runs are fully offline.

## Dependency notes

Versions are pinned in `src/requirements.txt`. Key constraints — do not change these without reading the notes:

| Package | Pinned to | Reason |
|---|---|---|
| `huggingface_hub` | `0.25.2` | ≥ 0.26 removed `use_auth_token` kwarg that pyannote still uses internally |
| `speechbrain` | `1.0.2` | 1.1+ has a lazy-import that conflicts with `pytorch_lightning` |
| `gradio` | not used | requires `huggingface_hub ≥ 0.33.5` — incompatible with pyannote pin |

## Credits

Created by [Eddy](https://github.com/eddyafram) · Built with [Claude](https://claude.ai) (Anthropic)

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for details.
