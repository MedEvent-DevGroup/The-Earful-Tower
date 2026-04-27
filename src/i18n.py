"""Minimal i18n helper for The Earful Tower.

Usage in app code:
    from i18n import I18n
    _i18n = I18n()          # auto-detects Windows locale, falls back to "en"
    t = _i18n.t             # shorthand
    print(t("app.title"))
    print(t("errors.bad_ext", ext=".xyz"))
    _i18n.set_lang("fr")    # switch at runtime
"""

from __future__ import annotations

import json
import locale
from pathlib import Path
from typing import Any

LOCALES_DIR = Path(__file__).parent / "locales"

# Native-language display names shown in the language selector.
# Key = locale file stem, Value = how it appears in the UI dropdown.
_DISPLAY_NAMES: dict[str, str] = {
    "en": "English",
    "fr": "Français (CA)",
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def detect_system_locale() -> str:
    """Return the best-matching available locale code for the running system."""
    try:
        code = locale.getdefaultlocale()[0] or ""
        lang = code.split("_")[0].lower()
        available = _available_codes()
        return lang if lang in available else "en"
    except Exception:
        return "en"


def _available_codes() -> set[str]:
    return {p.stem for p in LOCALES_DIR.glob("*.json") if not p.stem.startswith("_")}


def _flatten(d: dict, prefix: str = "") -> dict[str, str]:
    """Recursively flatten a nested dict into dot-notation keys."""
    out: dict[str, str] = {}
    for k, v in d.items():
        full = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flatten(v, full))
        else:
            out[full] = str(v)
    return out


# ---------------------------------------------------------------------------
# I18n class
# ---------------------------------------------------------------------------

class I18n:
    def __init__(self, lang: str | None = None) -> None:
        self._fallback: dict[str, str] = {}
        self._strings: dict[str, str] = {}
        self._lang: str = "en"

        # Always load English as the fallback layer first
        self._fallback = _flatten(self._read_json("en"))
        self._strings = dict(self._fallback)

        # Then load the requested (or auto-detected) language
        target = lang if lang else detect_system_locale()
        if target != "en":
            self.set_lang(target)

    # ── public interface ──────────────────────────────────────────────────────

    def set_lang(self, lang: str) -> None:
        """Switch to a different locale. Falls back to English for missing keys."""
        data = self._read_json(lang)
        if data:
            self._lang = lang
            self._strings = _flatten(data)
        # else: silently keep current language (unknown locale file)

    @property
    def lang(self) -> str:
        return self._lang

    def t(self, key: str, **kwargs: Any) -> str:
        """Translate *key* with optional format placeholders.

        Falls back to the English string, then to the raw key if nothing matches.
        """
        val = self._strings.get(key) or self._fallback.get(key, key)
        if kwargs:
            try:
                return val.format(**kwargs)
            except (KeyError, ValueError):
                return val
        return val

    @staticmethod
    def available() -> dict[str, str]:
        """Return {lang_code: display_name} for every *.json in locales/."""
        result: dict[str, str] = {}
        for p in sorted(LOCALES_DIR.glob("*.json")):
            if p.stem.startswith("_"):
                continue
            result[p.stem] = _DISPLAY_NAMES.get(p.stem, p.stem)
        return result

    # ── private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _read_json(lang: str) -> dict:
        path = LOCALES_DIR / f"{lang}.json"
        if not path.exists():
            return {}
        try:
            with path.open(encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
