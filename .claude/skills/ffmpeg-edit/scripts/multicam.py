#!/usr/bin/env python3
"""Auto multicam: cut to the camera of whoever is speaking, based on per-speaker loudness."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import duration, fmt, rms_series, run_filter, video_size  # noqa: E402

STEP = 0.1
WIDE = -1


def decide(levels, margin_db, floor_db, has_wide):
    """levels: list per speaker of RMS lists. Returns a camera index per window."""
    n = min(len(l) for l in levels)
    out, cur = [], 0
    for t in range(n):
        vals = [l[t] for l in levels]
        best = max(range(len(vals)), key=lambda i: vals[i])
        others = [v for i, v in enumerate(vals) if i != best]
        if vals[best] < floor_db:
            pick = cur  # nobody talks: hold
        elif not others or vals[best] - max(others) >= margin_db:
            pick = best
        else:
            pick = WIDE if has_wide else cur  # crosstalk
        out.append(pick)
        cur = pick
    return out


def to_shots(picks, min_shot):
    shots = []  # [cam, start_idx, end_idx)
    for i, c in enumerate(picks):
        if shots and shots[-1][0] == c:
            shots[-1][2] = i + 1
        else:
            shots.append([c, i, i + 1])
    min_n = int(round(min_shot / STEP))
    changed = True
    while changed and len(shots) > 1:
        changed = False
        for i, s in enumerate(shots):
            if s[2] - s[1] < min_n:
                j = i - 1 if i > 0 else i + 1  # merge into previous (or next)
                lo, hi = min(i, j), max(i, j)
                keep_cam = shots[j][0]
                shots[lo:hi + 1] = [[keep_cam, shots[lo][1], shots[hi][2]]]
                changed = True
                break
    merged = []
    for s in shots:
        if merged and merged[-1][0] == s[0]:
            merged[-1][2] = s[2]
        else:
            merged.append(s)
    return [(c, a * STEP, b * STEP) for c, a, b in merged]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output")
    ap.add_argument("--cam", action="append", required=True)
    ap.add_argument("--mic", action="append", default=[])
    ap.add_argument("--offset", action="append", type=float, default=[])
    ap.add_argument("--wide")
    ap.add_argument("--min-shot", type=float, default=2.0)
    ap.add_argument("--margin", type=float, default=3.0, help="dB a speaker must lead by")
    ap.add_argument("--floor", type=float, default=-45.0, help="dB below which = silence")
    ap.add_argument("--audio-from", type=int, help="use only this cam/mic index as output audio")
    ap.add_argument("--cfr", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    cams = a.cam
    if a.mic and len(a.mic) != len(cams):
        sys.exit("give one --mic per --cam (same order)")
    offs = (a.offset + [0.0] * len(cams))[:len(cams)]
    srcs = a.mic or cams

    levels = []
    for src, off in zip(srcs, offs):
        lv = rms_series(src, STEP)
        levels.append(lv[int(round(off / STEP)):])
    picks = decide(levels, a.margin, a.floor, bool(a.wide))
    shots = to_shots(picks, a.min_shot)
    total = min(duration(c) - o for c, o in zip(cams, offs))
    if shots:
        shots[-1] = (shots[-1][0], shots[-1][1], min(shots[-1][2], total))

    name = lambda c: "WIDE" if c == WIDE else f"CAM {chr(65 + c)}"
    print(f"{len(shots)} shots, {len(shots) - 1} switches")
    for c, s, e in shots:
        print(f"  {fmt(s)} → {name(c)}")
    if a.dry_run:
        return

    W, H = video_size(cams[0])
    inputs = [["-ss", f"{o:.3f}", "-i", c] for c, o in zip(cams, offs)]
    wide_idx = None
    if a.wide:
        wide_idx = len(inputs)
        inputs.append(["-i", a.wide])
    mic_base = len(inputs)
    for m, o in zip(a.mic, offs):
        inputs.append(["-ss", f"{o:.3f}", "-i", m])

    norm = (f"fps={a.cfr},scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1")
    g, labels = [], []
    for i, (c, s, e) in enumerate(shots):
        src = wide_idx if c == WIDE else c
        g.append(f"[{src}:v]trim={s:.3f}:{e:.3f},setpts=PTS-STARTPTS,{norm}[s{i}];")
        labels.append(f"[s{i}]")
    g.append("".join(labels) + f"concat=n={len(shots)}:v=1:a=0[v];")
    a_srcs = [f"[{mic_base + i}:a]" for i in range(len(a.mic))] if a.mic \
        else [f"[{i}:a]" for i in range(len(cams))]
    if a.audio_from is not None:
        a_srcs = [a_srcs[a.audio_from]]
    if len(a_srcs) == 1:
        g.append(f"{a_srcs[0]}atrim=0:{total:.3f}[a]")
    else:
        g.append("".join(a_srcs) + f"amix=inputs={len(a_srcs)}:duration=shortest:normalize=0,"
                 f"atrim=0:{total:.3f}[a]")
    run_filter(inputs, "\n".join(g), ["[v]", "[a]"], a.output,
               ["-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"])
    print(f"wrote {a.output}")


if __name__ == "__main__":
    main()
