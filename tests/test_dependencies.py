import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from jupyterhub_fastapi_adapter import dependencies
from jupyterhub_fastapi_adapter.dependencies import User, require_authenticated_user
from jupyterhub_fastapi_adapter.hub_oauth import hub_auth

app = FastAPI()


@app.get("/me")
async def me(user: User = Depends(require_authenticated_user)):
    return {"username": user.username}


client = TestClient(app)


def fake_hub_user(monkeypatch, scopes):
    """Make get_current_user return a hub user model whose token has `scopes`."""

    async def get_current_user(request):
        return {"name": "potato", "admin": False, "groups": [], "scopes": scopes}

    monkeypatch.setattr(dependencies, "get_current_user", get_current_user)


@pytest.mark.parametrize(
    "scopes",
    [
        ["access:services!service=testservice"],
        ["access:services"],  # unfiltered scope covers every service
    ],
)
def test_token_with_access_scope_is_allowed(monkeypatch, scopes):
    fake_hub_user(monkeypatch, scopes)
    resp = client.get("/me")
    assert resp.status_code == 200
    assert resp.json() == {"username": "potato"}


@pytest.mark.parametrize(
    "scopes",
    [
        ["read:users:name!user=potato"],  # e.g. a personal token from /hub/token
        ["access:services!service=otherservice"],  # token for a different service
    ],
)
def test_token_without_access_scope_is_forbidden(monkeypatch, scopes):
    fake_hub_user(monkeypatch, scopes)
    resp = client.get("/me")
    assert resp.status_code == 403


def test_empty_access_scopes_denies_everyone(monkeypatch):
    fake_hub_user(monkeypatch, ["access:services!service=testservice"])
    monkeypatch.setattr(hub_auth, "access_scopes", set())
    resp = client.get("/me")
    assert resp.status_code == 403
