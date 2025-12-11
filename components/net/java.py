from __future__ import annotations

import json
import os
import sys
import time
from typing import Callable, Dict, Optional, Tuple
import subprocess
import shutil
import zipfile
import tarfile
import platform
try:
	import requests
except Exception:
	requests = None

try:
	from urllib.request import urlopen, Request
	from urllib.error import URLError, HTTPError
except Exception:
	urlopen = None

SUPPORTED_MAJORS = [8, 16, 17, 21]

API_ASSETS_URL = (
	"https://api.adoptium.net/v3/assets/feature_releases/{major}/ga"
)


class TemurinError(Exception):
	pass


def _http_get_json(url: str, params: Optional[Dict] = None, timeout: int = 30) -> Dict:
	"""GET JSON from the given URL using requests or urllib fallback.

	This function imports `requests` and `urllib` locally so the
	fallback always works even if module-level imports behaved
	unexpectedly in the environment.
	"""
	try:
		import requests as _requests
	except Exception:
		_requests = None

	if _requests:
		resp = _requests.get(url, params=params or {}, timeout=timeout)
		resp.raise_for_status()
		return resp.json()

	try:
		from urllib.request import urlopen as _urlopen, Request as _Request
		from urllib.error import URLError as _URLError, HTTPError as _HTTPError
	except Exception:
		try:
			import http.client as _httpclient
			from urllib.parse import urlparse as _urlparse
		except Exception:
			raise TemurinError("No HTTP client available (requests, urllib, or http.client)")

		parsed = _urlparse(url)
		conn_cls = _httpclient.HTTPSConnection if parsed.scheme == 'https' else _httpclient.HTTPConnection
		conn = conn_cls(parsed.netloc, timeout=timeout)
		path = parsed.path or '/'
		if parsed.query:
			path += '?' + parsed.query
		try:
			conn.request('GET', path)
			resp = conn.getresponse()
			data = resp.read()
			if resp.status >= 400:
				raise TemurinError(f"HTTP error: {resp.status} {resp.reason}")
			return json.loads(data.decode('utf-8'))
		except Exception as e:
			raise TemurinError(f"HTTP client fallback failed: {e}")

	if params:
		qs = "&".join(f"{k}={v}" for k, v in (params or {}).items())
		url = url + ("?" + qs if qs else "")
	req = _Request(url)
	try:
		with _urlopen(req, timeout=timeout) as fh:
			data = fh.read()
			return json.loads(data.decode("utf-8"))
	except _HTTPError as e:
		raise TemurinError(f"HTTP error: {e.code} {e.reason}")
	except _URLError as e:
		raise TemurinError(f"URL error: {e.reason}")


