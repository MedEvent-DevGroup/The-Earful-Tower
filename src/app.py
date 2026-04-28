"""Local desktop GUI for audio transcription with speaker diarization.

Launch:  python app.py
"""

from __future__ import annotations

# ── Splash screen — shown immediately, before any heavy imports ───────────────
import tkinter as tk
from pathlib import Path

_ROOT = Path(__file__).parent
_ICON = _ROOT.parent / "icon.ico"

_splash = tk.Tk()
_splash.overrideredirect(True)          # no title bar / border
_splash.configure(bg="#12183B")
_splash.attributes("-topmost", True)

_SW, _SH = _splash.winfo_screenwidth(), _splash.winfo_screenheight()
_W, _H   = 430, 310
_splash.geometry(f"{_W}x{_H}+{(_SW - _W)//2}+{(_SH - _H)//2}")

try:
    _splash.iconbitmap(str(_ICON))
except Exception:
    pass

tk.Label(_splash, text="👂",
         font=("Segoe UI Emoji", 54),
         bg="#12183B", fg="white").pack(pady=(18, 4))

tk.Label(_splash, text="The Earful Tower",
         font=("Segoe UI", 17, "bold"),
         bg="#12183B", fg="white").pack()

_status_var = tk.StringVar(value="Starting up…")
tk.Label(_splash, textvariable=_status_var,
         font=("Segoe UI", 10),
         bg="#12183B", fg="#6a9fd8").pack(pady=(5, 0))

# ── credits & privacy notice ──────────────────────────────────────────────────
tk.Frame(_splash, height=1, bg="#2a3a6a").pack(fill="x", padx=24, pady=(14, 10))

tk.Label(_splash,
         text="Created by Eddy  ·  Built with Claude (Anthropic)",
         font=("Segoe UI", 9),
         bg="#12183B", fg="#7a9fc8").pack()

tk.Label(_splash,
         text="🔒  Runs 100% locally — no audio data ever leaves your machine.",
         font=("Segoe UI", 9),
         bg="#12183B", fg="#7a9fc8").pack(pady=(5, 0))

tk.Label(_splash,
         text="On first launch, model weights are downloaded from HuggingFace.",
         font=("Segoe UI", 8),
         bg="#12183B", fg="#4a6a8a").pack(pady=(2, 0))

tk.Label(_splash,
         text="No audio is involved — only your token and IP are logged there.",
         font=("Segoe UI", 8),
         bg="#12183B", fg="#4a6a8a").pack()

_splash.update()

# ── Now do the heavy imports (customtkinter, torch, pyannote via pipeline) ────
import ctypes
import queue
import subprocess
import sys
import threading
from tkinter import filedialog

_status_var.set("Loading UI framework…")
_splash.update()

import customtkinter as ctk

_status_var.set("Loading pipeline…")
_splash.update()

sys.path.insert(0, str(_ROOT))
from i18n import I18n
from transcribe_3speakers import run as run_pipeline

# ── Close splash, proceed with app ───────────────────────────────────────────
_splash.destroy()

# ── Windows taskbar: tell the shell this is a distinct app (not "Python") ────
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "TheEarfulTower.App.1")
except Exception:
    pass

# ── i18n (auto-detect Windows locale, falls back to English) ─────────────────
_i18n = I18n()

# ── Theme ─────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Stable internal codes for the transcription language selector
TX_LANG_CODES = ["fr", "en"]

# Output format codes in display order, grouped.
# Each entry: (group_i18n_key, [format_codes], show_timestamps_option)
FORMAT_GROUPS: list[tuple[str, list[str], bool]] = [
    ("formats.group_text",  ["txt", "md"],   True),   # timestamps opt here
    ("formats.group_video", ["srt", "mkv"],  False),
    ("formats.group_data",  ["json"],        False),
]
FORMAT_DEFAULT_ON = {"txt", "srt"}

# Keys in the pipeline log that signal a phase change
_PHASE_KEYWORDS: list[tuple[str, str]] = [
    ("[stage] 1/4", "phases.stage_1"),
    ("[stage] 2/4", "phases.stage_2"),
    ("[stage] 3/4", "phases.stage_3"),
    ("[stage] 4/4", "phases.stage_4"),
    ("[ffmpeg]",    "phases.stage_1"),
    ("[pyannote]",  "phases.stage_2"),
    ("[whisper]",   "phases.stage_3"),
    ("[airtime]",   "phases.stage_4"),
    ("[out]",       "phases.stage_4"),
    ("ERROR",       "phases.error"),
]

