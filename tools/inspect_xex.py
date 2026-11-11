#!/usr/bin/env python3
"""Report the identity of an Xbox 360 default.xex and any default.xexp patches.

Run this on your own computer against files dumped from your own console:

    python3 tools/inspect_xex.py path/to/default.xex [path/to/default.xexp ...]

It reads headers only and never modifies or uploads anything. For each XEX it
prints the title ID, media ID, version and SHA-256. For each XEXP it prints the
versions it patches from and to, its SHA-256, and whether it is built for the
given default.xex (the same signature-binding check the Theft4 installer uses).
It also flags the GTA IV USA retail executable and GTA IV TU8, which Theft4
already pins, so they are not mistaken for Episodes from Liberty City files.

Patches inside a title-update package must be extracted to a loose
default.xexp first (for example with Velocity).
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import struct
import sys

XEX2_MAGIC = b"XEX2"
HEADER_EXECUTION_INFO = 0x00040006
HEADER_DELTA_PATCH_DESCRIPTOR = 0x000005FF

MODULE_TITLE = 0x00000001
MODULE_PATCH = 0x00000010
MODULE_PATCH_FULL = 0x00000020
MODULE_PATCH_DELTA = 0x00000040

SECURITY_RSA_OFFSET = 0x8
SECURITY_RSA_SIZE = 0x100
MAX_HEADER_BYTES = 64 * 1024 * 1024

# Values Theft4 pins for Grand Theft Auto IV (gta4-recomp/src/install).
GTA4_USA_MEDIA_ID = 0x6AC07221
GTA4_TU8_PATCH_SHA256 = "480aee5e2b42707791e7571bb8407c5bb3f6c7534f07f9beb426db4cfc648fd3"
GTA4_USA_RSA_SIGNATURE_SHA1 = bytes([
    0x19, 0x2B, 0x3F, 0x56, 0x7C, 0x59, 0x36, 0x0C, 0x6C, 0xE2,
    0x11, 0x82, 0x0D, 0x77, 0x6F, 0x6B, 0x25, 0x25, 0x1A, 0x89,
])


class XexError(ValueError):
    pass


@dataclass
class XexInfo:
    path: Path
    sha256: str
    module_flags: int
    title_id: int | None = None
    media_id: int | None = None
    version: int | None = None
    base_version: int | None = None
    disc_number: int | None = None
    disc_count: int | None = None
    rsa_signature_sha1: bytes | None = None
    delta_source_version: int | None = None
    delta_target_version: int | None = None
    delta_source_digest: bytes | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def is_patch(self) -> bool:
        return bool(self.module_flags & MODULE_PATCH)


def format_version(value: int | None) -> str:
    if value is None:
        return "unknown"
    major = (value >> 28) & 0xF
    minor = (value >> 24) & 0xF
    build = (value >> 8) & 0xFFFF
    qfe = value & 0xFF
    return f"{major}.{minor}.{build}.{qfe}"


def _u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise XexError("header field is out of bounds")
    return struct.unpack_from(">I", data, offset)[0]


def parse_xex(path: Path) -> XexInfo:
    raw = path.read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()
    if len(raw) < 0x18 or raw[:4] != XEX2_MAGIC:
        raise XexError(f"{path} is not an XEX2 file")

    module_flags = _u32(raw, 0x4)
    header_size = _u32(raw, 0x8)
    security_offset = _u32(raw, 0x10)
    header_count = _u32(raw, 0x14)
    if header_size > len(raw) or header_size > MAX_HEADER_BYTES:
        raise XexError(f"{path}: header size is out of bounds")
    if header_count > (header_size - 0x18) // 8:
        raise XexError(f"{path}: optional header count is out of bounds")
    header = raw[:header_size]

    info = XexInfo(path=path, sha256=sha256, module_flags=module_flags)

    rsa_end = security_offset + SECURITY_RSA_OFFSET + SECURITY_RSA_SIZE
    if security_offset >= 0x18 and rsa_end <= header_size:
        rsa = header[security_offset + SECURITY_RSA_OFFSET:rsa_end]
        info.rsa_signature_sha1 = hashlib.sha1(rsa).digest()
    else:
        info.notes.append("security info is missing or out of bounds")

    for index in range(header_count):
        key = _u32(header, 0x18 + index * 8)
        offset = _u32(header, 0x18 + index * 8 + 4)
        if key == HEADER_EXECUTION_INFO:
            if offset + 0x18 > header_size:
                raise XexError(f"{path}: execution info is out of bounds")
            info.media_id = _u32(header, offset)
            info.version = _u32(header, offset + 0x4)
            info.base_version = _u32(header, offset + 0x8)
            info.title_id = _u32(header, offset + 0xC)
            info.disc_number = header[offset + 0x12]
            info.disc_count = header[offset + 0x13]
        elif key == HEADER_DELTA_PATCH_DESCRIPTOR:
            if offset + 0x20 > header_size:
                raise XexError(f"{path}: delta patch descriptor is out of bounds")
            info.delta_target_version = _u32(header, offset + 0x4)
            info.delta_source_version = _u32(header, offset + 0x8)
            info.delta_source_digest = header[offset + 0xC:offset + 0x20]
    return info


def patch_matches(base: XexInfo, patch: XexInfo) -> tuple[bool, str]:
    """Mirror gta4_installer.cpp ValidatePatch's base-binding checks."""
    if not patch.is_patch or not (patch.module_flags & MODULE_PATCH_DELTA):
        return False, "not a delta XEXP patch"
    if patch.delta_source_digest is None:
        return False, "no delta patch descriptor"
    if base.rsa_signature_sha1 is None:
        return False, "the base XEX has no readable signature"
    if patch.delta_source_version != base.version:
        return False, (f"patches version {format_version(patch.delta_source_version)}, "
                       f"but the XEX is {format_version(base.version)}")
    if patch.delta_source_digest != base.rsa_signature_sha1:
        return False, "built for a different executable (signature binding mismatch)"
    return True, "built for this executable"


