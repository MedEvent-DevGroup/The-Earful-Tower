# Agent onboarding prompt — The Earful Tower

> Paste this into ChatGPT, Copilot, or any other AI agent to onboard it on this project.

---

You are helping me maintain and extend a local Windows desktop app called **The Earful Tower**.

## Project location

All files are at `C:\Dev\audio-extraction\` on my Windows machine (Alienware Aurora R16, Windows 11, RTX 4090 24 GB, Python 3.11).

## What it does

The Earful Tower is a local audio transcription app with speaker diarization. It:
- Takes an audio file (m4a, mp3, wav, etc.) as input
- Detects and separates speakers using **pyannote.audio 3.1**
- Transcribes speech using **faster-whisper large-v3**
- Outputs a timestamped transcript (`.txt`), markdown (`.md`), subtitles (`.srt`), and/or a waveform video with subtitles (`.mkv`)
- Supports Canadian French and English
- Runs entirely locally — no cloud, no API calls for transcription
- Has a CustomTkinter GUI with a splash screen, launched via a `.lnk` shortcut

## Project structure

```
C:\Dev\audio-extraction\
├── The Earful Tower.lnk      — shortcut to launch the app
├── README.md                  — full project documentation
├── _template.md               — template for new connector files
├── .gitignore
├── icon.ico                   — app icon (ear emoji on dark background)
├── connectors\
│   └── huggingface-read.md    — HuggingFace read token (gitignored)
├── .venv\                     — Python 3.11 virtual environment
└── src\
    ├── app.py                 — CustomTkinter GUI + splash screen
    ├── transcribe_3speakers.py — full pipeline, also usable as CLI
    ├── i18n.py                — i18n helper (JSON locale files, auto-detect, t() API)
    ├── locales\
    │   ├── en.json            — English UI strings
    │   ├── fr.json            — French Canadian UI strings
    │   └── _template.json     — contributor template for new languages
    ├── make_icon.py           — icon generator (one-time use)
    └── requirements.txt       — pinned dependencies
```

## Key files

- **`src/app.py`** — the GUI. Uses CustomTkinter. Shows a splash screen on launch (plain tkinter, shown before heavy imports). Runs the pipeline in a background thread and streams log output to the UI via a queue polled with `after()`. Has an independent UI language selector (top-right, 🌐) and a transcription language selector; they are independent.
- **`src/transcribe_3speakers.py`** — the pipeline. Exposes a `run()` function used by both the GUI and CLI. Stages: ffmpeg → 16 kHz WAV, pyannote diarization, faster-whisper transcription, speaker assignment by temporal overlap, output writing.
- **`src/i18n.py`** — lightweight i18n. `I18n` class with `t(key, **kwargs)` dot-notation lookup, English fallback for missing keys, `set_lang()` for runtime switching, `available()` for locale discovery. Auto-detects Windows locale via stdlib `locale.getdefaultlocale()`. Add a new language by dropping a JSON file in `src/locales/`.

## Tech stack

| Library | Version | Role |
|---|---|---|
| customtkinter | 5.2.2 | Desktop GUI |
| faster-whisper | 1.1.0 | Transcription (CTranslate2 backend) |
| pyannote.audio | 3.3.2 | Speaker diarization |
| speechbrain | 1.0.2 | pyannote dependency |
| huggingface_hub | 0.25.2 | Model downloads |
| torch + torchaudio | 2.4.1 (cu121) | GPU inference |
| ffmpeg | system install | Audio conversion |

## Critical dependency constraints — do not change these without reading first

- **`huggingface_hub` must stay at `0.25.2`** — versions ≥ 0.26 removed the `use_auth_token` kwarg that pyannote.audio 3.3.2 still uses internally. Upgrading breaks diarization.
- **`speechbrain` must stay at `1.0.2`** — version 1.1+ has a lazy-import that collides with `pytorch_lightning`'s `inspect.stack()` call, crashing on pipeline load.
- **`torch` / `torchaudio` must stay at `2.4.1`** — torch 2.6+ flipped `torch.load(weights_only=True)` to default-on, which breaks `pyannote.audio 3.3.2` (`omegaconf.ListConfig` not in safe-globals allowlist) and `speechbrain 1.0.2` checkpoint loading. There are open Dependabot alerts on torch (GHSA-3749-ghw9-m3mg, GHSA-887c-mr87-cxwp, GHSA-53q9-r3pm-6pq6) — they are dismissed as `tolerable_risk` because the DoS paths need crafted tensors not reachable from the audio pipeline and the RCE path needs an attacker-controlled checkpoint we never load (we only pull from the `pyannote` and `speechbrain` HuggingFace orgs; faster-whisper uses CTranslate2, not `torch.load`). Re-evaluate when bumping pyannote to 4.x or adding any user-supplied model path.
- **Do not add Gradio** — its dependency on `huggingface_hub >= 0.33.5` is incompatible with the above constraint. CustomTkinter was chosen specifically to avoid this conflict.

## HuggingFace token

Stored in `connectors\huggingface-read.md`. The pipeline reads it at runtime using a regex (`hf_\S+`). The token needs read access to:
- `pyannote/speaker-diarization-3.1`
- `pyannote/segmentation-3.0`
Both model terms must be accepted on huggingface.co before the token works for those models.

## i18n system

- All UI strings live in `src/locales/<lang>.json` using dot-notation keys (e.g. `settings.header`, `phases.stage_1`)
- `_i18n = I18n()` is a module-level singleton in `app.py`; call `_i18n.t("key")` or `_i18n.t("key", placeholder=value)`
- UI language and transcription language are **independent** — separate selectors
- UI language auto-detects from Windows locale on first launch; user can override in the 🌐 menu (top-right corner)
- To add a new language: copy `src/locales/_template.json`, rename to `<lang>.json`, fill in strings — it will appear in the selector automatically
- Do **not** change key names in JSON files — they are referenced by string in app.py

## Validation rules currently enforced

- Number of speakers: integer, 1–8
- Speaker names: trailing commas and empty entries are stripped
- If fewer names are provided than speakers detected, extras fall back to letters (A, B, C…)
- Audio extension: soft warning shown for non-audio files, but ffmpeg still attempts conversion

## How to run

```powershell
# GUI
Double-click "The Earful Tower.lnk"

