#!/usr/bin/env python3
"""Lay a music bed under a voice track with sidechain ducking and loudness normalisation."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import duration, run_filter  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("video")
    ap.add_argument("music")
    ap.add_argument("output")
    ap.add_argument("--music-db", type=float, default=-14.0)
    ap.add_argument("--duck", type=float, default=8.0, help="approx dB of ducking under speech")
    ap.add_argument("--fade", type=float, default=2.0)
    ap.add_argument("--lufs", type=float, default=-14.0)
    a = ap.parse_args()

    total = duration(a.video)
    ratio = max(2.0, min(20.0, a.duck))  # stronger duck -> higher ratio
    fade_out = max(0.0, total - a.fade)
    graph = (
        f"[0:a]asplit=2[voice][key];"
        f"[1:a]volume={a.music_db}dB,atrim=0:{total:.3f},asetpts=PTS-STARTPTS,"
        f"afade=t=in:d={a.fade},afade=t=out:st={fade_out:.3f}:d={a.fade}[bed];"
        f"[bed][key]sidechaincompress=threshold=0.02:ratio={ratio}:attack=20:release=400[ducked];"
        f"[voice][ducked]amix=inputs=2:duration=first:normalize=0,"
        f"loudnorm=I={a.lufs}:TP=-1.5:LRA=11[out]"
    )
    run_filter([a.video, ["-stream_loop", "-1", "-i", a.music]], graph,
               ["0:v?", "[out]"], a.output,
               ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-t", f"{total:.3f}", "-movflags", "+faststart"])
    print(f"wrote {a.output}  (music {a.music_db} dB, duck ~{a.duck} dB, {a.lufs} LUFS)")


if __name__ == "__main__":
    main()
