# FNAF: Security Breach — Save Editor

A lightweight GUI for viewing and editing **Five Nights at Freddy's: Security
Breach** save files (`SaveGameSlotN.sav`). It reads the game's Unreal Engine
**GVAS** save format (UE4.27), lets you change missions, world flags, and raw
property values, and writes the file back with all internal size fields
recomputed so the save stays valid.

![tabs: Missions · World Flags · Raw Tree](#)

---

## Quick start

1. Install **Python 3** (3.8 or newer). On Windows, grab it from
   [python.org](https://www.python.org/downloads/) and tick *"Add Python to
   PATH"* during setup. Tkinter (the GUI toolkit) ships with the standard
   Windows and macOS installers.
2. Keep `save_editor.py` and `gvas.py` **in the same folder**.
3. Run it:

   ```
   python save_editor.py
   ```

4. **File ▸ Open** and choose a `.sav` file.

Your saves normally live in:

```
%LOCALAPPDATA%\FnafSecurityBreach\Saved\SaveGames\
```

---

## Tabs

**Missions** — edit any story mission. Pick one from the list to set its
**Status** (Inactive / Active / Complete / Failed), its **InfoState** number,
and its list of **completed step indices** (comma-separated, e.g. `0, 1, 2`).
The **"Enable first step"** button sets a mission Active with step 0 complete in
one click.

**World Flags** — the game's `ActivatedObjects` set: every world trigger marked
done (doors opened, generators powered, cutscenes seen, …). Filter by name,
**remove** a flag to let the game re-trigger that event, or **add** one.

**Raw Tree** — the complete property tree. Double-click any scalar value
(int, float, bool, string, name, enum) to edit it. Array and map entries are
labelled by their contents (e.g. `[18] StopRoxy`) so they're easy to find. Use
this for anything the other tabs don't cover — inventory, Freddy power,
player position, and so on.

---

## Safety

- **Round-trip check on open.** The editor re-serializes the file you open and
  compares it byte-for-byte to the original. If they don't match, it warns you
  *before* you edit anything.
- **Automatic backups.** On save it writes a `.bak` copy next to the file by
  default (toggle in the toolbar).
- **Self-correcting sizes.** Unreal stores byte-length fields for every nested
  container. The editor recomputes all of them on save, so edits that change a
  value's length (adding a mission, removing a flag, renaming a string) stay
  valid.

**Always keep a backup of a save you care about.** Editing save files is
inherently risky, and this tool comes with no warranty (see LICENSE).

---

## Supported property types

The GVAS library (`gvas.py`) handles the full set used by Security Breach saves:
Bool, Int, Int64, UInt32, Float, Str, Name, Enum, Byte, Struct (named-field and
binary like Vector/Rotator), Array (scalar and struct), Set, and Map (including
enum keys and inline-struct values). Unknown property types are preserved as raw
bytes so they round-trip untouched.

---

## How it works (for the curious)

Security Breach saves use a slightly older GVAS variant where each property
header stores its size as a **32-bit** int (not 64-bit). The library parses the
whole property tree into editable Python objects and, on write, re-emits the
header, every property, and the trailer — recomputing each container's size
field from the actual serialized bytes. That's why a no-op load→save reproduces
the original file exactly, and why structural edits don't corrupt the save.

---

## Troubleshooting

- **`ModuleNotFoundError: No module named 'tkinter'`** — your Python was built
  without Tk. On Windows/macOS reinstall from python.org; on Linux install your
  distro's `python3-tk` package.
- **"This file did not round-trip exactly" warning on open** — the file uses a
  structure this build doesn't fully model. Editing is not recommended; please
  report the save (see below) so it can be supported.
- **Game doesn't reflect an edit** — some in-game state is driven by live events
  rather than saved values.

---

## Reporting issues

If a save won't open or round-trip, that's the most useful thing to report.
Include the game version and, if you can, the save file itself.

---

## Credits

GVAS format handling is original and dependency-free (Python standard library only).
