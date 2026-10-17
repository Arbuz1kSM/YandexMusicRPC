from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_STORED, BadZipFile, ZipFile

spec = importlib.util.spec_from_file_location(
    "build_embedded", Path(__file__).resolve().parents[1] / "tools/build_embedded.py"
)
build_embedded = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_embedded)


class EmbeddedRuntimeTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.archive = Path(directory.name) / "python312.zip"

    def write_stdlib(self):
        with ZipFile(self.archive, "w", compression=ZIP_STORED) as archive:
            for name in ("encodings/__init__.pyc", "encodings/utf_8.pyc", "codecs.pyc", "io.pyc"):
                archive.writestr(name, b"test-bytecode")

    def test_complete_archive_passes(self):
        self.write_stdlib()
        build_embedded.validate_stdlib(self.archive)

    def test_truncated_archive_stops_build(self):
        self.write_stdlib()
        content = self.archive.read_bytes()
        self.archive.write_bytes(content[: len(content) // 2])
        with self.assertRaises(BadZipFile):
            build_embedded.validate_stdlib(self.archive)

    def test_corrupt_entry_stops_build(self):
        self.write_stdlib()
        content = self.archive.read_bytes().replace(b"test-bytecode", b"bad!-bytecode", 1)
        self.archive.write_bytes(content)
        with self.assertRaisesRegex(ValueError, "Damaged Python standard library"):
            build_embedded.validate_stdlib(self.archive)

    def test_missing_encodings_stops_build(self):
        with ZipFile(self.archive, "w") as archive:
            archive.writestr("io.pyc", b"test-bytecode")
        with self.assertRaisesRegex(ValueError, "Incomplete Python standard library"):
            build_embedded.validate_stdlib(self.archive)
