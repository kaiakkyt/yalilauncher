"""Downloader helpers for YaliLauncher.

This module exposes `download_file` which downloads a URL to a path
and reports progress via an optional callback. It uses `components.net.http`
for the underlying requests session so retry behaviour is shared.
"""
import os
import hashlib
from typing import Optional, Callable
from . import http

ProgressCallback = Optional[Callable[[int, int], None]]  # downloaded, total


def _sha256_of_file(path: str, chunk_size: int = 65536) -> str:
	h = hashlib.sha256()
	with open(path, 'rb') as f:
		for chunk in iter(lambda: f.read(chunk_size), b''):
			h.update(chunk)
	return h.hexdigest()


def download_file(url: str, dest_path: str, progress_cb: ProgressCallback = None, expected_sha256: Optional[str] = None, timeout: int = 30) -> str:
	"""Download `url` to `dest_path`.

	- `progress_cb(downloaded_bytes, total_bytes)` will be called intermittently if provided.
	- If `expected_sha256` is provided the file will be validated and removed on mismatch.
	- Returns the final path on success, raises on errors.
	"""
	tmp = dest_path + '.part'
	os.makedirs(os.path.dirname(dest_path) or '.', exist_ok=True)

	resp = http.get(url, stream=True, timeout=timeout)
	resp.raise_for_status()

	total = int(resp.headers.get('content-length') or 0)
	downloaded = 0

	with open(tmp, 'wb') as fh:
		for chunk in resp.iter_content(chunk_size=8192):
			if not chunk:
				continue
			fh.write(chunk)
			downloaded += len(chunk)
			if progress_cb:
				try:
					progress_cb(downloaded, total)
				except Exception:
					pass

	os.replace(tmp, dest_path)

	if expected_sha256:
		actual = _sha256_of_file(dest_path)
		if actual.lower() != expected_sha256.lower():
			try:
				os.remove(dest_path)
			except Exception:
				pass
			raise ValueError(f"checksum mismatch for {dest_path}: expected {expected_sha256}, got {actual}")

	return dest_path
