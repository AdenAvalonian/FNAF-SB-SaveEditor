# Changelog

All notable changes to this project are documented here.

## [1.0.0] - 2026-06-27

First public release.

### Features
- GUI editor for FNAF: Security Breach `.sav` files (GVAS / UE4.27).
- **Missions** tab — edit mission Status, InfoState, and completed step indices;
  one-click "Enable first step".
- **World Flags** tab — view, filter, add, and remove `ActivatedObjects` world
  triggers.
- **Raw Tree** tab — browse and edit any scalar property; array/map entries are
  labelled by their contents for readability.
- Dark theme.
- Automatic `.bak` backup on save (toggleable).
- Round-trip integrity check on open.

### Library (`gvas.py`)
- Dependency-free GVAS parser/serializer (Python standard library only).
- Byte-exact round-trip on every tested save.
- Handles Bool, Int, Int64, UInt32, Float, Str, Name, Enum, Byte, Struct
  (named-field + binary), Array (scalar + struct), Set, and Map (incl. enum keys
  and inline-struct values); unknown types preserved as raw bytes.
- Automatic recomputation of all nested container size fields on write.
