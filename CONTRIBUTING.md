# Contributing to The Earful Tower

Thanks for your interest! Contributions are welcome — here's how to get started.

## Adding a language

The easiest contribution. No Python knowledge required.

1. Copy `src/locales/_template.json` → `src/locales/<lang>.json`  
   Use the [BCP 47](https://en.wikipedia.org/wiki/IETF_language_tag) language code (e.g. `es`, `de`, `pt`, `ja`)
2. Fill in every string value — do not change key names
3. Add your language's display name to `src/i18n.py` in the `_DISPLAY_NAMES` dict
4. Test: launch the app, select your language in the 🌐 menu, verify all labels
5. Open a pull request

## Reporting a bug

Open an issue and include:
- Your OS and Python version
- GPU model (or "CPU only")
- The full error message / traceback from the Log tab

## Submitting code

1. Fork the repo and create a branch: `git checkout -b my-feature`
2. Make your changes — keep the critical dependency constraints in `src/requirements.txt` (see README)
3. Test with a short audio file using `--preview 60`
4. Open a pull request with a clear description of what changed and why

## Dependency constraints

Before changing any pinned version in `requirements.txt`, read the notes in the README.  
The `huggingface_hub` and `speechbrain` pins in particular will break the pipeline if bumped carelessly.
