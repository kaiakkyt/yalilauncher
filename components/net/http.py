"""HTTP helpers for YaliLauncher.

Move all network request logic into this module so the UI code
doesn't directly call requests. Provides a session with retries
and convenience helpers like `get_json` and `get`.
"""
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter, Retry

DEFAULT_TIMEOUT = 10

_session: Optional[requests.Session] = None


def _get_session() -> requests.Session:
	global _session
	if _session is None:
		s = requests.Session()
		retries = Retry(total=3, backoff_factor=0.3,
						status_forcelist=(429, 500, 502, 503, 504),
						allowed_methods=frozenset(['GET', 'POST']))
		adapter = HTTPAdapter(max_retries=retries)
		s.mount('https://', adapter)
		s.mount('http://', adapter)
		_session = s
	return _session


def get(url: str, *, stream: bool = False, timeout: int = DEFAULT_TIMEOUT, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> requests.Response:
	"""Perform an HTTP GET using a shared session. Returns requests.Response.

	Caller is responsible for calling `resp.raise_for_status()` when appropriate.
	"""
	sess = _get_session()
	resp = sess.get(url, stream=stream, timeout=timeout, params=params, headers=headers)
	return resp


def get_json(url: str, *, timeout: int = DEFAULT_TIMEOUT, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Any:
	"""GET a URL and parse JSON. Raises on HTTP or JSON errors."""
	resp = get(url, stream=False, timeout=timeout, params=params, headers=headers)
	resp.raise_for_status()
	return resp.json()


def head(url: str, *, timeout: int = DEFAULT_TIMEOUT, headers: Optional[Dict[str, str]] = None) -> requests.Response:
	sess = _get_session()
	return sess.head(url, timeout=timeout, headers=headers)
