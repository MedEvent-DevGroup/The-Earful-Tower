"""Transcribe a multi-speaker audio file with speaker diarization.

CLI:
    python transcribe_3speakers.py <audio> [--speakers N] [--names A,B,C]
    [--lang fr|en] [--no-timestamps] [--formats txt,md,srt,mkv] [--out-dir PATH]

Also importable as a library by app.py via run().
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

import torch
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline

ROOT = Path(__file__).parent
CONNECTOR_PATH = ROOT.parent / "connectors" / "huggingface-read.md"
HF_TOKEN_RE = re.compile(r"hf_\S+")

# Generic Whisper hints — improve accuracy for dialect/domain without exposing
# personal context.  Override per-run with the --initial-prompt CLI flag or the
# initial_prompt= argument of run().
INITIAL_PROMPTS: dict[str, str] = {
    "fr": "Conversation en français québécois entre plusieurs interlocuteurs.",
    "en": "",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_hf_token() -> str:
    text = CONNECTOR_PATH.read_text(encoding="utf-8")
    m = HF_TOKEN_RE.search(text)
    if not m:
        sys.exit(f"No hf_ token found in {CONNECTOR_PATH}")
    return m.group(0)


def _hms(t: float, srt: bool = False) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    if srt:
        return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")
    return f"{h:02d}:{m:02d}:{int(s):02d}"


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

def to_wav(src: Path, dst: Path, log: Callable = print) -> None:
    if dst.exists():
        log(f"[ffmpeg] reusing cached {dst.name}")
        return
    log(f"[ffmpeg] converting to 16 kHz mono WAV...")
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(src), "-ac", "1", "-ar", "16000", "-vn", str(dst)],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr.decode()}")
    log("[ffmpeg] conversion done")


def diarize(
    wav: Path,
    token: str,
    num_speakers: int,
    log: Callable = print,
) -> list[tuple[float, float, str]]:
    log("[pyannote] loading pipeline...")
    os.environ["HF_TOKEN"] = token
    os.environ["HUGGING_FACE_HUB_TOKEN"] = token
    pipe = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
    pipe.to(torch.device("cuda" if torch.cuda.is_available() else "cpu"))
    log(f"[pyannote] running diarization (speakers={num_speakers})...")
    ann = pipe(str(wav), num_speakers=num_speakers)
    turns: list[tuple[float, float, str]] = []
    for segment, _, label in ann.itertracks(yield_label=True):
        turns.append((segment.start, segment.end, label))
    turns.sort()
    log(f"[pyannote] {len(turns)} turns across {len({t[2] for t in turns})} speakers")
    del pipe
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return turns


def transcribe(
    wav: Path,
    language: str = "fr",
    initial_prompt: str | None = None,
    log: Callable = print,
) -> list[dict]:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    log(f"[system] using device: {device.upper()}")
    log(f"[whisper] loading large-v3 ({compute_type})...")
    model = WhisperModel("large-v3", device=device, compute_type=compute_type)
    # Caller-supplied prompt wins; fall back to language default; None disables.
    prompt = initial_prompt if initial_prompt is not None else (INITIAL_PROMPTS.get(language, "") or None)
    log(f"[whisper] transcribing (language={language})...")
    segments_iter, info = model.transcribe(
        str(wav),
        language=language,
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        condition_on_previous_text=False,
        initial_prompt=prompt,
    )
    out: list[dict] = []
    last_ping = -1
    for s in segments_iter:
        out.append({"start": s.start, "end": s.end, "text": s.text.strip()})
        minute = int(s.end // 60)
        if minute > last_ping:
            last_ping = minute
            log(f"[whisper] {s.end / 60:.1f} min — {s.text.strip()[:72]}")
    log(f"[whisper] done — {len(out)} segments, {info.duration:.0f}s total")
    return out


def assign_speaker(seg: dict, turns: list[tuple[float, float, str]]) -> str:
    best_label, best_overlap = "UNK", 0.0
    s, e = seg["start"], seg["end"]
    for ts, te, label in turns:
        if te <= s:
            continue
        if ts >= e:
            break
        overlap = min(e, te) - max(s, ts)
        if overlap > best_overlap:
            best_overlap, best_label = overlap, label
    # fallback: no overlap found — assign nearest turn by segment centre
    if best_label == "UNK" and turns:
        centre = (s + e) / 2
        best_label = min(turns, key=lambda t: abs((t[0] + t[1]) / 2 - centre))[2]
    return best_label


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def _grouped_lines(segments: list[dict]) -> list[tuple[float, str, str]]:
    """Collapse consecutive same-speaker segments into one line."""
    lines: list[tuple[float, str, str]] = []
    cur_name: str | None = None
    cur_start = 0.0
    buf: list[str] = []
    for seg in segments:
        if seg["speaker"] != cur_name:
            if buf and cur_name is not None:
                lines.append((cur_start, cur_name, " ".join(buf).strip()))
            buf = []
            cur_name = seg["speaker"]
            cur_start = seg["start"]
        buf.append(seg["text"])
    if buf and cur_name is not None:
        lines.append((cur_start, cur_name, " ".join(buf).strip()))
    return lines


def write_outputs(
    segments: list[dict],
    out_base: Path,
    names: list[str] | None = None,
    timestamps: bool = True,
    formats: list[str] | None = None,
    audio_path: Path | None = None,
    log: Callable = print,
) -> list[Path]:
    if formats is None:
        formats = ["txt"]

    # Rank speakers by airtime, most talkative first → map to names or A/B/C
    airtime: dict[str, float] = {}
    for seg in segments:
        airtime[seg["speaker"]] = airtime.get(seg["speaker"], 0.0) + (seg["end"] - seg["start"])
    ranked = sorted(airtime.items(), key=lambda kv: kv[1], reverse=True)
    # Build label list: use provided names, pad with letters if there are more
    # speakers than names (e.g. pyannote found a 4th speaker the user didn't name)
    fallback = list("ABCDEFGHIJ")
    base_labels = names if names else []
    labels = base_labels + [l for l in fallback if l not in base_labels]
    mapping = {raw: labels[i] for i, (raw, _) in enumerate(ranked)}

    log("[airtime] most to least talkative:")
    total = sum(airtime.values()) or 1.0
    for raw, secs in ranked:
        log(f"  {mapping[raw]:<14} {secs / 60:5.1f} min  ({100 * secs / total:.0f}%)")

    for seg in segments:
        seg["speaker"] = mapping[seg["speaker"]]

    out_paths: list[Path] = []
    lines = _grouped_lines(segments)

    # .txt
    if "txt" in formats:
        path = out_base.with_suffix(".txt")
        with path.open("w", encoding="utf-8") as f:
            for start, name, text in lines:
                prefix = f"[{_hms(start)}] " if timestamps else ""
                f.write(f"{prefix}{name}: {text}\n")
        log(f"[out] {path.name}")
        out_paths.append(path)

    # .md
    if "md" in formats:
        path = out_base.with_suffix(".md")
        with path.open("w", encoding="utf-8") as f:
            f.write(f"# Transcript: {out_base.name}\n\n")
            for start, name, text in lines:
                ts_str = f" *{_hms(start)}*" if timestamps else ""
                f.write(f"**{name}**{ts_str}  \n{text}\n\n")
        log(f"[out] {path.name}")
        out_paths.append(path)

    # .srt (also needed by mkv)
    srt_path = out_base.with_suffix(".srt")
    if "srt" in formats or "mkv" in formats:
        with srt_path.open("w", encoding="utf-8") as f:
            for i, seg in enumerate(segments, 1):
                f.write(
                    f"{i}\n"
                    f"{_hms(seg['start'], srt=True)} --> {_hms(seg['end'], srt=True)}\n"
                    f"[{seg['speaker']}] {seg['text']}\n\n"
                )
        if "srt" in formats:
            log(f"[out] {srt_path.name}")
            out_paths.append(srt_path)

    # .json
    if "json" in formats:
        path = out_base.with_suffix(".json")
        with path.open("w", encoding="utf-8") as f:
            json.dump(
                [{"start": seg["start"], "end": seg["end"],
                  "speaker": seg["speaker"], "text": seg["text"]}
                 for seg in segments],
                f, indent=2, ensure_ascii=False,
            )
        log(f"[out] {path.name}")
        out_paths.append(path)

    # .mkv (waveform video + soft subs)
    if "mkv" in formats and audio_path:
        mkv_path = out_base.with_suffix(".mkv")
        log("[ffmpeg] encoding waveform video (this takes a few minutes)...")
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(audio_path),
                "-i", str(srt_path),
                "-filter_complex",
                "[0:a]showwaves=s=1280x240:mode=cline:colors=0x66ccff|0x66ccff:rate=25,format=yuv420p[v]",
                "-map", "[v]", "-map", "0:a", "-map", "1:s",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
                "-c:a", "copy", "-c:s", "srt",
                "-metadata:s:s:0", "language=fra",
                str(mkv_path),
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg mkv failed:\n{result.stderr.decode()}")
        log(f"[out] {mkv_path.name}")
        out_paths.append(mkv_path)

    return out_paths


# ---------------------------------------------------------------------------
# Main entry point (used by both CLI and app.py)
# ---------------------------------------------------------------------------

def run(
    audio: Path,
    num_speakers: int = 3,
    names: list[str] | None = None,
    language: str = "fr",
    timestamps: bool = True,
    formats: list[str] | None = None,
    out_dir: Path | None = None,
    preview_seconds: int | None = None,
    initial_prompt: str | None = None,
    log: Callable = print,
) -> tuple[list[Path], list[dict]]:
    src = Path(audio).resolve()
    if not src.exists():
        raise FileNotFoundError(f"Audio file not found: {src}")

    out_dir_path = Path(out_dir).resolve() if out_dir else src.parent
    out_dir_path.mkdir(parents=True, exist_ok=True)
    out_base = out_dir_path / src.stem

    log("[stage] 1/4 ffmpeg")
    wav = src.with_suffix(".16k.wav")
    to_wav(src, wav, log=log)

    if preview_seconds:
        preview_wav = src.with_suffix(".preview.wav")
        log(f"[ffmpeg] preview mode — first {preview_seconds}s")
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav), "-t", str(preview_seconds), str(preview_wav)],
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg preview trim failed:\n{result.stderr.decode()}")
        wav = preview_wav

    log("[stage] 2/4 diarization")
    token = read_hf_token()
    turns = diarize(wav, token, num_speakers, log=log)

    log("[stage] 3/4 transcription")
    segs = transcribe(wav, language=language, initial_prompt=initial_prompt, log=log)

    for seg in segs:
        seg["speaker"] = assign_speaker(seg, turns)

    log("[stage] 4/4 export")
    paths = write_outputs(
        segs,
        out_base,
        names=names,
        timestamps=timestamps,
        formats=formats or ["txt"],
        audio_path=src,
        log=log,
    )
    return paths, segs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Transcribe multi-speaker audio with diarization")
    ap.add_argument("audio", type=Path, help="Input audio file")
    ap.add_argument("--speakers", type=int, default=3, help="Number of speakers (default: 3)")
    ap.add_argument("--names", type=str, default=None, help="Speaker names, most-talkative first: 'Alice,Bob,Charlie'")
    ap.add_argument("--lang", type=str, default="fr", choices=["fr", "en"], help="Language (default: fr)")
    ap.add_argument("--no-timestamps", action="store_true", help="Omit timestamps from txt/md output")
    ap.add_argument("--formats", type=str, default="txt", help="Output formats, comma-separated: txt,md,srt,mkv")
    ap.add_argument("--out-dir", type=Path, default=None, help="Output directory (default: same as audio)")
    ap.add_argument("--preview", type=int, default=None, metavar="SECONDS",
                    help="Process only the first N seconds (useful for testing)")
    ap.add_argument("--initial-prompt", type=str, default=None, metavar="TEXT",
                    help="Custom context hint fed to Whisper (optional; overrides built-in default)")
    args = ap.parse_args()

    names = [n.strip() for n in args.names.split(",")] if args.names else None
    formats = [f.strip() for f in args.formats.split(",")]

    paths, _ = run(
        audio=args.audio,
        num_speakers=args.speakers,
        names=names,
        language=args.lang,
        timestamps=not args.no_timestamps,
        formats=formats,
        out_dir=args.out_dir,
        preview_seconds=args.preview,
        initial_prompt=args.initial_prompt,
    )


if __name__ == "__main__":
    main()
