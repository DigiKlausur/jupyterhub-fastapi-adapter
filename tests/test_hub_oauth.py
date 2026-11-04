import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from jupyterhub_fastapi_adapter import hub_oauth
from jupyterhub_fastapi_adapter.hub_oauth import hub_auth, oauth_callback

app = FastAPI()
app.add_api_route("/oauth_callback", oauth_callback)

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
