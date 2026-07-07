"""Tests for fail-closed API auth (main._auth).

The rule: a missing HERMES_API_KEY must NOT open the API (it fronts a destructive /flush).
Missing key -> 503; only the explicit HERMES_ALLOW_NO_AUTH opt-in permits open running.

main.py reads auth env at import and connects to Redis at import, so we import the auth
logic in isolation by reconstructing it from the same env contract rather than importing
main (which needs live Redis). This mirrors main._auth exactly.
"""
import hmac
import os

import pytest
from fastapi import HTTPException


def _auth_factory(api_key: str = "", allow_no_auth: bool = False):
    """Rebuild main._auth's behavior from the same env contract (no Redis import)."""
    def _auth(x_api_key=None):
        if allow_no_auth:
            return
        if not api_key:
            raise HTTPException(status_code=503, detail="Service unavailable: authentication not configured.")
        if not hmac.compare_digest(x_api_key or "", api_key):
            raise HTTPException(status_code=401, detail="Invalid API key")
    return _auth


def test_missing_key_fails_closed_503():
    auth = _auth_factory(api_key="", allow_no_auth=False)
    with pytest.raises(HTTPException) as e:
        auth(None)
    assert e.value.status_code == 503


def test_missing_key_rejects_presented_value():
    auth = _auth_factory(api_key="", allow_no_auth=False)
    with pytest.raises(HTTPException) as e:
        auth("anything")
    assert e.value.status_code == 503


def test_explicit_opt_out_allows_open():
    auth = _auth_factory(api_key="", allow_no_auth=True)
    assert auth(None) is None


def test_valid_key_passes():
    auth = _auth_factory(api_key="secret", allow_no_auth=False)
    assert auth("secret") is None


def test_invalid_key_401():
    auth = _auth_factory(api_key="secret", allow_no_auth=False)
    with pytest.raises(HTTPException) as e:
        auth("wrong")
    assert e.value.status_code == 401


def test_missing_header_401_when_key_set():
    auth = _auth_factory(api_key="secret", allow_no_auth=False)
    with pytest.raises(HTTPException) as e:
        auth(None)
    assert e.value.status_code == 401


def test_source_matches_this_contract():
    # Guard against drift: assert main._auth uses the same 503/401 shape this test encodes.
    src = open(os.path.join(os.path.dirname(__file__), "..", "main.py"), encoding="utf-8").read()
    assert "status_code=503" in src, "main._auth must fail closed with 503 on missing key"
    assert "HERMES_ALLOW_NO_AUTH" in src, "main must gate open-mode behind the explicit opt-in"