# CLI
cd C:\Dev\audio-extraction
.\.venv\Scripts\Activate.ps1
python src\transcribe_3speakers.py "path\to\audio.m4a" --speakers 3 --names "Alice,Bob,Charlie" --lang fr --formats txt,srt [--initial-prompt "domain hint"] [--preview 60] [--no-timestamps] [--out-dir "C:\output"]
```

## Wiki

The project has a GitHub Wiki with user-facing documentation. It is a **separate git repository** from the main code.

- **Live URL**: https://github.com/MedEvent-DevGroup/The-Earful-Tower/wiki
- **Local clone**: `C:\Dev\earful-wiki\`
- **Remote**: `https://github.com/MedEvent-DevGroup/The-Earful-Tower.wiki.git`
- **Default branch**: `master`

### Pages

| File | Wiki page | Contents |
|---|---|---|
| `Home.md` | Home | Overview, page index, quick links |
| `Installation.md` | Installation | Prerequisites, download, setup steps |
| `Usage-Guide.md` | Usage Guide | Every UI control explained |
| `CLI-Reference.md` | CLI Reference | All flags, examples, exit codes |
| `Adding-a-Language.md` | Adding a Language | Locale contributor guide |
| `Troubleshooting.md` | Troubleshooting | Common errors and fixes |
| `Dependency-Notes.md` | Dependency Notes | Pinned versions and why |
| `Privacy-and-Security.md` | Privacy and Security | What data goes where |
| `_Sidebar.md` | *(sidebar)* | Navigation shown on every page |

### When to update the wiki

Update the relevant wiki page(s) whenever you make these types of changes to the main repo:

| Change | Update |
|---|---|
| New CLI flag or changed default | `CLI-Reference.md` |
| New output format or UI option | `Usage-Guide.md` + `CLI-Reference.md` |
| New or changed prerequisite | `Installation.md` |
| Dependency version change | `Dependency-Notes.md` |
| New known error or fix | `Troubleshooting.md` |
| Privacy-relevant network behaviour | `Privacy-and-Security.md` |
| New language added | `Adding-a-Language.md` (if process changes) |

### How to update

```powershell
cd C:\Dev\earful-wiki
# edit the relevant .md file(s)
git add <file>
git commit -m "docs: describe what changed"
git push origin master
```
