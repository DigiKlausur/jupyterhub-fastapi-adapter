from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from jupyterhub_fastapi_adapter import hub_oauth
from jupyterhub_fastapi_adapter.hub_oauth import (
    JUPYTERHUB_SERVICE_PREFIX,
    AuthenticationRequired,
    authentication_required_handler,
    hub_auth,
    oauth_callback,
)

app = FastAPI()
app.add_api_route("/oauth_callback", oauth_callback)
app.add_exception_handler(AuthenticationRequired, authentication_required_handler)


@app.get(JUPYTERHUB_SERVICE_PREFIX + "page")
async def protected_page(request: Request):
    raise AuthenticationRequired(request)


client = TestClient(app)


@pytest.fixture
def fake_token_exchange(monkeypatch):
    """Make the hub's /oauth2/token endpoint return a fixed access token."""
    real_async_client = httpx.AsyncClient

    def async_client(*args, **kwargs):
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, json={"access_token": "user-token"})
        )
        return real_async_client(*args, transport=transport, **kwargs)

    monkeypatch.setattr(hub_oauth.httpx, "AsyncClient", async_client)


def get_set_cookie(headers=None):
    resp = client.get("/oauth_callback?code=abc", headers=headers, follow_redirects=False)
    assert resp.status_code == 307
    set_cookie = resp.headers["set-cookie"]
    assert set_cookie.startswith(f"{hub_auth.cookie_name}=user-token")
    return set_cookie


def test_cookie_is_httponly_and_not_secure_over_http(fake_token_exchange):
    set_cookie = get_set_cookie()
    assert "HttpOnly" in set_cookie
    assert "Secure" not in set_cookie


def test_cookie_is_secure_behind_https_proxy(fake_token_exchange):
    set_cookie = get_set_cookie(headers={"X-Forwarded-Proto": "https"})
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie


def test_login_redirect_state_is_path_and_query_only():
    resp = client.get(
        JUPYTERHUB_SERVICE_PREFIX + "page?a=1",
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )
    assert resp.status_code == 307
    state = parse_qs(urlparse(resp.headers["location"]).query)["state"][0]
    assert state == JUPYTERHUB_SERVICE_PREFIX + "page?a=1"


def callback_location(state):
    """Where oauth_callback redirects to for the given state."""
    params = {"code": "abc", "state": state}
    resp = client.get("/oauth_callback", params=params, follow_redirects=False)
    return resp.headers["location"]


def test_callback_redirects_to_state_inside_service(fake_token_exchange):
    target = JUPYTERHUB_SERVICE_PREFIX + "page?a=1"
    assert callback_location(target) == target


@pytest.mark.parametrize("state", ["", "https://evil.example/", "//evil.example/", "/hub/home"])
def test_callback_ignores_state_outside_service(fake_token_exchange, state):
    assert callback_location(state) == JUPYTERHUB_SERVICE_PREFIX