# Spinbox bounds
SPK_MIN, SPK_MAX, SPK_DEFAULT = 1, 8, 3


# ---------------------------------------------------------------------------
# Auto-hiding scrollable frame
# ---------------------------------------------------------------------------

class _AutoHideScrollFrame(ctk.CTkScrollableFrame):
    """CTkScrollableFrame whose scrollbar hides itself when all content fits."""

    def __init__(self, master, **kw) -> None:
        super().__init__(master, **kw)
        # Override the canvas yscrollcommand so we can show/hide the bar
        self._parent_canvas.configure(yscrollcommand=self._auto_scroll_set)

    def _auto_scroll_set(self, lo: str, hi: str) -> None:
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self._scrollbar.grid_remove()   # content fits — hide
        else:
            self._scrollbar.grid()          # overflow — show
        self._scrollbar.set(lo, hi)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("The Earful Tower")

        # Size: tall enough to show all settings comfortably on a 1080p screen.
        # Minimum enforced so nothing gets hidden; scrollable frame handles the rest.
        self.geometry("1100x820")
        self.minsize(860, 620)
        self.resizable(True, True)

        if _ICON.exists():
            self.iconbitmap(str(_ICON))

        self.device: str | None = None

        # Independent language selectors
        self._tx_lang_code: str = "fr"
        self._ui_lang_code: str = _i18n.lang

        # Speaker count (spinbox)
        self._n_speakers: int = SPK_DEFAULT

        # Status key tracking — lets _apply_translations() re-translate the status
        # label when the UI language changes without losing the current state.
        self._status_key:    str  = "progress.idle"
        self._status_kwargs: dict = {}

        self._build_ui()
        self._apply_translations()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)   # top bar  — fixed height
        self.grid_rowconfigure(1, weight=1)   # panels   — stretches

        self._build_top_bar()
        self._build_settings_panel()
        self._build_progress_panel()

    def _build_top_bar(self) -> None:
        bar = ctk.CTkFrame(self, height=36, corner_radius=0, fg_color="transparent")
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(8, 0))
        bar.grid_columnconfigure(0, weight=1)

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(right, text="🌐", font=ctk.CTkFont(size=14)).pack(
            side="left", padx=(0, 4))

        available = _i18n.available()
        self._ui_lang_display_to_code: dict[str, str] = {v: k for k, v in available.items()}

        self._ui_lang_var = ctk.StringVar(value=available.get(_i18n.lang, "English"))
        ctk.CTkOptionMenu(
            right,
            variable=self._ui_lang_var,
            values=list(available.values()),
            width=150,
            command=self._on_ui_language_change,
        ).pack(side="left")

    def _build_settings_panel(self) -> None:
        # Scrollbar appears only when the window is too short to show everything.
        frame = _AutoHideScrollFrame(self)
        frame.grid(row=1, column=0, padx=(12, 6), pady=12, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)

        row = 0

        # app title / subtitle
        self._lbl_app_title = ctk.CTkLabel(
            frame, text="", font=ctk.CTkFont(size=18, weight="bold"))
        self._lbl_app_title.grid(
            row=row, column=0, padx=16, pady=(12, 2), sticky="w"); row += 1

        self._lbl_app_subtitle = ctk.CTkLabel(
            frame, text="", text_color="gray", font=ctk.CTkFont(size=11))
        self._lbl_app_subtitle.grid(
            row=row, column=0, padx=16, pady=(0, 10), sticky="w"); row += 1

        # settings header
        self._lbl_settings_header = ctk.CTkLabel(
            frame, text="", font=ctk.CTkFont(size=16, weight="bold"))
        self._lbl_settings_header.grid(
            row=row, column=0, padx=16, pady=(4, 8), sticky="w"); row += 1

        # ── audio file ──
        self._lbl_audio_file = ctk.CTkLabel(frame, text="")
        self._lbl_audio_file.grid(row=row, column=0, padx=16, sticky="w"); row += 1

        file_row = ctk.CTkFrame(frame, fg_color="transparent")
        file_row.grid(row=row, column=0, padx=16, pady=(0, 8), sticky="ew"); row += 1
        file_row.grid_columnconfigure(0, weight=1)

        self.audio_entry = ctk.CTkEntry(file_row, placeholder_text="")
        self.audio_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self._btn_browse_audio = ctk.CTkButton(
            file_row, text="", width=80, command=self._browse_audio)
        self._btn_browse_audio.grid(row=0, column=1)

        # ── transcription language + speakers (side by side) ──
        two = ctk.CTkFrame(frame, fg_color="transparent")
        two.grid(row=row, column=0, padx=16, pady=(0, 8), sticky="ew"); row += 1
        two.grid_columnconfigure(0, weight=1)
        two.grid_columnconfigure(1, weight=0)

        lang_frame = ctk.CTkFrame(two, fg_color="transparent")
        lang_frame.grid(row=0, column=0, sticky="ew", padx=(0, 16))
        self._lbl_tx_lang = ctk.CTkLabel(lang_frame, text="")
        self._lbl_tx_lang.pack(anchor="w")
        self._opt_tx_lang = ctk.CTkOptionMenu(
            lang_frame,
            values=[],
            width=160,
            command=self._on_tx_lang_change,
        )
        self._opt_tx_lang.pack(fill="x")

        spk_frame = ctk.CTkFrame(two, fg_color="transparent")
        spk_frame.grid(row=0, column=1, sticky="e")
        self._lbl_speakers = ctk.CTkLabel(spk_frame, text="")
        self._lbl_speakers.pack(anchor="w")
        self._build_spinbox(spk_frame)

        # ── speaker names ──
        self._lbl_names = ctk.CTkLabel(frame, text="")
        self._lbl_names.grid(row=row, column=0, padx=16, sticky="w"); row += 1
        self.names_entry = ctk.CTkEntry(frame, placeholder_text="")
        self.names_entry.grid(row=row, column=0, padx=16, pady=(0, 8), sticky="ew"); row += 1

        # ── preview mode ──
        self._lbl_preview = ctk.CTkLabel(frame, text="")
        self._lbl_preview.grid(row=row, column=0, padx=16, sticky="w"); row += 1
        self.preview_entry = ctk.CTkEntry(frame, placeholder_text="")
        self.preview_entry.grid(row=row, column=0, padx=16, pady=(0, 8), sticky="ew"); row += 1

        # ── output formats (grouped) ──────────────────────────────────────────
        self._lbl_formats = ctk.CTkLabel(frame, text="")
        self._lbl_formats.grid(row=row, column=0, padx=16, sticky="w"); row += 1

        self.fmt_vars:      dict[str, ctk.BooleanVar]  = {}
        self._chk_fmt:      dict[str, ctk.CTkCheckBox] = {}
        self._lbl_fmt_grp:  list[ctk.CTkLabel]         = []
        self._fmt_grp_keys: list[str]                  = []

        fmt_outer = ctk.CTkFrame(frame, fg_color="transparent")
        fmt_outer.grid(row=row, column=0, padx=16, pady=(2, 8), sticky="ew"); row += 1
        fmt_outer.grid_columnconfigure(0, weight=1)

        gr = 0
        for gkey, codes, show_ts in FORMAT_GROUPS:
            # group header label
            lbl = ctk.CTkLabel(fmt_outer, text="",
                               font=ctk.CTkFont(size=12, weight="bold"))
            lbl.grid(row=gr, column=0, sticky="w", pady=(8 if gr > 0 else 0, 2))
            self._lbl_fmt_grp.append(lbl)
            self._fmt_grp_keys.append(gkey)
            gr += 1

            # format checkboxes
            for code in codes:
                var = ctk.BooleanVar(value=(code in FORMAT_DEFAULT_ON))
                self.fmt_vars[code] = var
                chk = ctk.CTkCheckBox(fmt_outer, text="", variable=var)
                chk.grid(row=gr, column=0, sticky="w", padx=(14, 0), pady=1)
                self._chk_fmt[code] = chk
                gr += 1

            # timestamps option lives inside the Text group, indented further
            if show_ts:
                self.timestamps_var = ctk.BooleanVar(value=True)
                self._chk_timestamps = ctk.CTkCheckBox(
                    fmt_outer, text="", variable=self.timestamps_var)
                self._chk_timestamps.grid(
                    row=gr, column=0, sticky="w", padx=(28, 0), pady=(4, 2))
                gr += 1

        # ── output folder ──
        self._lbl_outdir = ctk.CTkLabel(frame, text="")
        self._lbl_outdir.grid(row=row, column=0, padx=16, sticky="w"); row += 1

        out_row = ctk.CTkFrame(frame, fg_color="transparent")
        out_row.grid(row=row, column=0, padx=16, pady=(0, 8), sticky="ew"); row += 1
        out_row.grid_columnconfigure(0, weight=1)
        self.outdir_entry = ctk.CTkEntry(out_row, placeholder_text="")
        self.outdir_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._btn_browse_outdir = ctk.CTkButton(
            out_row, text="", width=80, command=self._browse_outdir)
        self._btn_browse_outdir.grid(row=0, column=1)

        # ── open folder when done ──
        self.open_folder_var = ctk.BooleanVar(value=True)
        self._chk_open_folder = ctk.CTkCheckBox(
            frame, text="", variable=self.open_folder_var)
        self._chk_open_folder.grid(
            row=row, column=0, padx=16, pady=(0, 12), sticky="w"); row += 1

        # ── start button ──
        self.start_btn = ctk.CTkButton(
            frame, text="",
            height=42, font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start)
        self.start_btn.grid(row=row, column=0, padx=16, pady=(0, 16), sticky="ew")

    def _build_spinbox(self, parent: ctk.CTkFrame) -> None:
        """Build the ± speaker-count spinbox inside *parent* (packed, not gridded)."""
        sf = ctk.CTkFrame(parent, fg_color="transparent")
        sf.pack(anchor="w")

        ctk.CTkButton(
            sf, text="−", width=28, height=28, font=ctk.CTkFont(size=14),
            command=lambda: self._adj_speakers(-1)).grid(row=0, column=0)

        self._spk_label = ctk.CTkLabel(
            sf, text=str(self._n_speakers), width=36, anchor="center",
            font=ctk.CTkFont(size=14, weight="bold"))
        self._spk_label.grid(row=0, column=1, padx=4)

        ctk.CTkButton(
            sf, text="+", width=28, height=28, font=ctk.CTkFont(size=14),
            command=lambda: self._adj_speakers(1)).grid(row=0, column=2)

    def _adj_speakers(self, delta: int) -> None:
        self._n_speakers = max(SPK_MIN, min(SPK_MAX, self._n_speakers + delta))
        self._spk_label.configure(text=str(self._n_speakers))

    def _build_progress_panel(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.grid(row=1, column=1, padx=(6, 12), pady=12, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        self._lbl_progress_header = ctk.CTkLabel(
            frame, text="", font=ctk.CTkFont(size=16, weight="bold"))
        self._lbl_progress_header.grid(
            row=0, column=0, padx=16, pady=(12, 8), sticky="w")

        self.status_label = ctk.CTkLabel(
            frame, text="", anchor="w", font=ctk.CTkFont(size=13))
        self.status_label.grid(row=1, column=0, padx=16, pady=(0, 6), sticky="ew")

        # Tabs — internal names stay in English (CTkTabview can't rename them)
        self._tabs = ctk.CTkTabview(frame)
        self._tabs.grid(row=2, column=0, padx=16, pady=(0, 12), sticky="nsew")
        self._tabs.add("Log")
        self._tabs.add("Transcript")

        for tab_name in ("Log", "Transcript"):
            self._tabs.tab(tab_name).grid_rowconfigure(0, weight=1)
            self._tabs.tab(tab_name).grid_columnconfigure(0, weight=1)

        self.log_box = ctk.CTkTextbox(
            self._tabs.tab("Log"), wrap="word",
            font=ctk.CTkFont(family="Consolas", size=12))
        self.log_box.grid(row=0, column=0, sticky="nsew")

        self.transcript_box = ctk.CTkTextbox(
            self._tabs.tab("Transcript"), wrap="word",
            font=ctk.CTkFont(family="Consolas", size=12))
        self.transcript_box.grid(row=0, column=0, sticky="nsew")

    # ── translations ──────────────────────────────────────────────────────────

    def _apply_translations(self) -> None:
        """Push current locale strings into every widget that carries text."""
        t = _i18n.t

        self._lbl_app_title.configure(text=t("app.title"))
        self._lbl_app_subtitle.configure(text=t("app.subtitle"))
        self._lbl_settings_header.configure(text=t("settings.header"))
        self._lbl_audio_file.configure(text=t("settings.audio_file"))
        self.audio_entry.configure(placeholder_text=t("settings.audio_placeholder"))
        self._btn_browse_audio.configure(text=t("settings.browse"))

        tx_opts = [t(f"lang_options.{c}") for c in TX_LANG_CODES]
        self._lbl_tx_lang.configure(text=t("settings.language"))
        self._opt_tx_lang.configure(values=tx_opts)
        self._opt_tx_lang.set(t(f"lang_options.{self._tx_lang_code}"))

        self._lbl_speakers.configure(text=t("settings.speakers"))
        self._lbl_names.configure(text=t("settings.names"))
        self.names_entry.configure(placeholder_text=t("settings.names_placeholder"))
        self._lbl_preview.configure(text=t("settings.preview"))
        self.preview_entry.configure(placeholder_text=t("settings.preview_placeholder"))
        self._lbl_formats.configure(text=t("settings.formats"))

        for lbl, key in zip(self._lbl_fmt_grp, self._fmt_grp_keys):
            lbl.configure(text=t(key))
        for code, chk in self._chk_fmt.items():
            chk.configure(text=t(f"formats.{code}"))
        self._chk_timestamps.configure(text=t("settings.timestamps"))

        self._lbl_outdir.configure(text=t("settings.out_dir"))
        self.outdir_entry.configure(placeholder_text=t("settings.out_dir_placeholder"))
        self._btn_browse_outdir.configure(text=t("settings.browse"))
        self._chk_open_folder.configure(text=t("settings.open_folder"))

        if self.start_btn.cget("state") != "disabled":
            self.start_btn.configure(text=t("settings.start_btn"))

        self._lbl_progress_header.configure(text=t("progress.header"))
        self._render_status()

    def _on_ui_language_change(self, display_name: str) -> None:
        code = self._ui_lang_display_to_code.get(display_name, "en")
        _i18n.set_lang(code)
        self._ui_lang_code = code
        self._apply_translations()

    def _on_tx_lang_change(self, display_name: str) -> None:
        for code in TX_LANG_CODES:
            if display_name == _i18n.t(f"lang_options.{code}"):
                self._tx_lang_code = code
                return

    # ── browse helpers ────────────────────────────────────────────────────────

    def _browse_audio(self) -> None:
        t = _i18n.t
        path = filedialog.askopenfilename(
            title=t("browse.audio_title"),
            filetypes=[
                (t("browse.audio_filter"), "*.m4a *.mp3 *.wav *.ogg *.flac *.mp4 *.mkv"),
                (t("browse.all_files"), "*.*"),
            ])
        if path:
            self.audio_entry.delete(0, "end")
            self.audio_entry.insert(0, path)

    def _browse_outdir(self) -> None:
        path = filedialog.askdirectory(title=_i18n.t("browse.outdir_title"))
        if path:
            self.outdir_entry.delete(0, "end")
            self.outdir_entry.insert(0, path)

    # ── pipeline ──────────────────────────────────────────────────────────────

    def _start(self) -> None:
        audio_path = self.audio_entry.get().strip()
        src = Path(audio_path) if audio_path else None
        if not src or not src.exists():
            self._set_status("errors.file_not_found")
            return

        AUDIO_EXTS = {".m4a", ".mp3", ".wav", ".ogg", ".flac", ".mp4", ".mkv", ".aac", ".wma"}
        if src.suffix.lower() not in AUDIO_EXTS:
            self._set_status("errors.bad_ext", ext=src.suffix)
            # soft warning — continue

        names_raw = self.names_entry.get().strip()
        if names_raw and ";" in names_raw:
            self._set_status("errors.names_separator")
            return
        names = [n.strip() for n in names_raw.split(",") if n.strip()] if names_raw else None

        preview_raw = self.preview_entry.get().strip()
        preview_seconds = None
        if preview_raw:
            try:
                preview_seconds = int(preview_raw)
            except ValueError:
                self._set_status("errors.preview_nan")
                return

        formats     = [code for code, var in self.fmt_vars.items() if var.get()]
        timestamps  = self.timestamps_var.get()
        out_dir_raw = self.outdir_entry.get().strip()
        out_dir     = Path(out_dir_raw) if out_dir_raw else None
        open_folder = self.open_folder_var.get()

        if not formats:
            self._set_status("errors.no_formats")
            return

        self.start_btn.configure(state="disabled",
                                 text=_i18n.t("settings.running"))
        self._clear_log()
        self._set_status("status.starting")

        log_q: queue.Queue[str | None] = queue.Queue()
        result: dict = {}

        def log(msg: str) -> None:
            log_q.put(msg)

        def worker() -> None:
            try:
                paths, segments = run_pipeline(
                    audio=src,
                    num_speakers=self._n_speakers,
                    names=names,
                    language=self._tx_lang_code,
                    timestamps=timestamps,
                    formats=formats,
                    out_dir=out_dir,
                    preview_seconds=preview_seconds,
                    log=log,
                )
                result["paths"]    = paths
                result["segments"] = segments
            except Exception as exc:
                log(f"ERROR: {exc}")
            finally:
                log_q.put(None)

        threading.Thread(target=worker, daemon=True).start()
        self._poll(log_q, result, open_folder)

    def _poll(self, log_q: queue.Queue, result: dict, open_folder: bool) -> None:
        t = _i18n.t
        try:
            while True:
                msg = log_q.get_nowait()
                if msg is None:
                    paths    = result.get("paths", [])
                    segments = result.get("segments", [])
                    if paths:
                        self._set_status("status.done")
                        n_spk_found = len({s["speaker"] for s in segments})
                        duration    = max((s["end"] for s in segments), default=0)
                        mins, secs  = int(duration // 60), int(duration % 60)
                        self._append_log(f"\n{t('summary.separator')}")
                        self._append_log(
                            t("summary.stats",
                              segments=len(segments),
                              speakers=n_spk_found,
                              duration=f"{mins}m {secs}s")
                        )
                        self._append_log(
                            t("summary.files") + "\n" +
                            "\n".join(f"  {p}" for p in paths))
                        if segments:
                            self.transcript_box.configure(state="normal")
                            self.transcript_box.delete("1.0", "end")
                            for seg in segments:
                                ts   = self._fmt_ts(seg["start"])
                                line = f"[{ts}] {seg['speaker']}: {seg['text']}\n"
                                self.transcript_box.insert("end", line)
                            self.transcript_box.configure(state="disabled")
                            self._tabs.set("Transcript")
                        if open_folder:
                            subprocess.Popen(["explorer", f"/select,{paths[0]}"])
                    else:
                        self._set_status("status.failed")
                    self.start_btn.configure(
                        state="normal", text=t("settings.start_btn"))
                    return

                self._append_log(msg)

                if msg.startswith("[system] using device:"):
                    self.device = msg.split(":", 1)[1].strip()
                    continue

                key = self._phase_key(msg)
                if key:
                    self._set_status(key)

        except queue.Empty:
            pass
        self.after(100, self._poll, log_q, result, open_folder)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _phase_key(self, msg: str) -> str | None:
        for kw, key in _PHASE_KEYWORDS:
            if kw in msg:
                return key
        return None

    def _set_status(self, key: str, **kwargs) -> None:
        """Store the i18n key and immediately render the translated status text."""
        self._status_key    = key
        self._status_kwargs = kwargs
        self._render_status()

    def _render_status(self) -> None:
        """Re-translate and display the current status (called on language switch too)."""
        text   = _i18n.t(self._status_key, **self._status_kwargs)
        suffix = f"   ({self.device})" if self.device else ""
        self.status_label.configure(text=text + suffix)

    def _append_log(self, msg: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")

    def _clear_log(self) -> None:
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.transcript_box.configure(state="normal")
        self.transcript_box.delete("1.0", "end")

    @staticmethod
    def _fmt_ts(t: float) -> str:
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


if __name__ == "__main__":
    app = App()
    app.mainloop()
