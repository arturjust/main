#!/usr/bin/env python3
"""Remove silent pauses from a video (jump-cut), keeping a little air around words."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import duration, fmt, run_filter, silences  # noqa: E402

V_ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]
A_ENC = ["-c:a", "aac", "-b:a", "192k"]


def keep_segments(total, gaps, pad, min_keep=0.05):
    keep, cur = [], 0.0
    for s, e in gaps:
        cut_s, cut_e = s + pad, e - pad
        if cut_e - cut_s <= 0:
            continue
        if cut_s - cur > min_keep:
            keep.append((cur, cut_s))
        cur = cut_e
    if total - cur > min_keep:
        keep.append((cur, total))
    return keep


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--min-silence", type=float, default=0.7)
    ap.add_argument("--noise", default="-35dB")
    ap.add_argument("--pad", type=float, default=0.12)
    ap.add_argument("--cfr", type=int, help="force constant frame rate")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    total = duration(a.input)
    gaps = silences(a.input, a.noise, a.min_silence)
    keep = keep_segments(total, gaps, a.pad)
    kept = sum(e - s for s, e in keep)
    print(f"pauses removed: {len(gaps)}  |  {fmt(total)} -> {fmt(kept)}  "
          f"(−{total - kept:.1f}s)")
    if a.dry_run:
        for s, e in keep:
            print(f"  keep {fmt(s)} – {fmt(e)}")
        return
    if not keep:
        sys.exit("nothing left to keep — check --noise")

    pre = f"fps={a.cfr}," if a.cfr else ""
    parts, labels = [], []
    for i, (s, e) in enumerate(keep):
        parts.append(f"[0:v]{pre}trim={s:.3f}:{e:.3f},setpts=PTS-STARTPTS[v{i}];")
        parts.append(f"[0:a]atrim={s:.3f}:{e:.3f},asetpts=PTS-STARTPTS[a{i}];")
        labels.append(f"[v{i}][a{i}]")
    graph = "\n".join(parts) + "\n" + "".join(labels) + \
        f"concat=n={len(keep)}:v=1:a=1[v][a]"
    run_filter([a.input], graph, ["[v]", "[a]"], a.output,
               V_ENC + A_ENC + ["-movflags", "+faststart"])
    print(f"wrote {a.output}")


if __name__ == "__main__":
    main()
