"""Preserve an exact checkout-filtered Git object after hash verification."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
from pathlib import Path


def materialize(
    *, source_repo: Path, commit: str, source_path: str,
    destination: Path, expected_sha256: str,
) -> str:
    command = [
        "git", "-c", f"safe.directory={source_repo.as_posix()}", "cat-file",
        "--filters", f"--path={source_path}", f"{commit}:{source_path}",
    ]
    payload = subprocess.check_output(command, cwd=source_repo)
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected_sha256:
        raise ValueError(f"source hash mismatch: expected {expected_sha256}, got {actual}")
    if destination.exists():
        if destination.read_bytes() != payload:
            raise FileExistsError(f"immutable destination differs: {destination}")
        return actual
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    return actual


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--source-path", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    print(materialize(**vars(args)))


if __name__ == "__main__":
    main()
