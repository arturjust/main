---
name: ffmpeg-edit
description: "Edit talking-head / podcast footage with plain ffmpeg: cut silent pauses (jump-cut), lay background music under the voice with automatic ducking, and switch between cameras by who is speaking (multicam podcast). Use when the user asks to \"remove pauses\", \"cut the silences\", \"tighten the recording\", \"add music under the voice\", \"duck the music\", \"switch cameras\", \"multicam edit\", \"cut to whoever is talking\", or generally wants a quick ffmpeg-only edit without an NLE. Requires ffmpeg/ffprobe and python3 (stdlib only)."
---

# ffmpeg-edit — pauses · music · cameras

Three deterministic jobs, each one script in `scripts/` (stdlib Python + ffmpeg).
Skill dir below is `$S` (`.claude/skills/ffmpeg-edit` in the project, or
`~/.claude/skills/ffmpeg-edit`). Always run `ffprobe` on the inputs first and
tell the user what you found (duration, fps, resolution, audio streams).

Never overwrite the source files. Write outputs next to them with a suffix
(`_cut`, `_music`, `_multicam`) unless the user names a path.

## 1. Cut pauses — `scripts/cut_pauses.py`

```bash
python3 $S/scripts/cut_pauses.py in.mp4 out.mp4 \
  --min-silence 0.7 --noise -35dB --pad 0.12
```

- `silencedetect` finds every gap quieter than `--noise` longer than
  `--min-silence` seconds; the gap is removed but `--pad` seconds of air is
  kept on each side, so words are not clipped.
- Defaults suit a phone/lav recording. Noisy room → raise `--noise` to
  `-30dB`; fast-paced reel → `--min-silence 0.4 --pad 0.08`.
- `--dry-run` prints the keep-list and the total time saved without rendering.
  Show the user that summary (e.g. "removed 37 pauses, −1:12") before a long
  render.
- Rendering re-encodes (libx264 CRF 18, AAC 192k) with frame-accurate cuts via
  `trim`/`atrim` + `concat`. For very long files it writes the filter graph to a
  file (`-filter_complex_script`).

## 2. Music under the voice — `scripts/music_bed.py`

```bash
python3 $S/scripts/music_bed.py voice.mp4 music.mp3 out.mp4 \
  --music-db -14 --duck 8 --fade 2
```

- Music is looped/trimmed to the video length, set to `--music-db` (default
  −14 dB, a safe "bed" level), faded in/out over `--fade` s.
- `sidechaincompress` keyed by the voice ducks the music by roughly `--duck`
  dB while someone speaks and lets it come back in pauses.
- Final mix is loudness-normalised to −14 LUFS (`loudnorm`) — the social
  platforms' target. Pass `--lufs -16` for podcasts/YouTube long-form.
- Video stream is copied, not re-encoded.

## 3. Switch cameras by speaker — `scripts/multicam.py`

```bash
python3 $S/scripts/multicam.py out.mp4 \
  --cam camA.mp4 --cam camB.mp4 [--cam camC.mp4] \
  [--wide wide.mp4] [--mic micA.wav --mic micB.wav] \
  [--offset 0 --offset 0.42] --min-shot 2.0
```

- Each `--cam` is one speaker's angle. The speaker is decided from per-speaker
  audio: separate `--mic` files if given (one per cam, same order), otherwise
  each camera's own audio track.
- Loudness is measured every 0.1 s (`astats` RMS); the loudest speaker wins if
  louder than the others by 3 dB. Shots shorter than `--min-shot` are merged
  so the edit doesn't flicker. If both talk or nobody does, it cuts to
  `--wide` (if given) or holds the current shot.
- `--offset` (seconds, per cam) lines up cameras that were not started at the
  same moment. If the user doesn't know offsets, find them by cross-correlating
  a clap/first word: run
  `ffmpeg -i camX.mp4 -af silencedetect=n=-30dB:d=0.3 -f null -` on each and
  diff the first speech onsets.
- The output audio is the mix of all mics (or cam A's audio with `--audio-from 0`).
- `--dry-run` prints the shot list (`00:12.4 → CAM B`) — show it to the user.

## Order of operations for a full podcast edit

1. `multicam.py` (needs the original, unsynced-by-cuts timing)
2. `cut_pauses.py` on the multicam result
3. `music_bed.py` last, so ducking follows the final voice

Report each step's numbers (pauses removed, time saved, number of camera
switches, final LUFS) to the user.

## Gotchas

- Variable-frame-rate phone video: add `--cfr 30` to `cut_pauses.py` /
  `multicam.py` (forces `fps=30`) or the cuts drift from the audio.
- Different camera resolutions are scaled/padded to the first camera's size.
- For vertical reels from horizontal footage, crop afterwards:
  `ffmpeg -i in.mp4 -vf "crop=ih*9/16:ih,scale=1080:1920" -c:a copy out.mp4`.
