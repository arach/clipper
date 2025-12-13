# clipper

A slick TUI for compressing videos and copying them to your clipboard. Drop, compress, share.

<table>
<tr>
<td width="50%">
<img src="tui.png" alt="clipper welcome screen" width="100%">
</td>
<td width="50%">
<img src="clipper-tui.png" alt="clipper TUI" width="100%">
</td>
</tr>
</table>

## Install

```bash
git clone https://github.com/arach/clipper.git
cd clipper
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```bash
# Launch the TUI
clipper

# Or use the CLI
clip info video.mp4
clip comp video.mp4
```

## Keybindings

| Key | Action |
|-----|--------|
| `c` | Compress |
| `s` | Share (copy path to clipboard) |
| `h` | History (recent compressions) |
| `w` | Toggle watcher |
| `e` | Edit config |
| `a` | About / help |
| `l` | Copy logs to clipboard |
| `Esc` | Unfocus / command mode |
| `q` | Quit |

**Tip:** Drag & drop video files directly into the TUI!

## Presets

Name your files with a preset suffix and clipper auto-detects:

| Suffix | Scale | Quality | Use case |
|--------|-------|---------|----------|
| `-social` | 50% | CRF 28 | Quick shares, DMs |
| `-web` | 75% | CRF 23 | Balanced |
| `-archive` | 100% | CRF 18 | High quality |
| `-tiny` | 25% | CRF 32 | Previews |

Example: `vacation-social.mp4` → auto-compresses with social preset

## Watch Mode

Press `w` to start the watcher. Drop videos into the inbox folder:

```
~/Movies/VidTools/
├── inbox/      ← drop files here
├── processing/ ← currently compressing
└── done/       ← grab your compressed files
```

Edit the watch folder location by pressing `e`.

## Config

Press `e` for the config screen, or edit directly:

```
~/.config/clipper/config.toml
```

## Requirements

- Python 3.10+
- ffmpeg (`brew install ffmpeg`)
- macOS (uses `pbcopy` for clipboard)

## License

MIT