def _select_asset_for_major(major: int, os_name: str = "windows", arch: str = "x64") -> Tuple[str, str]:
	"""Query the Adoptium assets API and return (download_url, filename).

	Raises TemurinError on failure.
	"""
	url = API_ASSETS_URL.format(major=major)
	params = {
		"image_type": "jdk",
		"jvm_impl": "hotspot",
		"os": os_name,
		"architecture": arch,
		"heap_size": "normal",
	}

	last_exc = None
	tried_urls = []
	for (u, p) in (
		(url, params),
		(API_ASSETS_URL.format(major=major).rsplit('/ga', 1)[0], params),
		(url, {**params, 'release_type': 'ga'}),
		(API_ASSETS_URL.format(major=major).rsplit('/ga', 1)[0], {**params, 'release_type': 'ga'}),
	):
		try:
			tried_urls.append((u, p))
			data = _http_get_json(u, params=p)
			if isinstance(data, list) and data:
				break
		except Exception as e:
			last_exc = e
			data = None

	if not isinstance(data, list) or not data:
		msg = f"No assets returned for Java {major}. Tried: {tried_urls}"
		if last_exc:
			msg += f"; last error: {last_exc}"
		try:
			vendor_params = {**params, 'vendor': 'eclipse-temurin'}
			data = _http_get_json(url, params=vendor_params)
			if isinstance(data, list) and data:
				pass
			else:
				data = None
		except Exception as e:
			data = None

		package_types = ['zip', 'tar.gz', 'tar.xz', 'msi', 'exe', 'pkg']
		binary_base = 'https://api.adoptium.net/v3/binary/latest/{major}/ga/{os}/{arch}/{image_type}/{jvm_impl}'
		for ptype in package_types:
			cand = binary_base.format(major=major, os=os_name, arch=arch, image_type='jdk', jvm_impl='hotspot')
			cand_url = cand + '/' + ptype
			try:
				status, headers = _http_head(cand_url)
				if status and (200 <= status < 400):
					loc = headers.get('Location') or headers.get('location')
					if loc:
						filename = os.path.basename(loc.split('?')[0])
						return loc, filename
					return cand_url, os.path.basename(cand_url)
			except Exception:
				continue

		raise TemurinError(msg)

	best = None
	best_ts = 0
	for entry in data:
		ts = 0
		for key in ("release_date", "release_name", "timestamp", "release_timestamp"):
			val = entry.get(key)
			if isinstance(val, str):
				try:
					ts = int(time.mktime(time.strptime(val.split("+")[0], "%Y-%m-%dT%H:%M:%S")))
				except Exception:
					ts = len(val)
			elif isinstance(val, (int, float)):
				ts = int(val)
		if ts >= best_ts:
			best_ts = ts
			best = entry

	if not best:
		best = data[0]

	binaries = best.get("binaries") or best.get("binary") or []
	if not binaries:
		pkg = best.get("package")
		if pkg and isinstance(pkg, dict) and pkg.get("link"):
			return pkg.get("link"), pkg.get("name") or os.path.basename(pkg.get("link"))
		raise TemurinError(f"No binary packages available for Java {major}")

	for b in binaries:
		pkg = b.get("package") if isinstance(b, dict) else None
		if not pkg:
			pkg = None
			if isinstance(b, dict):
				pkg = b.get("binary", {}).get("package") or b.get("package")
		if pkg and isinstance(pkg, dict) and pkg.get("link"):
			return pkg.get("link"), pkg.get("name") or os.path.basename(pkg.get("link"))

	raise TemurinError(f"Unable to select a binary package for Java {major}")


def _stream_download(url: str, dest_path: str, progress_cb: Optional[Callable[[int, Optional[int]], None]] = None, chunk_size: int = 64 * 1024):
	"""Stream-download URL to dest_path. progress_cb(bytes_read, total_bytes).

	Uses requests when available; otherwise urllib streaming.
	"""
	try:
		import requests as _requests
	except Exception:
		_requests = None

	if _requests:
		with _requests.get(url, stream=True) as r:
			r.raise_for_status()
			total = int(r.headers.get("Content-Length") or 0) or None
			read = 0
			with open(dest_path, "wb") as fh:
				for chunk in r.iter_content(chunk_size=chunk_size):
					if not chunk:
						continue
					fh.write(chunk)
					read += len(chunk)
					if progress_cb:
						try:
							progress_cb(read, total)
						except Exception:
							pass
		return

	try:
		from urllib.request import urlopen as _urlopen, Request as _Request
		from urllib.error import URLError as _URLError, HTTPError as _HTTPError
	except Exception:
		try:
			import http.client as _httpclient
			from urllib.parse import urlparse as _urlparse
		except Exception:
			raise TemurinError("No HTTP client available for download (requests, urllib, or http.client)")

		parsed = _urlparse(url)
		conn_cls = _httpclient.HTTPSConnection if parsed.scheme == 'https' else _httpclient.HTTPConnection
		conn = conn_cls(parsed.netloc, timeout=30)
		path = parsed.path or '/'
		if parsed.query:
			path += '?' + parsed.query
		try:
			conn.request('GET', path)
			resp = conn.getresponse()
			if resp.status >= 400:
				raise TemurinError(f"HTTP error while downloading: {resp.status} {resp.reason}")
			total = None
			try:
				total = int(resp.getheader('Content-Length'))
			except Exception:
				total = None
			read = 0
			with open(dest_path, 'wb') as out:
				while True:
					chunk = resp.read(chunk_size)
					if not chunk:
						break
					out.write(chunk)
					read += len(chunk)
					if progress_cb:
						try:
							progress_cb(read, total)
						except Exception:
							pass
			return
		except Exception as e:
			raise TemurinError(f"http.client download failed: {e}")

	req = _Request(url)
	try:
		with _urlopen(req) as fh:
			meta = fh.info()
			total = None
			try:
				total = int(meta.get("Content-Length"))
			except Exception:
				total = None
			read = 0
			with open(dest_path, "wb") as out:
				while True:
					chunk = fh.read(chunk_size)
					if not chunk:
						break
					out.write(chunk)
					read += len(chunk)
					if progress_cb:
						try:
							progress_cb(read, total)
						except Exception:
							pass
	except _HTTPError as e:
		raise TemurinError(f"HTTP error while downloading: {e.code} {e.reason}")
	except _URLError as e:
		raise TemurinError(f"URL error while downloading: {e.reason}")


