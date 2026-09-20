# waen (แว่น)

waen is a Windows overlay that watches a selected game-text region, reads
English text with OCR, translates it to Thai, and draws the translation without
covering the original text.

## Requirements and installation

- Windows 10 version 2004 or later, or Windows 11.
- Python 3.11 or later for development. The packaged release does not need
  Python installed.
- An English Windows OCR language pack (`en-US` or `en-GB`) is recommended.

For a development install from this checkout:

```bat
.venv\Scripts\python -m pip install -e ".[dev]"
```

To create the Windows package, install the build extra and then build the spec:

```bat
.venv\Scripts\python -m pip install -e ".[build]"
.venv\Scripts\python -m PyInstaller build\waen.spec --clean
```

Copy the entire `dist\waen\` directory to the target computer and run
`waen.exe`; do not copy just the executable.

## Use

Start `waen.exe`, choose the game-text region from the settings window, then
start translation. Translation uses Google Translate and therefore needs an
internet connection. A saved region can be captured for diagnostics with:

```bat
waen --save-region capture.png
```

For terminal-only capture and OCR, use:

```bat
waen --cli --region 0,0,1280,720
```

The defaults can be changed in `%APPDATA%\waen\config.json`.

## Hotkeys

| Action | Default |
| --- | --- |
| Start / stop translation | Ctrl+Alt+T |
| Select capture region | Ctrl+Alt+R |
| Hide overlay | Ctrl+Alt+H |

## Game setup

Set the game to **Borderless Windowed** mode where possible. Desktop capture
is most reliable for borderless windows, and this lets the overlay remain above
the game; exclusive fullscreen can prevent one or both from being captured or
displayed correctly.

## Troubleshooting

- **No text or a black capture:** confirm the selected physical-pixel region,
  use Borderless Windowed mode, and try the `mss` capture backend in the config.
- **Windows OCR is unavailable:** install an `en-US` or `en-GB` OCR language
  pack, or select RapidOCR in the config.
- **RapidOCR cannot find its models:** use the complete `dist\waen\` folder;
  the package bundles the model data beside the executable.
- **Overlay does not appear:** check that another overlay/anti-cheat tool is not
  blocking it, then restart waen after the game has opened.
- **Translation fails:** confirm internet access; waen uses the free Google
  Translate backend and needs no API key.

## Design and phase reports

- [Design specification](docs/superpowers/specs/2026-09-10-waen-design.md)
- [Implementation plan](docs/superpowers/plans/2026-09-10-waen.md)
- [Phase 0 OCR report](docs/phase0-ocr-report.md)
- [Phase 0 regional OCR report](docs/phase0-ocr-report-region.md)
- [Phase 2 placeholder notes](docs/phase2-placeholder-notes.md)
- [Phase 5 build notes](docs/phase5-build-notes.md)
- [Phase 6 corpus notes](docs/phase6-corpus-notes.md)
