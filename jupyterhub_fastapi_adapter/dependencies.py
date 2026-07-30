import httpx
from fastapi import Request
from pydantic import BaseModel, Field

from .hub_oauth import JUPYTERHUB_API_URL, AuthenticationRequired, get_token_from_request


class User(BaseModel):
    """
    Represents a user in the system.
    """

    username: str
    admin: bool = Field(default=False)
    groups: list[str] = Field(default_factory=list)


async def get_current_user(request: Request) -> dict | None:
    """Validate token against JupyterHub API and return the user model."""
    token = get_token_from_request(request)
    if not token:
        return None

    async with httpx.AsyncClient(
        base_url=JUPYTERHUB_API_URL, headers={"Authorization": f"token {token}"}
    ) as client:
        resp = await client.get(url="/user")
    if resp.status_code != 200:
        return None
    return resp.json()


async def require_authenticated_user(request: Request) -> User:
    """Dependency that requires authentication.

    Raises AuthenticationRequired if not logged in.
    """
    user_data = await get_current_user(request)
    if user_data is None:
        raise AuthenticationRequired(request)
    return User(
        username=user_data["name"],
        admin=user_data.get("admin", False),
        groups=user_data.get("groups", []),
    )
