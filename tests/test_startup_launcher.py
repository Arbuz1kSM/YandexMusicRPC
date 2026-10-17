from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from app.startup import _command


class StartupLauncherTests(unittest.TestCase):
    def test_embedded_runtime_uses_launcher_with_spaces(self):
        path = r"C:\Users\User\AppData\Local\Programs\Yandex Music RPC\YandexMusicRPC.exe"
        with patch.object(sys, "_yandex_rpc_launcher", path, create=True):
            self.assertEqual(_command(), f'"{path}" --minimized')

    def test_explicit_executable_overrides_bundled_launcher(self):
        with patch.object(sys, "_yandex_rpc_launcher", "unused.exe", create=True):
            self.assertEqual(_command(Path("explicit.exe")), '"explicit.exe" --minimized')
