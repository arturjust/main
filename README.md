# Video editing skills for Claude Code

Five skills from the "Claude edits video" reel:

| # | Skill | What it does | Source |
|---|---|---|---|
| 01 | `ghost-editor` | Talking-head reel editor: picks the best takes, cuts bad takes and pauses, adds captions, motion and SFX | [kurbaitaev/ghost-editor](https://github.com/kurbaitaev/ghost-editor) (MIT) |
| 02 | `ffmpeg-edit` | Cuts pauses, puts ducked music under the voice, switches cameras by speaker | written for this repo |
| 03 | `hyperframes`, `hyperframes-cli`, `hyperframes-registry`, `media-use`, `figma`, `reverse-any-video`, `remotion-to-hyperframes`, `slideshow`, `style-sampling` | HeyGen HyperFrames: about 450 ready-made animations, titles and transitions (HTML rendered to video) | [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) (Apache-2.0) |
| 04 | `shorts` | Long stream or podcast to shorts: finds hook moments, adds captions, exports | [AgriciDaniel/claude-shorts](https://github.com/AgriciDaniel/claude-shorts) (MIT) |
| 05 | `resolve-*` | Skills for the DaVinci Resolve MCP: edits right inside your Resolve project | [samuelgursky/davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp) (MIT) |

## Install

```bash
git clone <this repo> && cd <repo>
bash install-skills.sh        # copies into ~/.claude/skills
```

Or just open Claude Code inside this repo: the skills in `.claude/skills/` work for this project without installing.

### Dependencies

- **All skills:** `ffmpeg`, `python3`, `node` 22 or newer.
- **ghost-editor and HyperFrames:** `npx hyperframes` downloads the CLI the first time it runs. See `.claude/skills/ghost-editor/README.md` for details.
- **shorts:** `git clone https://github.com/AgriciDaniel/claude-shorts && cd claude-shorts && bash setup.sh` installs faster-whisper and Remotion. An NVIDIA GPU is recommended.
- **DaVinci Resolve MCP:** the skills only work once the MCP server is connected:
  ```bash
  git clone https://github.com/samuelgursky/davinci-resolve-mcp && cd davinci-resolve-mcp && python install.py
  ```
  The installer writes the config for Claude Code. It works with the **free** DaVinci Resolve through the in-app bridge (Workspace ▸ Scripts). See the "Free edition" section of that repo's README.
