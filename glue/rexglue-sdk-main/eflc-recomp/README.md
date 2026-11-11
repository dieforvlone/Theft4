# eflc-recomp: Episodes from Liberty City (separate app)

This is the start of a separate static recompilation of the standalone Xbox 360
**Grand Theft Auto: Episodes from Liberty City** disc. It shares the RexGlue
runtime with `gta4-recomp`, but has its own executable input, codegen config,
identity, data folder and (eventually) installer and iOS app.

**Status: scaffold only.** Nothing here has been run against a real EFLC
executable yet. No guest addresses are filled in.

## Why a separate app

- EFLC ships its own `default.xex`. Theft4's generated code, its codegen config
  and every title hook are tied to the exact GTA IV USA `6AC07221` + TU8 binary.
  None of those addresses carry over.
- The EFLC disc shares title ID `545407F2` with GTA IV. Saves are stored under
  `saves/<XUID>/545407F2/`, so the two games must not share a data root. This
  app uses `EFLCRecomp/` instead of `LibertyRecomp/`.
- A broken EFLC build can never affect the shipping GTA IV app.

Because the title ID is shared, the **media ID and exact executable hashes**
are the only reliable way to tell the games apart. The GTA IV installer already
rejects other media IDs, so it will refuse the EFLC disc. The EFLC installer
must do the reverse. See `src/eflc_identity.h`.

## Layout

```text
eflc-recomp/
├── CMakeLists.txt        separate app target (EFLCRecomp), opt-in
├── eflc_manifest.toml    codegen input: assets/default_eflc.xex
├── eflc_config.toml      codegen flags; addresses intentionally empty
├── assets/               your own executable (git-ignored)
├── generated/            codegen output (git-ignored)
└── src/
    ├── main.cpp
    ├── eflc_app.h        minimal first-boot app, no hooks
    └── eflc_identity.h   title/media/hash pins (to be filled in)
```

## Step 1: get the executable (on your own machine)

1. Extract your EFLC disc image with `tools/extract-xiso` (or any GDFX extractor).
2. If EFLC has a title update, obtain it from your own console. Produce the
   patched executable the same way `gta4-recomp/assets/default_v8.xex` was made
   (base XEX with its XEXP applied), and save it as
   `eflc-recomp/assets/default_eflc.xex`.
3. Identify the files with `tools/inspect_xex.py` (Python 3, no extra
   packages; it only reads headers):

   ```sh
   python3 tools/inspect_xex.py path/to/default.xex path/to/default.xexp
   ```

   It prints the title ID, media ID and versions, says whether each patch is
   built for that exact executable (the installer's signature-binding check),
   flags GTA IV's own executable and TU8 so they aren't mistaken for EFLC's,
   and prints the values to paste into `src/eflc_identity.h`. Pass several
   `.xexp` files at once if the shared `545407F2` update folder holds more
   than one. A patch still inside a title-update package must be extracted to
   a loose `default.xexp` first, for example with Velocity.

Never commit the executable, the patch, generated code or game data.

## Step 2: codegen configuration

Run codegen once with the starter config:

```sh
cd glue/rexglue-sdk-main/eflc-recomp
rexglue codegen eflc_manifest.toml
```

Then port each category in `gta4-recomp/gta4_config.toml` by finding the EFLC
equivalent, never by copying the address:

| Section | GTA IV count | How to find it in EFLC |
|---|---|---|
| `[rexcrt]` memset/memcpy/memmove/str* | 9 | FLIRT match + caller count + leaf-shape check, exactly as the GTA IV comments describe |
| `[functions]` cross-function branch targets / thunks | 79 total | Codegen errors and unresolved-branch warnings point at them |
| Script-native callbacks | (part of the 79) | Native registration calls taking a name string; the names are the same between games |
| CRT constructor thunks | (part of the 79) | The CRT constructor table. Use flat-image offsets (`VA - 0x82000000`) |
| CRT/heap/file boundaries | (part of the 79) | Match by code pattern; keep the original PPC bodies |

Rebuild after each change until the app links.

## Step 3: first boot

```sh
cmake -DREXGLUE_BUILD_EFLC_RECOMP=ON ...   # plus your normal desktop flags
cmake --build . --target EFLCRecomp
```

Put the extracted disc, with `default.xexp` beside `default.xex`, in
`<user folder>/EFLCRecomp/game`. The goal of this step is the EFLC main menu
with the generic Xenos renderer and no title hooks.

## Step 4: port hooks one at a time

Address count is the number of distinct guest addresses each GTA IV source file
hardcodes. Each must be found again in the EFLC binary, usually by matching the
surrounding code pattern because the engine is very close to GTA IV's.

| GTA IV file | Addresses | Purpose | Priority |
|---|---:|---|---|
| `gta4_presentation_hooks.cpp` | 6 | Frame presentation | 1 |
| `gta4_native_hooks.cpp` | 149 | Native Metal renderer integration | 1 (largest) |
| `gta4_transition_hooks.cpp` | 16 | Loading/transition handling | 1 |
| `gta4_input_hooks.cpp` | 27 | Controller input | 2 |
| `input/context_touch_controls.cpp`, `gta4_touch_coordinator.cpp` | 9 + 5 | Touch controls (iOS) | 2 |
| `gta4_aspect_hooks.cpp` | 17 | Native aspect ratio | 3 |
| `gta4_frontend_hooks.cpp` | 8 | Front-end menus | 3 |
| `gta4_font_selection_trace.cpp` | 7 | Font selection (EFLC uses the TLAD/TBoGT atlases) | 3 |
| `gta4_quicksave_hooks.cpp` | 11 | Quicksave | 3 |
| `gta4_motion_hooks.cpp`, `gta4_motion_vehicle_hooks.cpp` | 13 + 1 | Motion blur | 4 |
| `gta4_population_hooks.cpp` | 5 | Population tuning | 4 |
| `gta4_loading_parallax_fix.cpp` | 4 | Loading-screen fix | 4 |
| `gta4_gameplay_mods.cpp` | 3 | Mods tab | 5 |
| `gta4_multiplayer_64_hooks.cpp`, network | 4 + 2 | Online | 5 |
| `gta4_audio_lifetime_trace.cpp`, `legal_screen_trace.cpp`, `gta4_streaming_diagnostics.cpp`, `gta4_fault_probe_hooks.cpp` | 47 + 5 + 3 + 3 | Diagnostics only | As needed |

Copy a hook file into `eflc-recomp/src/` only when its addresses have been
re-derived, and keep a comment beside each address saying how it was verified.

## Step 5: installer and iOS app

- Installer: reuse `gta4-recomp/src/install` with the identity pinned in
  `eflc_identity.h`, writing into `EFLCRecomp/`.
- iOS: a second app target with its own bundle identifier, generated code and
  container. `ios/CMakeLists.txt` is currently hardwired to `gta4-recomp`, so it
  needs a title parameter. Texture preparation must scan EFLC's archives and
  use EFLC's archive key.
