import os

# hub_oauth.py reads these at import time, so set them before the package is imported.
os.environ.setdefault("JUPYTERHUB_API_URL", "http://hub.test/hub/api")
os.environ.setdefault("JUPYTERHUB_API_TOKEN", "service-token")
os.environ.setdefault("JUPYTERHUB_SERVICE_PREFIX", "/services/testservice/")
os.environ.setdefault("JUPYTERHUB_SERVICE_NAME", "testservice")
