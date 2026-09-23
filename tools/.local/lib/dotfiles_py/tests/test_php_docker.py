from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotfiles_tools.php_docker import _container_identity


class ContainerIdentityTest(unittest.TestCase):
    def test_uses_the_calling_user_for_normal_invocations(self) -> None:
        with (
            patch("dotfiles_tools.php_docker.os.getuid", return_value=1000),
            patch("dotfiles_tools.php_docker.os.getgid", return_value=1001),
            patch.dict(os.environ, {"SUDO_UID": "", "SUDO_GID": ""}),
        ):
            self.assertEqual(_container_identity(Path.cwd()), (1000, 1001))

    def test_ignores_inherited_sudo_metadata_for_normal_invocations(self) -> None:
        with (
            patch("dotfiles_tools.php_docker.os.getuid", return_value=1000),
            patch("dotfiles_tools.php_docker.os.getgid", return_value=1001),
            patch.dict(os.environ, {"SUDO_UID": "2000", "SUDO_GID": "2001"}),
        ):
            self.assertEqual(_container_identity(Path.cwd()), (1000, 1001))

    def test_uses_the_original_user_for_sudo_invocations(self) -> None:
        with (
            patch("dotfiles_tools.php_docker.os.getuid", return_value=0),
            patch("dotfiles_tools.php_docker.os.getgid", return_value=0),
            patch.dict(os.environ, {"SUDO_UID": "1000", "SUDO_GID": "1001"}),
        ):
            self.assertEqual(_container_identity(Path.cwd()), (1000, 1001))

    def test_uses_the_mounted_directory_owner_for_privileged_automation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            working_directory = Path(directory)
            owner = working_directory.stat()

            with (
                patch("dotfiles_tools.php_docker.os.getuid", return_value=0),
                patch("dotfiles_tools.php_docker.os.getgid", return_value=0),
                patch.dict(os.environ, {"SUDO_UID": "", "SUDO_GID": ""}),
            ):
                self.assertEqual(
                    _container_identity(working_directory),
                    (owner.st_uid, owner.st_gid),
                )


if __name__ == "__main__":
    unittest.main()
