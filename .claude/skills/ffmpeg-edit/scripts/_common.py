"""Shared helpers for the ffmpeg-edit skill (stdlib only)."""
import json
import os
import re
import subprocess
import sys
import tempfile


def run(cmd, capture=False):
    print("+", " ".join(cmd[:6]), "..." if len(cmd) > 6 else "", file=sys.stderr)
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stderr[-4000:])
        sys.exit(f"command failed: {cmd[0]}")
    return res


def probe(path):
    out = run(["ffprobe", "-v", "error", "-show_format", "-show_streams",
               "-of", "json", path]).stdout
    return json.loads(out)


def duration(path):
    return float(probe(path)["format"]["duration"])


def has_audio(path):
    return any(s["codec_type"] == "audio" for s in probe(path)["streams"])


def video_size(path):
    for s in probe(path)["streams"]:
        if s["codec_type"] == "video":
            return int(s["width"]), int(s["height"])
    sys.exit(f"no video stream in {path}")


def silences(path, noise="-35dB", min_silence=0.7, stream="0:a:0"):
    """Return list of (start, end) silent intervals."""
    res = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-map", stream,
         "-af", f"silencedetect=n={noise}:d={min_silence}", "-f", "null", "-"],
        capture_output=True, text=True)
    out, start = [], None
    for line in res.stderr.splitlines():
        m = re.search(r"silence_start: (-?[\d.]+)", line)
        if m:
            start = max(0.0, float(m.group(1)))
        m = re.search(r"silence_end: ([\d.]+)", line)
        if m and start is not None:
            out.append((start, float(m.group(1))))
            start = None
    if start is not None:
        out.append((start, duration(path)))
    return out


def rms_series(path, step=0.1, stream="0:a:0"):
    """Per-window RMS level in dB (list of floats, one per `step` seconds)."""
    sr = 16000
    n = int(sr * step)
    res = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-map", stream,
         "-af", f"aresample={sr},asetnsamples=n={n}:p=0,"
                "astats=metadata=1:reset=1,"
                "ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-",
         "-f", "null", "-"],
        capture_output=True, text=True)
    vals = []
    for line in res.stdout.splitlines():
        if "RMS_level=" in line:
            v = line.split("=", 1)[1].strip()
            vals.append(-120.0 if v in ("-inf", "inf", "nan") else float(v))
    return vals


def run_filter(inputs, graph, maps, out, extra=()):
    """Run ffmpeg with a (possibly huge) filter graph written to a temp file."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(graph)
        gfile = f.name
    cmd = ["ffmpeg", "-hide_banner", "-y"]
    for i in inputs:
        cmd += i if isinstance(i, list) else ["-i", i]
    cmd += ["-filter_complex_script", gfile]
    for m in maps:
        cmd += ["-map", m]
    cmd += list(extra) + [out]
    try:
        run(cmd)
    finally:
        os.unlink(gfile)


def fmt(t):
    m, s = divmod(t, 60)
    return f"{int(m):02d}:{s:04.1f}"
