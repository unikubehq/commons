import os
from operator import attrgetter, itemgetter

from django.conf import settings

DEFAULTS = {
    "KEYCLOAK_REALM_NAME": "unikube",
    "KEYCLOAK_PORT": 8080,
    "KEYCLOAK_SCHEME": "https",
}


def _resolve(namespace, name, default):
    for resolver in (attrgetter, itemgetter):
        try:
            return resolver(name)(namespace)
        except (TypeError, AttributeError, KeyError):
            pass
    return default


class KeycloakConfig:
    unset = object()

    def __init__(self, **overrides):
        self.overrides = {k: v for k, v in overrides.items() if v is not None}
        scheme = self._resolve("KEYCLOAK_SCHEME")
        host = self._resolve("KEYCLOAK_HOST")
        port = self._resolve("KEYCLOAK_PORT")
        self.SERVER_URL = f"{scheme}://{host}:{port}"
        self.REALM_NAME = self._resolve("KEYCLOAK_REALM_NAME")
        self.CLIENT_ID = self._resolve("KEYCLOAK_CLIENT_ID")
        self.CLIENT_SECRET = self._resolve("KEYCLOAK_CLIENT_SECRET")

    def _resolve(self, name):
        unset = object()
        for namespace in (self.overrides, settings, os.environ, DEFAULTS):
            value = _resolve(namespace, name, unset)
            if value is not unset:
                return value


config = KeycloakConfig()


def configure(scheme=None, host=None, port=None, realm_name=None, client_id=None, client_secret=None):
    global config
    _override = KeycloakConfig(
        KEYCLOAK_SCHEME=scheme,
        KEYCLOAK_HOST=host,
        KEYCLOAK_PORT=port,
        KEYCLOAK_REALM_NAME=realm_name,
        KEYCLOAK_CLIENT_ID=client_id,
        KEYCLOAK_CLIENT_SECRET=client_secret,
    )
    config.SERVER_URL = _override.SERVER_URL
    config.REALM_NAME = _override.REALM_NAME
    config.CLIENT_ID = _override.CLIENT_ID
    config.CLIENT_SECRET = _override.CLIENT_SECRET
