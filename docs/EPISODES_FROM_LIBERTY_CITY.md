# GTA: Episodes from Liberty City on iOS

Theft4 0.3.X Beta Mercy Build can run The Lost and Damned and The Ballad of
Gay Tony from the standalone Xbox 360 *Grand Theft Auto: Episodes from Liberty
City* disc. No game files are included; use your own discs.

## What you need

| Disc | Region | Title ID |
|---|---|---|
| Xbox 360 *Grand Theft Auto IV* | USA | `545407F2` |
| Xbox 360 *Grand Theft Auto: Episodes from Liberty City* (standalone) | USA | `545407F2` |

You also need the GTA IV Title Update 8 file. Theft4 asks for it during GTA IV
setup and installs it.

## Setup

1. Extract the GTA IV disc and copy its contents into
   **Files → Theft4 → game**. Follow the in-app setup to install Title Update 8.
2. Extract the Episodes from Liberty City disc and copy its contents, unchanged,
   into **Files → Theft4 → game_eflc**.
3. On the Play page, choose **GTA: EFLC** and tap **Enter Liberty City**.

The first time GTA: EFLC is chosen, Theft4 completes `game_eflc` from the
verified GTA IV folder (which it only reads):

- the disc's own `default.xex` is kept as `default_eflc.xex`;
- GTA IV's `default.xex`, `default.xexp` and `aes_key.bin` are copied in;
- `game_eflc/update` receives GTA IV's Title Update 8 files, then the files the
  disc's `Update` folder adds (the episode shaders `rage_postfx_e1`,
  `rage_postfx_e2` and `water_e2` in `shaders/dcl` and `shaders/fxl_final`).

GTA IV and GTA: EFLC keep separate saves, caches and logs
(`Application Support/Theft4` and `Application Support/Theft4-EFLC`).

## Why the episodes need their own folder

Theft4 always runs GTA IV's Title Update 8 program. The Episodes disc builds
the episode world changes into its own `common.rpf`, `xbox360.rpf` and
`audio.rpf` (for example `e2_xref.ide`, the `_e2` map definitions and the
`E2_Int_*` interiors), and its `DLC1`/`DLC2` folders hold only the
episode-specific archives. With GTA IV's archives the episodes crash while
looking up assets such as `P_e2_landing_marker`; with the disc's archives they
run.

Two path differences are handled in the runtime:

- Episode discovery opens `DLC1\DLC.rpf` and `DLC2\DLC.rpf` with no device
  prefix; `DLC1\` and `DLC2\` are linked to `game:\DLC1\` and `game:\DLC2\`.
- The episode shader declarations are requested as
  `shaders\<name>dcl\<name>dcl\<name>.dcl`; that directory is linked to
  `shaders\dcl\` for the three episode shaders.
