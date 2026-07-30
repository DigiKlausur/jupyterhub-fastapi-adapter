
# jupyterhub-fastapi-adapter

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![PyPI Version](https://img.shields.io/pypi/v/jupyterhub-fastapi-adapter.svg)](https://pypi.org/project/jupyterhub-fastapi-adapter/)

A lightweight adapter for building authenticated **FastAPI** services that run behind **JupyterHub**.

The package provides:

* OAuth authentication using JupyterHub's service OAuth flow
* FastAPI dependencies for accessing the authenticated user
* Automatic browser redirects to the JupyterHub login page
* Health-check friendly authentication handling
* Cookie- and token-based authentication support

## Features

* ✅ OAuth login flow for browser-based services
* ✅ `require_authenticated_user` FastAPI dependency
* ✅ `User` model with username, admin status, and groups
* ✅ Authentication exception and exception handler
* ✅ Supports both OAuth cookies and `Authorization` headers


---

## Installation

```bash
pip install jupyterhub-fastapi-adapter
```

---

## Requirements

The service must run as a **JupyterHub Service** and the following environment variables must be available:

| Variable                    | Description                           |
| --------------------------- | ------------------------------------- |
| `JUPYTERHUB_API_URL`        | URL of the JupyterHub API             |
| `JUPYTERHUB_API_TOKEN`      | Service API token                     |
| `JUPYTERHUB_SERVICE_PREFIX` | Service prefix assigned by JupyterHub |

---

## Basic Usage

Create a FastAPI application:

```python
"""
Minimal FastAPI JupyterHub managed service.
Shows the authenticated user's information as JSON.

Uses jupyterhub.services.auth.HubOAuth to identify the logged-in user
from JupyterHub's OAuth cookie.
"""

import os

from fastapi import Depends, FastAPI
from jupyterhub.utils import url_path_join
from jupyterhub_fastapi_adapter import (
    AuthenticationRequired,
    User,
    authentication_required_handler,
    oauth_callback,
    require_authenticated_user,
)

JUPYTERHUB_SERVICE_PREFIX = os.environ["JUPYTERHUB_SERVICE_PREFIX"]

app = FastAPI()

# Register exception handler
app.exception_handler(AuthenticationRequired)(authentication_required_handler)

# Register OAuth callback route
app.get(url_path_join(JUPYTERHUB_SERVICE_PREFIX, "oauth_callback"))(oauth_callback)


@app.get(JUPYTERHUB_SERVICE_PREFIX)
async def index(user: User = Depends(require_authenticated_user)):
    """Return authenticated user information."""
    return user


@app.get(url_path_join(JUPYTERHUB_SERVICE_PREFIX, "hello"))
async def hello(user: User = Depends(require_authenticated_user)):
    return {"message": f"Hello, {user.username}!"}
```

When an unauthenticated browser visits the service, they are automatically redirected to the JupyterHub OAuth login flow.

After successful authentication, JupyterHub redirects the user back to the service and authentication is handled using an OAuth cookie.

---

## Authentication Dependency

Use the provided dependency to require authentication:

```python
from fastapi import Depends

from jupyterhub_fastapi_adapter.dependencies import require_authenticated_user


@app.get("/protected")
async def protected(user=Depends(require_authenticated_user)):
    return {"hello": user.username}
```

The dependency returns a `User` object:

```python
class User(BaseModel):
    username: str
    admin: bool
    groups: list[str]
```

---

## OAuth Flow

The package implements the standard JupyterHub service OAuth flow:

1. A user accesses a protected endpoint.
2. If no valid authentication is present, `AuthenticationRequired` is raised.
3. The exception handler redirects the browser to JupyterHub's OAuth endpoint.
4. JupyterHub authenticates the user.
5. The OAuth callback exchanges the authorization code for an access token.
6. The access token is stored in a cookie.
7. Future requests authenticate using that cookie.

For API clients, bearer tokens supplied via the `Authorization` header are also supported.

---

## Health Checks

Requests that do not advertise `Accept: text/html` receive a simple `200 OK` response instead of an OAuth redirect when authentication is required.

This allows JupyterHub and other infrastructure to perform health checks without triggering the login flow.

---

## API

### `hub_oauth`

* `AuthenticationRequired`
* `authentication_required_handler()`
* `oauth_callback()`
* `get_token_from_request()`

### `dependencies`

* `require_authenticated_user()`
* `get_current_user()`
* `User`

---

## License

MIT