def _http_head(url: str, timeout: int = 10) -> Tuple[Optional[int], Dict[str, str]]:
	"""Perform a HEAD request and return (status_code, headers dict).

	Uses requests if present, otherwise falls back to urllib/http.client.
	"""
	try:
		import requests as _requests
	except Exception:
		_requests = None

	if _requests:
		r = _requests.head(url, allow_redirects=True, timeout=timeout)
		return r.status_code, {k: v for k, v in r.headers.items()}

	try:
		from urllib.request import Request as _Request, urlopen as _urlopen
	except Exception:
		try:
			import http.client as _httpclient
			from urllib.parse import urlparse as _urlparse
		except Exception:
			raise TemurinError("No HTTP client available for HEAD request")
		parsed = _urlparse(url)
		conn_cls = _httpclient.HTTPSConnection if parsed.scheme == 'https' else _httpclient.HTTPConnection
		conn = conn_cls(parsed.netloc, timeout=timeout)
		path = parsed.path or '/'
		if parsed.query:
			path += '?' + parsed.query
		conn.request('HEAD', path)
		resp = conn.getresponse()
		headers = {k: v for k, v in resp.getheaders()}
		return resp.status, headers

	req = _Request(url, method='HEAD')
	try:
		with _urlopen(req, timeout=timeout) as fh:
			headers = dict(fh.getheaders()) if hasattr(fh, 'getheaders') else {}
			status = getattr(fh, 'status', None)
			return status, headers
	except Exception as e:
		raise TemurinError(f"HEAD request failed: {e}")


def download_temurin(major: int, dest_dir: str, os_name: Optional[str] = None, arch: str = "x64", progress_cb: Optional[Callable[[int, Optional[int]], None]] = None, install: bool = False, install_dir: Optional[str] = None, set_java_home: bool = False) -> str:
	"""Download a Temurin JDK for the requested major to dest_dir.

	Returns the full path to the downloaded file. Raises TemurinError on failure.
	"""
	if major not in SUPPORTED_MAJORS:
		raise TemurinError(f"Unsupported major: {major}. Supported: {SUPPORTED_MAJORS}")

	os_name = os_name or ("windows" if sys.platform.startswith("win") else "linux" if sys.platform.startswith("linux") else "mac")
	os_name = "mac" if os_name == "darwin" else os_name

	download_url, filename = _select_asset_for_major(major, os_name=os_name, arch=arch)

	os.makedirs(dest_dir, exist_ok=True)
	dest_path = os.path.join(dest_dir, filename)

	if os.path.exists(dest_path):
		return dest_path

	_stream_download(download_url, dest_path, progress_cb=progress_cb)

	if install:
		installed = install_temurin(major, dest_path, install_dir=install_dir, set_java_home=set_java_home)
		return dest_path if installed is None else str(installed)

	return dest_path


