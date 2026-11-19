#!/usr/bin/env python3
"""Preview or download a pinned ArtCraft Linux release; never install or run it."""

import argparse
import hashlib
import http.client
import json
import os
import platform
import re
import secrets
import stat
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit


SCRIPT = Path(__file__).resolve()
MANIFEST = SCRIPT.with_name("releases.json")
DEFAULT_DESTINATION = SCRIPT.parents[4] / "video_pipeline/workspace/artcraft-setup/downloads"
REPOSITORIES = {
    "filmcraft": "storytold/filmcraft",
    "effectcraft": "storytold/effectcraft",
    "soundcraft": "storytold/soundcraft",
}
ARCHES = {"x86_64": "x86_64", "amd64": "x86_64", "aarch64": "aarch64", "arm64": "aarch64"}
DELIVERY_HOSTS = {"github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}
MAX_SIZE = 2 * 1024**3
DISK_RESERVE = 64 * 1024**2
SOCKET_TIMEOUT = 15
TRANSFER_DEADLINE = 600
MAX_REDIRECTS = 5
CHUNK = 1024 * 1024
SAFE_COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*", re.ASCII)


def checked_url(url):
    """Accept only HTTPS GitHub delivery URLs, including signed asset queries."""
    if not isinstance(url, str) or not url.isascii() or any(ord(c) <= 32 or ord(c) == 127 for c in url):
        raise ValueError("Unsafe download URL")
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https" or parsed.hostname not in DELIVERY_HOSTS
        or parsed.username is not None or parsed.password is not None
        or parsed.netloc != parsed.hostname or parsed.fragment
        or "\\" in url or not parsed.path.startswith("/")
    ):
        raise ValueError("Unsafe download URL")
    return parsed


def load_artifact(app, arch):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
        raise ValueError("Expected manifest schema_version 1")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("Expected manifest artifacts list")
    matches = []
    for item in artifacts:
        required = {"app", "arch", "tag", "filename", "url", "size", "sha256", "provenance"}
        if not isinstance(item, dict) or not required <= item.keys():
            raise ValueError("Incomplete pinned artifact")
        if (
            not isinstance(item["app"], str) or item["app"] not in REPOSITORIES
            or not isinstance(item["arch"], str) or item["arch"] not in {"x86_64", "aarch64"}
        ):
            raise ValueError("Unknown pinned app or architecture")
        for name in ("tag", "filename"):
            value = item[name]
            if not isinstance(value, str) or not SAFE_COMPONENT.fullmatch(value) or value in {".", ".."}:
                raise ValueError(f"Unsafe artifact {name}")
        if item["tag"].lower() == "latest":
            raise ValueError("Release must use a pinned tag, not latest")
        if type(item["size"]) is not int or not 0 < item["size"] <= MAX_SIZE:
            raise ValueError("Invalid pinned artifact size")
        if not isinstance(item["sha256"], str) or not re.fullmatch(r"[0-9a-fA-F]{64}", item["sha256"]):
            raise ValueError("Invalid pinned SHA-256")
        if not isinstance(item["provenance"], str) or not item["provenance"].strip():
            raise ValueError("Artifact provenance is required")
        expected = (
            f"https://github.com/{REPOSITORIES[item['app']]}/releases/download/"
            f"{item['tag']}/{item['filename']}"
        )
        checked_url(item["url"])
        if item["url"] != expected:
            raise ValueError("Artifact URL does not match its trusted repository/tag/filename")
        if (item["app"], item["arch"]) == (app, arch):
            matches.append(item)
    if len(matches) != 1:
        raise ValueError(f"Expected one pinned Linux artifact for {app}/{arch}; found {len(matches)}")
    return matches[0]


