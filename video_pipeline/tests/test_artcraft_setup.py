"""Download-only safety checks; all HTTP traffic is mocked."""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


SCRIPT = Path(__file__).resolve().parents[2] / ".opencode/skills/post-production-artcraft/scripts/setup.py"
spec = importlib.util.spec_from_file_location("artcraft_setup", SCRIPT)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)
DATA = b"release test bytes"


def artifact(**changes):
    item = {
        "app": "filmcraft", "arch": "x86_64", "tag": "v1.2.3",
        "filename": "FilmCraft-1.2.3-x86_64.AppImage",
        "size": len(DATA), "sha256": hashlib.sha256(DATA).hexdigest(),
        "provenance": "Test fixture, not an actual release",
    }
    item["url"] = f"https://github.com/storytold/filmcraft/releases/download/{item['tag']}/{item['filename']}"
    return item | changes


def response(chunks=(DATA, b""), status=200, headers=None):
    result = MagicMock()
    result.status = status
    result.getheader.side_effect = (headers or {}).get
    result.read1.side_effect = chunks
    return result


class ArtcraftSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.destination = self.root / "downloads"
        self.manifest = self.root / "releases.json"
        self.write_manifest([artifact()])
        self.patch_manifest = patch.object(setup, "MANIFEST", self.manifest)
        self.patch_manifest.start()
        self.addCleanup(self.patch_manifest.stop)

    def write_manifest(self, items):
        self.manifest.write_text(json.dumps({"schema_version": 1, "artifacts": items}))

    def run_cli(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return setup.main(["--destination", str(self.destination), *args])

    def mock_http(self, *responses):
        # Keep protocol validation observable in-process. Watchdog tests below
        # exercise the actual child process separately, without external traffic.
        worker = patch.object(setup, "transfer_worker", side_effect=self.inline_transfer)
        worker.start()
        self.addCleanup(worker.stop)
        factory = patch.object(setup.http.client, "HTTPSConnection")
        mocked = factory.start()
        self.addCleanup(factory.stop)
        connections = [MagicMock() for _ in responses]
        for connection, reply in zip(connections, responses):
            connection.getresponse.return_value = reply
        mocked.side_effect = connections
        return mocked, connections

    @staticmethod
    def inline_transfer(item, fd):
        with os.fdopen(os.dup(fd), "wb") as target:
            setup.stream_artifact(item, target)

    def assert_clean(self):
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_preview_no_network_or_writes(self):
        with patch.object(setup.platform, "system", return_value="Linux"), patch.object(
            setup.platform, "machine", return_value="AMD64"
        ), patch.object(setup.http.client, "HTTPSConnection") as network, patch.object(
            setup.Path, "mkdir"
        ) as mkdir:
            self.assertEqual(self.run_cli(), 0)
        network.assert_not_called()
        mkdir.assert_not_called()
        self.assertFalse(self.destination.exists())

    def test_architecture_aliases_and_missing_pins(self):
        with patch.object(setup.platform, "system", return_value="Linux"):
            self.assertEqual(self.run_cli("--arch", "amd64"), 0)
            self.assertEqual(self.run_cli("--arch", "arm64"), 1)
            self.assertEqual(self.run_cli("--app", "soundcraft", "--arch", "x86_64"), 1)
            with patch.object(setup.platform, "machine", return_value="mips"):
                self.assertEqual(self.run_cli(), 1)
        with patch.object(setup.platform, "system", return_value="Darwin"):
            self.assertEqual(self.run_cli(), 1)

    def test_manifest_validation(self):
        for changes in (
            {"app": []}, {"arch": []},
            {"filename": "../bad"}, {"filename": "é.AppImage"}, {"tag": "latest"},
            {"tag": "../v1"}, {"size": True}, {"size": 0}, {"size": setup.MAX_SIZE + 1},
            {"sha256": "not-a-digest"}, {"provenance": ""},
            {"url": "https://github.com/evil/filmcraft/releases/download/v1.2.3/file"},
            {"url": artifact()["url"] + "?download=1"},
            {"url": artifact()["url"].replace("https:", "http:")},
            {"url": artifact()["url"].replace("github.com", "github.com.evil")},
            {"url": artifact()["url"].replace("github.com", "user@github.com")},
            {"url": artifact()["url"].replace("github.com", "github.com:443")},
        ):
            with self.subTest(changes=changes):
                self.write_manifest([artifact(**changes)])
                with self.assertRaises(ValueError):
                    setup.load_artifact("filmcraft", "x86_64")
        item = artifact()
        del item["size"]
        self.write_manifest([item])
        with self.assertRaises(ValueError):
            setup.load_artifact("filmcraft", "x86_64")
        self.write_manifest([artifact(), artifact()])
        with self.assertRaises(ValueError):
            setup.load_artifact("filmcraft", "x86_64")

    def test_success_and_verified_reuse(self):
        network, connections = self.mock_http(response())
        path, reused = setup.download(artifact(), self.destination)
        self.assertFalse(reused)
        self.assertEqual(path.read_bytes(), DATA)
        self.assertEqual(list(self.destination.iterdir()), [path])
        self.assertEqual(setup.download(artifact(), self.destination), (path, True))
        self.assertEqual(network.call_count, 1)
        connections[0].close.assert_called_once()
        connections[0].getresponse.return_value.close.assert_called_once()
        self.assertEqual(path.stat().st_mode & 0o111, 0)

    def test_official_signed_redirect(self):
        network, _ = self.mock_http(
            response(status=302, headers={"Location": "https://release-assets.githubusercontent.com/a/file?signature=abc"}),
            response(),
        )
        setup.download(artifact(), self.destination)
        self.assertEqual(network.call_count, 2)
        self.assertEqual(network.call_args.args, ("release-assets.githubusercontent.com",))

    def test_unsafe_redirects_and_redirect_bound(self):
        for url in (
            "http://github.com/a", "https://evil.example/a", "https://github.com:443/a",
            "https://user@objects.githubusercontent.com/a", "https://github.com.evil/a",
            "https://objects.githubusercontent.com/a#fragment", "https://github.com\\@evil.example/a",
        ):
            with self.subTest(url=url), patch.object(setup, "transfer_worker", side_effect=self.inline_transfer), patch.object(setup.http.client, "HTTPSConnection") as network:
                network.return_value.getresponse.return_value = response(status=302, headers={"Location": url})
                with self.assertRaises(ValueError):
                    setup.download(artifact(), self.destination)
                self.assertEqual(network.call_count, 1)
                self.assert_clean()
        network, _ = self.mock_http(*[
            response(status=302, headers={"Location": artifact()["url"]})
            for _ in range(setup.MAX_REDIRECTS + 1)
        ])
        with self.assertRaises(ValueError):
            setup.download(artifact(), self.destination)
        self.assertEqual(network.call_count, setup.MAX_REDIRECTS + 1)
        self.assert_clean()

    def test_failed_transfers_cleanup(self):
        for reply in (
            response((DATA[:-1], b"")), response((DATA + b"x", b"")),
            response((b"x" * len(DATA), b"")), response((TimeoutError("socket timed out"),)),
            response(headers={"Content-Length": "999"}), response(status=404),
        ):
            with self.subTest(reply=reply), patch.object(setup, "transfer_worker", side_effect=self.inline_transfer), patch.object(setup.http.client, "HTTPSConnection") as network:
                network.return_value.getresponse.return_value = reply
                with self.assertRaises((ValueError, TimeoutError)):
                    setup.download(artifact(), self.destination)
                self.assert_clean()

    def test_deadline_cleanup(self):
        self.mock_http(response())
        with patch.object(setup.time, "monotonic", side_effect=[0, 0, 0, 0, setup.TRANSFER_DEADLINE + 1]):
            with self.assertRaises(TimeoutError):
                setup.download(artifact(), self.destination)
        self.assert_clean()

    def test_existing_mismatch_and_symlink_are_untouched(self):
        self.destination.mkdir()
        final = self.destination / artifact()["filename"]
        final.write_bytes(b"x" * len(DATA))
        with patch.object(setup.http.client, "HTTPSConnection") as network:
            with self.assertRaises(ValueError):
                setup.download(artifact(), self.destination)
            self.assertEqual(final.read_bytes(), b"x" * len(DATA))
            final.unlink()
            outside = self.root / "outside"
            outside.write_bytes(DATA)
            final.symlink_to(outside)
            with self.assertRaises(OSError):
                setup.download(artifact(), self.destination)
            self.assertTrue(final.is_symlink())
            self.assertEqual(outside.read_bytes(), DATA)
            network.assert_not_called()

    def test_publish_race_never_clobbers(self):
        for winner in (DATA, b"unrelated"):
            with self.subTest(winner=winner):
                self.mock_http(response())
                final = self.destination / artifact()["filename"]

                def race(source, destination, **kwargs):
                    final.write_bytes(winner)
                    raise FileExistsError("another writer won")

                with patch.object(setup.os, "link", side_effect=race):
                    if winner == DATA:
                        self.assertEqual(setup.download(artifact(), self.destination), (final, True))
                    else:
                        with self.assertRaises(ValueError):
                            setup.download(artifact(), self.destination)
                self.assertEqual(final.read_bytes(), winner)
                self.assertEqual(list(self.destination.iterdir()), [final])
                final.unlink()

    def test_publish_race_symlink_is_preserved(self):
        self.mock_http(response())
        outside = self.root / "outside"
        outside.write_bytes(DATA)
        final = self.destination / artifact()["filename"]

        def race(source, destination, **kwargs):
            final.symlink_to(outside)
            raise FileExistsError("symlink won")

        with patch.object(setup.os, "link", side_effect=race):
            with self.assertRaises(OSError):
                setup.download(artifact(), self.destination)
        self.assertTrue(final.is_symlink())
        self.assertEqual(outside.read_bytes(), DATA)
        self.assertEqual(list(self.destination.iterdir()), [final])

    def test_cli_download_is_explicit_and_reports_failures(self):
        network, _ = self.mock_http(response())
        with patch.object(setup.platform, "system", return_value="Linux"):
            self.assertEqual(self.run_cli("--arch", "x86_64", "--download"), 0)
            final = self.destination / artifact()["filename"]
            self.assertEqual(final.read_bytes(), DATA)
            final.write_bytes(b"bad")
            self.assertEqual(self.run_cli("--arch", "x86_64", "--download"), 1)
            self.assertEqual(final.read_bytes(), b"bad")
        self.assertEqual(network.call_count, 1)

    def test_disk_reserve_checked_before_network_or_staging(self):
        with patch.object(setup.os, "fstatvfs") as disk, patch.object(
            setup.http.client, "HTTPSConnection"
        ) as network:
            disk.return_value.f_bavail = setup.DISK_RESERVE
            disk.return_value.f_frsize = 1
            with self.assertRaises(ValueError):
                setup.download(artifact(), self.destination)
            disk.assert_called_once()
            network.assert_not_called()
        self.assert_clean()

    def test_destination_permissions_and_symlink_parents(self):
        self.mock_http(response())
        path, _ = setup.download(artifact(), self.destination)
        self.assertEqual(self.destination.stat().st_mode & 0o777, 0o700)
        path.unlink()
        self.destination.chmod(0o777)
        with self.assertRaisesRegex(ValueError, "not group/world writable"):
            setup.download(artifact(), self.destination)
        self.destination.chmod(0o700)
        alias = self.root / "alias"
        alias.symlink_to(self.destination, target_is_directory=True)
        with self.assertRaises(OSError):
            setup.download(artifact(), alias)
        with self.assertRaises(OSError):
            setup.download(artifact(), alias / "child")
        self.assertFalse((self.destination / "child").exists())
        with patch.object(setup.os, "getuid", return_value=os.getuid() + 1):
            with self.assertRaisesRegex(ValueError, "owned by this user"):
                setup.download(artifact(), self.destination)

    def test_destination_rename_is_anchored_and_refused(self):
        self.mock_http(response())
        moved = self.root / "moved"
        final = self.destination / artifact()["filename"]

        def moved_destination(item, fd):
            self.inline_transfer(item, fd)
            self.destination.rename(moved)
            self.destination.mkdir(mode=0o700)
            final.write_bytes(b"other directory's file")

        with patch.object(setup, "transfer_worker", side_effect=moved_destination):
            with self.assertRaisesRegex(ValueError, "Destination directory changed"):
                setup.download(artifact(), self.destination)
        self.assertEqual(final.read_bytes(), b"other directory's file")
        self.assertEqual(list(moved.iterdir()), [])

    def test_relative_destination_does_not_follow_worker_cwd_change(self):
        self.mock_http(response())
        cwd = Path.cwd()
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()

        def changed_cwd(item, fd):
            self.inline_transfer(item, fd)
            os.chdir(elsewhere)

        try:
            os.chdir(self.root)
            with patch.object(setup, "transfer_worker", side_effect=changed_cwd):
                path, _ = setup.download(artifact(), Path("downloads"))
            self.assertEqual(path, self.destination / artifact()["filename"])
            self.assertEqual(path.read_bytes(), DATA)
            self.assertEqual(list(elsewhere.iterdir()), [])
        finally:
            os.chdir(cwd)

    def test_staging_replacement_before_publication_is_preserved(self):
        def replaced(item, fd):
            self.inline_transfer(item, fd)
            staging = next(self.destination.glob("*.part"))
            staging.unlink()
            staging.write_bytes(b"unverified replacement")

        self.mock_http(response())
        with patch.object(setup, "transfer_worker", side_effect=replaced), patch.object(setup.os, "link") as link:
            with self.assertRaisesRegex(ValueError, "Staging pathname changed"):
                setup.download(artifact(), self.destination)
        link.assert_not_called()
        leftovers = list(self.destination.iterdir())
        self.assertEqual(len(leftovers), 1)
        self.assertEqual(leftovers[0].read_bytes(), b"unverified replacement")

    def test_staging_swap_at_link_never_publishes_unverified_bytes(self):
        self.mock_http(response())
        real_link = os.link
        final = self.destination / artifact()["filename"]

        def swap(source, name, **kwargs):
            staging = next(self.destination.glob("*.part"))
            staging.unlink()
            staging.write_bytes(b"other writer")
            try:
                real_link(source, name, **kwargs)
            finally:
                if final.exists():
                    self.assertEqual(final.read_bytes(), DATA)

        with patch.object(setup.os, "link", side_effect=swap):
            # Linux can also refuse linking an FD whose last name was removed.
            with self.assertRaises((ValueError, FileNotFoundError)):
                setup.download(artifact(), self.destination)
        self.assertFalse(final.exists())
        leftovers = list(self.destination.iterdir())
        self.assertEqual(len(leftovers), 1)
        self.assertEqual(leftovers[0].read_bytes(), b"other writer")

    def test_final_replacement_after_link_is_not_deleted(self):
        self.mock_http(response())
        real_link = os.link
        final = self.destination / artifact()["filename"]

        def swap(source, name, **kwargs):
            real_link(source, name, **kwargs)
            final.unlink()
            final.write_bytes(b"other writer")

        with patch.object(setup.os, "link", side_effect=swap):
            with self.assertRaisesRegex(ValueError, "changed during publication"):
                setup.download(artifact(), self.destination)
        self.assertEqual(list(self.destination.iterdir()), [final])
        self.assertEqual(final.read_bytes(), b"other writer")

    def child_command(self, body):
        # Run the real worker entrypoint with only its HTTP implementation mocked.
        code = (
            "import http.client, json, os, runpy, socket, sys, time\n"
            "from unittest.mock import MagicMock\n"
            f"sys.argv = [{str(SCRIPT)!r}, '--stream-worker', sys.argv[1]]\n"
            "connection = MagicMock()\n"
            "http.client.HTTPSConnection = lambda *a, **k: connection\n"
            + body + "\n"
            f"runpy.run_path({str(SCRIPT)!r}, run_name='__main__')\n"
        )
        real_run = subprocess.run

        def run(command, **kwargs):
            return real_run([sys.executable, "-c", code, command[-1]], **kwargs)

        return patch.object(setup.subprocess, "run", side_effect=run)

    def test_real_worker_success_and_validation_failure(self):
        for data in (DATA, b"x" * len(DATA)):
            with self.subTest(data=data), self.child_command(
                "reply = connection.getresponse.return_value\n"
                "reply.status = 200\n"
                "reply.getheader.return_value = None\n"
                f"reply.read1.side_effect = [{data!r}, b'']"
            ):
                if data == DATA:
                    path, reused = setup.download(artifact(), self.destination)
                    self.assertFalse(reused)
                    self.assertEqual(path.read_bytes(), DATA)
                    path.unlink()
                else:
                    with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                        setup.download(artifact(), self.destination)
                self.assert_clean()

    def test_hard_watchdog_stops_header_trickle_and_blocked_dns(self):
        for phase in ("headers", "dns"):
            pid_path = self.root / "worker-pid"
            body = (
                "def block(*args, **kwargs):\n"
                f"    open({str(pid_path)!r}, 'w').write(str(os.getpid()))\n"
                "    os.write(int(sys.argv[2]), b'partial')\n"
            )
            if phase == "headers":
                # Bytes/headers can keep arriving within each socket timeout.
                body += "    while True:\n        time.sleep(0.01)\n"
                body += "connection.getresponse.side_effect = block"
            else:
                body += "    time.sleep(30)\n"
                body += "socket.getaddrinfo = block\nconnection.connect.side_effect = lambda: socket.getaddrinfo('unused', 443)"
            with self.subTest(phase=phase), self.child_command(body), patch.object(setup, "TRANSFER_DEADLINE", 0.5):
                start = time.monotonic()
                with self.assertRaisesRegex(TimeoutError, "worker stopped"):
                    setup.download(artifact(), self.destination)
                self.assertLess(time.monotonic() - start, 3)
            pid = int(pid_path.read_text())
            with self.assertRaises(ProcessLookupError):
                os.kill(pid, 0)
            self.assert_clean()
            pid_path.unlink()

    def test_parent_verifies_worker_bytes(self):
        def unchecked(item, fd):
            os.write(fd, b"x" * item["size"])

        with patch.object(setup, "transfer_worker", side_effect=unchecked):
            with self.assertRaisesRegex(ValueError, "Staging size or SHA-256 mismatch"):
                setup.download(artifact(), self.destination)
        self.assert_clean()


if __name__ == "__main__":
    unittest.main()