def recognize(info: XexInfo) -> str | None:
    if info.is_patch:
        if info.sha256 == GTA4_TU8_PATCH_SHA256:
            return "GTA IV TU8 (already used by Theft4; it cannot patch EFLC)"
        return None
    if info.rsa_signature_sha1 == GTA4_USA_RSA_SIGNATURE_SHA1:
        return "GTA IV USA retail executable (already used by Theft4)"
    if info.media_id == GTA4_USA_MEDIA_ID:
        return "GTA IV USA retail media ID"
    return None


def describe(info: XexInfo) -> list[str]:
    kind = "XEXP patch" if info.is_patch else "XEX executable"
    lines = [f"{info.path}", f"  type:            {kind}"]
    if info.title_id is not None:
        lines.append(f"  title ID:        {info.title_id:08X}")
    if info.media_id is not None:
        lines.append(f"  media ID:        {info.media_id:08X}")
    if info.version is not None:
        lines.append(f"  version:         {format_version(info.version)} (0x{info.version:08X})")
    if info.base_version is not None:
        lines.append(f"  base version:    {format_version(info.base_version)}")
    if info.disc_count:
        lines.append(f"  disc:            {info.disc_number} of {info.disc_count}")
    if info.is_patch:
        lines.append(f"  patches from:    {format_version(info.delta_source_version)}")
        target = info.delta_target_version
        hex_target = f" (0x{target:08X})" if target is not None else ""
        lines.append(f"  patches to:      {format_version(target)}{hex_target}")
    elif info.module_flags & MODULE_TITLE == 0:
        info.notes.append("not marked as a title executable")
    lines.append(f"  SHA-256:         {info.sha256}")
    known = recognize(info)
    if known:
        lines.append(f"  recognized as:   {known}")
    lines.extend(f"  note:            {note}" for note in info.notes)
    return lines


def identity_snippet(base: XexInfo, patch: XexInfo | None) -> list[str]:
    target = patch.delta_target_version if patch else base.version
    return [
        "Values for glue/rexglue-sdk-main/eflc-recomp/src/eflc_identity.h:",
        f"  inline constexpr uint32_t kSupportedMediaId = 0x{base.media_id or 0:08X};",
        f'  inline constexpr std::string_view kSupportedBaseXexSha256 = "{base.sha256}";',
        f'  inline constexpr std::string_view kSupportedPatchSha256 = "{patch.sha256 if patch else ""}";',
        f"  inline constexpr uint32_t kSupportedTargetVersion = 0x{target or 0:08X};",
    ]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("xex", type=Path, help="default.xex from your own disc or console")
    parser.add_argument("patches", type=Path, nargs="*", help="optional default.xexp files")
    args = parser.parse_args(argv)

    try:
        base = parse_xex(args.xex)
        patches = [parse_xex(path) for path in args.patches]
    except (OSError, XexError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if base.is_patch:
        print(f"error: {args.xex} is a patch; pass default.xex first", file=sys.stderr)
        return 2

    print("\n".join(describe(base)))
    matching: list[XexInfo] = []
    for patch in patches:
        print()
        print("\n".join(describe(patch)))
        ok, reason = patch_matches(base, patch)
        print(f"  for this XEX:    {'YES' if ok else 'NO'} - {reason}")
        if ok:
            matching.append(patch)

    print()
    if recognize(base):
        print("This is the GTA IV executable, not Episodes from Liberty City. "
              "Use default.xex from the EFLC disc.")
        return 1
    if patches and not matching:
        print("None of the patches are built for this executable. Without a matching "
              "patch, the base executable is what eflc-recomp would be built from.")
    elif len(matching) > 1:
        print("More than one patch matches; use the one with the highest target version.")
    best = max(matching, key=lambda p: p.delta_target_version or 0) if matching else None
    print("\n".join(identity_snippet(base, best)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
