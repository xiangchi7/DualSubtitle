# DualSubtitle — Chinese/English dual-language text for DARK SOULS III 1.15.0

Shows game text twice: your display language plus the other language.

- Display language **Simplified Chinese** → English appears below / next to it
- Display language **English** → Chinese appears below / next to it
- Covers base game + DLC1 + DLC2 (text comes from the cumulative packs `menu_dlc1/2`, `item_dlc1/2`)
- Does not touch the exe, params, or saves; coexists with your existing mods
- Every text category can be toggled individually (see configuration below)

## Quick start

1. Close the game
2. Run `install.ps1` (right-click → Run with PowerShell, or `powershell -ExecutionPolicy Bypass -File install.ps1`)
3. Start the game **offline**. Playing online with modified files carries a soft-ban risk

To uninstall: run `restore.ps1` (restores every replaced file byte-for-byte).

## File layout

```
DualSubtitle\
  msg\zhocn\*.msgbnd.dcx    ← generated Chinese slot (Chinese + English)
  msg\engus\*.msgbnd.dcx    ← generated English slot (English + Chinese)
  source\                   ← pristine copies of the original text packs (keep this)
  tools\dualsub.py          ← generator
  tools\dualsub.config.json ← category settings
  build.ps1                 ← regenerate
  install.ps1 / restore.ps1 ← install / uninstall
```

## Configuration

Edit `tools\dualsub.config.json`. Real FMG file names are internal and never need editing:

```json
{
  "categories": {
    "Dialogue": true,
    "Cutscene Subtitles": true,
    "Dialogue Boxes": true,
    "Event Text": true,
    "Menu Text": true,
    "Key Prompts": true,
    "Help Text": true,
    "System Messages": true,
    "Place Names": true,
    "Item Names": true,
    "Item Descriptions": "off",
    "Item Lore": "off",
    "Blood Messages": true,
    "Other": true
  }
}
```

Values:

| Value | Effect |
|---|---|
| `true` | bilingual (separator chosen automatically) |
| `false` / `"off"` | keep the original text, no merge |
| `"en_only"` | replace with the English text (good for long descriptions) |
| `"append"` | force appending the other language (may be clipped) |

After editing, run:

```powershell
powershell -ExecutionPolicy Bypass -File build.ps1
powershell -ExecutionPolicy Bypass -File install.ps1
```

Global options: `default_enabled` (fallback for unlisted categories) and `separator` (default `\n`).

## How separators are chosen

- Multi-line widgets (dialogue, cutscene subtitles, event text, descriptions): newline
- Single-line widgets (names, place names, menus, prompts): `Chinese / English` on one line
- Long strings (>18 chars or already containing newlines): newline

## Known limitations

- The description panel has a fixed height: full Chinese + full English never fits.
  `Item Descriptions` and `Item Lore` default to `off`; set them to `"en_only"` to read the English text instead.
- Game updates or Steam "verify integrity" will overwrite these files; rerun `build.ps1` + `install.ps1`.
- This tool only edits text. If another mod also replaces msg files, regenerate from that mod's files as the source.
