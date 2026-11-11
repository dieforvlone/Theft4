#!/usr/bin/env python3
"""Exercise inspect_xex.py against synthetic XEX2/XEXP headers (no game data)."""
import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import struct
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('inspect_xex', Path(__file__).with_name('inspect_xex.py'))
inspect_xex = importlib.util.module_from_spec(spec)
sys.modules['inspect_xex'] = inspect_xex
spec.loader.exec_module(inspect_xex)


def build_xex(*, flags, media_id=0, version=0, title_id=0x545407F2, rsa=b'\x11' * 0x100,
              delta=None):
    """Build a minimal XEX2 header: optional headers, execution info, security info."""
    headers = []
    if delta is None:
        headers.append(inspect_xex.HEADER_EXECUTION_INFO)
    else:
        headers.append(inspect_xex.HEADER_DELTA_PATCH_DESCRIPTOR)
    table_end = 0x18 + 8 * len(headers)
    body_offset = table_end
    if delta is None:
        body = struct.pack('>IIII4BI', media_id, version, 0, title_id, 0, 0, 1, 1, 0)
    else:
        source_version, target_version, digest = delta
        body = struct.pack('>III', 0x4C, target_version, source_version) + digest
    security_offset = body_offset + len(body)
    security = struct.pack('>II', 0x184, 0) + rsa + b'\0' * 0x7C
    header_size = security_offset + len(security)
    data = b'XEX2' + struct.pack('>IIIII', flags, header_size, 0, security_offset, len(headers))
    for key in headers:
        data += struct.pack('>II', key, body_offset)
    return data + body + security + b'\0' * 64


class InspectXexTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, data):
        path = self.root / name
        path.write_bytes(data)
        return path

    def test_version_formatting(self):
        self.assertEqual(inspect_xex.format_version(0x00000805), '0.0.8.5')
        self.assertEqual(inspect_xex.format_version(0x00000005), '0.0.0.5')
        self.assertEqual(inspect_xex.format_version(0x21234567), '2.1.9029.103')

    def test_reads_execution_info_and_binds_matching_patch(self):
        rsa = b'\x42' * 0x100
        base = self.write('default.xex', build_xex(
            flags=inspect_xex.MODULE_TITLE, media_id=0x12345678, version=0x5, rsa=rsa))
        digest = hashlib.sha1(rsa).digest()
        patch = self.write('default.xexp', build_xex(
            flags=inspect_xex.MODULE_PATCH | inspect_xex.MODULE_PATCH_DELTA,
            delta=(0x5, 0x805, digest)))
        base_info = inspect_xex.parse_xex(base)
        patch_info = inspect_xex.parse_xex(patch)
        self.assertEqual(base_info.title_id, 0x545407F2)
        self.assertEqual(base_info.media_id, 0x12345678)
        self.assertEqual(patch_info.delta_target_version, 0x805)
        self.assertEqual(inspect_xex.patch_matches(base_info, patch_info)[0], True)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = inspect_xex.main([str(base), str(patch)])
        self.assertEqual(status, 0)
        self.assertIn('kSupportedMediaId = 0x12345678', output.getvalue())
        self.assertIn(f'kSupportedPatchSha256 = "{patch_info.sha256}"', output.getvalue())
        self.assertIn('kSupportedTargetVersion = 0x00000805', output.getvalue())

    def test_rejects_patch_for_another_executable(self):
        base = self.write('default.xex', build_xex(
            flags=inspect_xex.MODULE_TITLE, media_id=0x12345678, version=0x5))
        patch = self.write('default.xexp', build_xex(
            flags=inspect_xex.MODULE_PATCH | inspect_xex.MODULE_PATCH_DELTA,
            delta=(0x5, 0x805, b'\x99' * 20)))
        ok, reason = inspect_xex.patch_matches(inspect_xex.parse_xex(base),
                                               inspect_xex.parse_xex(patch))
        self.assertFalse(ok)
        self.assertIn('different executable', reason)

    def test_flags_gta4_executable(self):
        base = self.write('default.xex', build_xex(
            flags=inspect_xex.MODULE_TITLE, media_id=inspect_xex.GTA4_USA_MEDIA_ID, version=0x5))
        with contextlib.redirect_stdout(io.StringIO()) as output:
            status = inspect_xex.main([str(base)])
        self.assertEqual(status, 1)
        self.assertIn('not Episodes from Liberty City', output.getvalue())

    def test_rejects_non_xex(self):
        path = self.write('notes.txt', b'hello world, definitely not an xex')
        with self.assertRaises(inspect_xex.XexError):
            inspect_xex.parse_xex(path)


if __name__ == '__main__':
    unittest.main()