def install_temurin(major: int, installer_path: str, install_dir: Optional[str] = None, set_java_home: bool = False) -> Optional[str]:
	"""Attempt to execute or extract the downloaded Temurin package.

	Returns an installation path when available (e.g. extraction dir),
	or None when the installer was executed but the install location is not
	determinable.

	This function does not attempt to forcibly elevate privileges. If
	an operation fails due to permissions, the caller should re-run with
	appropriate privileges.
	"""
	if not os.path.exists(installer_path):
		raise TemurinError(f"Installer not found: {installer_path}")

	system = platform.system().lower()
	lower = installer_path.lower()

	if install_dir:
		target = install_dir
	else:
		if system == "windows":
			target = None
		elif system == "darwin":
			target = "/Library/Java/JavaVirtualMachines"
		else:
			try:
				is_root = os.geteuid() == 0
			except Exception:
				is_root = False
			target = "/usr/lib/jvm" if is_root else os.path.join(os.path.expanduser("~"), ".local", "opt")

	if system.startswith("win"):
		if lower.endswith('.msi'):
			cmd = ['msiexec', '/i', installer_path, '/qn', '/norestart']
			try:
				subprocess.run(cmd, check=True)
				return None
			except subprocess.CalledProcessError as e:
				raise TemurinError(f"msiexec failed: {e}")
		elif lower.endswith('.exe'):
			tried = []
			for flags in (['/s'], ['/quiet'], ['/qn'], []):
				cmd = [installer_path] + flags
				tried.append(' '.join(cmd))
				try:
					subprocess.run(cmd, check=True)
					return None
				except Exception:
					continue
			raise TemurinError(f"Failed to run EXE installer (attempts: {tried})")

	if system == 'darwin':
		if lower.endswith('.pkg'):
			cmd = ['installer', '-pkg', installer_path, '-target', '/']
			try:
				subprocess.run(cmd, check=True)
				return None
			except subprocess.CalledProcessError as e:
				raise TemurinError(f"macOS installer failed: {e}")

	if lower.endswith('.tar.gz') or lower.endswith('.tgz') or lower.endswith('.tar.xz'):
		if not target:
			raise TemurinError("No target directory configured for extraction")
		os.makedirs(target, exist_ok=True)
		try:
			shutil.unpack_archive(installer_path, extract_dir=target)
			entries = [e for e in os.listdir(target) if os.path.isdir(os.path.join(target, e))]
			new_dirs = sorted(entries, key=lambda n: os.path.getmtime(os.path.join(target, n)), reverse=True)
			if new_dirs:
				installed = os.path.join(target, new_dirs[0])
			else:
				installed = target
			if set_java_home:
				_maybe_set_java_home(installed)
			return installed
		except Exception as e:
			raise TemurinError(f"Extraction failed: {e}")

	if lower.endswith('.zip'):
		if not target:
			target = os.path.join(os.path.expanduser('~'), '.local', 'opt')
		os.makedirs(target, exist_ok=True)
		try:
			with zipfile.ZipFile(installer_path, 'r') as z:
				z.extractall(target)
			entries = [e for e in os.listdir(target) if os.path.isdir(os.path.join(target, e))]
			new_dirs = sorted(entries, key=lambda n: os.path.getmtime(os.path.join(target, n)), reverse=True)
			installed = os.path.join(target, new_dirs[0]) if new_dirs else target
			if set_java_home:
				_maybe_set_java_home(installed)
			return installed
		except Exception as e:
			raise TemurinError(f"ZIP extraction failed: {e}")

	try:
		subprocess.run([installer_path], check=True)
		return None
	except Exception as e:
		raise TemurinError(f"Unknown installer type and execution failed: {e}")


def _maybe_set_java_home(installed_path: str):
	"""Attempt to set JAVA_HOME for the current user when reasonable.

	This writes to user profile files on Unix-like systems and uses
	`setx` on Windows. It is conservative and will not overwrite system
	files.
	"""
	system = platform.system().lower()
	if system.startswith('win'):
		try:
			subprocess.run(['setx', 'JAVA_HOME', installed_path], check=True)
		except Exception:
			pass
		return

	profile = os.path.join(os.path.expanduser('~'), '.profile')
	line = f'export JAVA_HOME="{installed_path}"\n'
	try:
		if os.path.exists(profile):
			with open(profile, 'r', encoding='utf-8') as f:
				contents = f.read()
			if 'JAVA_HOME' in contents:
				return
		with open(profile, 'a', encoding='utf-8') as f:
			f.write('\n# Added by YaliLauncher/Temurin installer\n')
			f.write(line)
	except Exception:
		pass


if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(description="Download Temurin JDK for a given major")
	parser.add_argument("major", type=int, choices=SUPPORTED_MAJORS, help="Java major to download")
	parser.add_argument("dest", nargs="?", default=".", help="Destination directory")
	parser.add_argument("--install", action='store_true', help="Run installer/extract after download")
	parser.add_argument("--install-dir", default=None, help="Target directory to extract archives (if applicable)")
	parser.add_argument("--set-java-home", action='store_true', help="Attempt to set JAVA_HOME after extraction")
	args = parser.parse_args()

	def cb(read, total):
		if total:
			pct = (read / total) * 100
			print(f"Downloaded {read}/{total} ({pct:.1f}%)", end="\r")
		else:
			print(f"Downloaded {read} bytes", end="\r")

	try:
		path = download_temurin(args.major, args.dest, progress_cb=cb, install=args.install, install_dir=args.install_dir, set_java_home=args.set_java_home)
		print("\nResult:", path)
	except Exception as e:
		print("Error:", e)