def existing_matches(path, artifact, directory_fd):
    """Read through an O_NOFOLLOW descriptor; never replace an existing path."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    except FileNotFoundError:
        return False
    with os.fdopen(fd, "rb") as source:
        metadata = os.fstat(source.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != artifact["size"]:
            raise ValueError(f"Existing destination is not the expected regular file: {path}")
        digest = hashlib.file_digest(source, "sha256").hexdigest()
        current = os.stat(path, dir_fd=directory_fd, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (metadata.st_dev, metadata.st_ino):
            raise ValueError(f"Destination changed during verification: {path}")
        if digest != artifact["sha256"].lower():
            raise ValueError(f"Existing destination SHA-256 mismatch: {path}")
    return True


def remaining(deadline):
    left = deadline - time.monotonic()
    if left <= 0:
        raise TimeoutError("Download transfer deadline exceeded")
    return min(SOCKET_TIMEOUT, left)


def stream_artifact(artifact, target):
    deadline = time.monotonic() + TRANSFER_DEADLINE
    url = artifact["url"]
    for redirects in range(MAX_REDIRECTS + 1):
        parsed = checked_url(url)
        connection = http.client.HTTPSConnection(parsed.hostname, timeout=remaining(deadline))
        response = None
        try:
            connection.connect()
            sock = connection.sock
            sock.settimeout(remaining(deadline))
            path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
            connection.request("GET", path, headers={"User-Agent": "lesson-studio-artcraft-setup"})
            sock.settimeout(remaining(deadline))
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                if not location or redirects == MAX_REDIRECTS:
                    raise ValueError("Missing redirect location or too many redirects")
                url = urljoin(url, location)
                checked_url(url)
                continue
            if response.status != 200:
                raise ValueError(f"Download returned HTTP {response.status}")
            length = response.getheader("Content-Length")
            if length is not None and length != str(artifact["size"]):
                raise ValueError("Download Content-Length differs from pinned size")
            count = 0
            digest = hashlib.sha256()
            while True:
                sock.settimeout(remaining(deadline))
                chunk = response.read1(min(CHUNK, artifact["size"] - count + 1))
                remaining(deadline)
                if not chunk:
                    break
                count += len(chunk)
                if count > artifact["size"]:
                    raise ValueError("Download exceeds pinned size")
                target.write(chunk)
                digest.update(chunk)
            if count != artifact["size"]:
                raise ValueError("Download truncated before pinned size")
            if digest.hexdigest() != artifact["sha256"].lower():
                raise ValueError("Download SHA-256 mismatch")
            return
        finally:
            if response is not None:
                response.close()
            connection.close()


def transfer_worker(artifact, fd):
    """Only trusted local Python runs; the child gets a staging FD, not its path."""
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--stream-worker", str(fd)],
            input=json.dumps(artifact).encode(), pass_fds=(fd,),
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=TRANSFER_DEADLINE,
        )
    except subprocess.TimeoutExpired as error:
        # run() kills and reaps the child before raising, including blocked DNS/headers.
        raise TimeoutError("Download transfer deadline exceeded (worker stopped)") from error
    if result.returncode:
        raise ValueError(f"Download worker failed: {result.stderr.decode(errors='replace').strip()}")


def open_destination(destination, create=True):
    """Anchor every component without following symlinks (including parents)."""
    directory_fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in Path(os.path.abspath(destination)).parts[1:]:
            if create:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=directory_fd)
                except FileExistsError:
                    pass
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = child
        metadata = os.fstat(directory_fd)
        if metadata.st_uid != os.getuid() or metadata.st_mode & 0o022:
            raise ValueError("Destination must be owned by this user and not group/world writable")
        return directory_fd
    except BaseException:
        os.close(directory_fd)
        raise


def same_inode(metadata, other):
    return (metadata.st_dev, metadata.st_ino) == (other.st_dev, other.st_ino)


def path_is_inode(name, directory_fd, metadata):
    try:
        return same_inode(metadata, os.stat(name, dir_fd=directory_fd, follow_symlinks=False))
    except FileNotFoundError:
        return False


def check_destination(destination, directory_fd):
    current_fd = open_destination(destination, create=False)
    try:
        if not same_inode(os.fstat(directory_fd), os.fstat(current_fd)):
            raise ValueError("Destination directory changed")
    finally:
        os.close(current_fd)


def download(artifact, destination):
    # Freeze relative paths before starting the child; never resolve symlink parents.
    destination = Path(os.path.abspath(destination))
    directory_fd = open_destination(destination)
    name = artifact["filename"]
    final = destination / name
    staging = None
    fd = None
    metadata = None
    published = False
    try:
        if existing_matches(name, artifact, directory_fd):
            check_destination(destination, directory_fd)
            return final, True
        space = os.fstatvfs(directory_fd)
        if space.f_bavail * space.f_frsize < artifact["size"] + DISK_RESERVE:
            raise ValueError("Not enough free disk space for artifact and reserve")
        staging = f".{name}.{secrets.token_hex(16)}.part"
        fd = os.open(staging, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
        metadata = os.fstat(fd)
        transfer_worker(artifact, fd)
        os.fsync(fd)
        # The parent, not the network child, verifies the inode it will publish.
        with os.fdopen(os.dup(fd), "rb") as source:
            source.seek(0)
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        if os.fstat(fd).st_size != artifact["size"] or digest != artifact["sha256"].lower():
            raise ValueError("Staging size or SHA-256 mismatch")
        if not path_is_inode(staging, directory_fd, metadata):
            raise ValueError("Staging pathname changed before publication")
        try:
            # Linux linkat follows this proc FD, not the replaceable staging name.
            # Fail closed if procfs is unavailable; never fall back to a path link.
            os.link(f"/proc/self/fd/{fd}", name, dst_dir_fd=directory_fd, follow_symlinks=True)
            published = True
        except FileExistsError:
            if not existing_matches(name, artifact, directory_fd):
                raise ValueError("Destination disappeared during publication")
            check_destination(destination, directory_fd)
            return final, True
        if not path_is_inode(name, directory_fd, metadata) or not path_is_inode(staging, directory_fd, metadata):
            raise ValueError("Destination or staging changed during publication")
        check_destination(destination, directory_fd)
        return final, False
    except BaseException:
        if published and path_is_inode(name, directory_fd, metadata):
            os.unlink(name, dir_fd=directory_fd)
        raise
    finally:
        if metadata is not None and path_is_inode(staging, directory_fd, metadata):
            os.unlink(staging, dir_fd=directory_fd)
        if fd is not None:
            os.close(fd)
        os.close(directory_fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Download only; default is a no-network, no-write preview")
    parser.add_argument("--app", choices=REPOSITORIES, default="filmcraft")
    parser.add_argument("--arch", choices=ARCHES, help="Default: native host (amd64/arm64 aliases accepted)")
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    args = parser.parse_args(argv)
    try:
        if platform.system() != "Linux":
            raise ValueError("Only Linux downloads are supported")
        arch = ARCHES.get((args.arch or platform.machine()).lower())
        if arch is None:
            raise ValueError(f"Unsupported native architecture: {platform.machine()}")
        artifact = load_artifact(args.app, arch)
        final = args.destination / artifact["filename"]
        print(f"{'Download only' if args.download else 'Preview (no network or writes)'}: {args.app}/{arch} {artifact['tag']}")
        print(f"Source: {artifact['url']}")
        print(f"Destination: {final}")
        print(f"Bytes: {artifact['size']}; SHA-256: {artifact['sha256']}")
        if args.download:
            final, reused = download(artifact, args.destination)
            print(f"{'Reused verified file' if reused else 'Downloaded and verified'}: {final}")
        else:
            print("Pass --download to fetch this artifact. Nothing is installed or executed.")
        return 0
    except (OSError, ValueError, http.client.HTTPException) as error:
        print(f"ArtCraft setup error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--stream-worker":
        try:
            with os.fdopen(int(sys.argv[2]), "wb") as target:
                stream_artifact(json.load(sys.stdin), target)
        except (OSError, ValueError, http.client.HTTPException) as error:
            print(error, file=sys.stderr)
            sys.exit(1)
        sys.exit(0)
    sys.exit(main())
