"""
JupyterHub OAuth authentication utilities for FastAPI services.

Provides OAuth redirect-based authentication with cookie support,
as opposed to the token-based auth in dependencies.py.
"""

import os
from urllib.parse import urlencode

import httpx
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jupyterhub.services.auth import HubOAuth

# Environment variables
JUPYTERHUB_API_URL = os.environ["JUPYTERHUB_API_URL"]
JUPYTERHUB_API_TOKEN = os.environ["JUPYTERHUB_API_TOKEN"]
JUPYTERHUB_SERVICE_PREFIX = os.environ["JUPYTERHUB_SERVICE_PREFIX"]

# Initialize HubOAuth instance at module level
hub_auth = HubOAuth()


class AuthenticationRequired(Exception):
    """Raised when authentication is required but user is not logged in."""

    def __init__(self, request: Request):
        self.request = request
        super().__init__("Authentication required")


def get_token_from_request(request: Request) -> str | None:
    """Extract the user's OAuth token from JupyterHub's cookie or Authorization header."""
    # JupyterHub sets this cookie after OAuth login
    token = request.cookies.get(hub_auth.cookie_name)
    if token:
        return token

    # Fallback: Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("token "):
        return auth_header[len("token ") :]
    if auth_header.startswith("Bearer "):
        return auth_header[len("Bearer ") :]

    return None


async def authentication_required_handler(request: Request, exc: AuthenticationRequired):
    """Handle authentication required by redirecting to OAuth.

    Returns OK for health checks.
    """
    # For health checks (no Accept: text/html), return 200 so
    # JupyterHub knows the service is alive
    accept = request.headers.get("Accept", "")
    if "text/html" not in accept:
        return HTMLResponse(content="OK", status_code=200)

    # Detect redirect loop: if we just came from oauth_callback but still failed auth,
    # something is broken (e.g., JupyterHub API down, token validation issues)
    referer = request.headers.get("Referer", "")
    if "oauth_callback" in referer:
        return HTMLResponse(
            content=(
                "<h1>Authentication Error</h1>"
                "<p>Unable to validate credentials after successful OAuth login.</p>"
                "<p>This may indicate a temporary service issue. Please try again later.</p>"
            ),
            status_code=500,
        )

    # For browser requests, redirect to OAuth login
    state = str(request.url)
    authorize_url = (
        hub_auth.oauth_authorization_url
        + "?"
        + urlencode(
            {
                "client_id": hub_auth.oauth_client_id,
                "redirect_uri": hub_auth.oauth_redirect_uri,
                "response_type": "code",
                "state": state,
            }
        )
    )
    return RedirectResponse(url=authorize_url)


async def oauth_callback(request: Request, code: str = "", state: str = ""):
    """Exchange the OAuth code for a token — JupyterHub sets the cookie automatically."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{JUPYTERHUB_API_URL}/oauth2/token",
            data={
                "client_id": hub_auth.oauth_client_id,
                "client_secret": JUPYTERHUB_API_TOKEN,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": hub_auth.oauth_redirect_uri,
            },
        )
    if resp.status_code != 200:
        return HTMLResponse(content="<h1>Authentication failed</h1>", status_code=502)

    token_data = resp.json()
    token = token_data["access_token"]

    next_url = state or JUPYTERHUB_SERVICE_PREFIX
    response = RedirectResponse(url=next_url)
    response.set_cookie(
        key=hub_auth.cookie_name,
        value=token,
        path=hub_auth.base_url,
    )
    return response
