import sys
from itertools import cycle
from time import sleep
from typing import Optional, Tuple
from urllib.parse import urljoin

import docker
import requests

spinner = cycle("|/-\\")


class KeycloakDriverException(Exception):
    pass


class KeycloakDriver(object):
    _container = None
    _log_lines = []
    _default_image = "quay.io/keycloak/keycloak"
    _default_tag = "12.0.1"
    _default_port = 8080
    _default_username = "admin"
    _default_password = "admin"
    _default_client_id = "test-client"
    _default_client_secret = "test-secret"
    _default_realm_name = "test"
    _default_environment = {
        "KEYCLOAK_USER": _default_username,
        "KEYCLOAK_PASSWORD": _default_password,
        "DB_VENDOR": "h2",
    }
    _test_line = "Http management interface listening on http://127.0.0.1:9990/management"
    _client_session = None
    port = None

    def __init__(self, port: int = None, realm_name: str = None, client_id: str = None, client_secret: str = None):
        if port:
            self.port = port
        if realm_name:
            self._default_realm_name = realm_name
        if client_id:
            self._default_client_id = client_id
        if client_secret:
            self._default_client_secret = client_secret

    def get_server_host_port(self) -> Tuple[Optional[str], Optional[int]]:
        if self._container and self.port:
            return "localhost", self.port
        return None, None

    def get_image(self) -> str:
        return self._default_image

    def get_tag(self) -> str:
        return self._default_tag

    def get_environment(self) -> dict:
        return self._default_environment

    def get_client_id(self) -> str:
        return self._default_client_id

    def get_client_secret(self) -> str:
        return self._default_client_secret

    def get_realm_name(self):
        return self._default_realm_name

    def _start_keycloak(self):
        client = docker.from_env()
        fimage = f"{self.get_image()}:{self.get_tag()}"
        c = client.containers.run(
            fimage,
            auto_remove=True,
            detach=True,
            ports={self._default_port: ("127.0.0.1", self.port)},
            environment=self.get_environment(),
        )
        self._container = client.containers.get(c.id)
        if not self.port:
            self.port = self._container.attrs["NetworkSettings"]["Ports"][f"{self._default_port}/tcp"][0]["HostPort"]
        # busy wait for keycloak to come up (timeout 60 seconds)
        for i in range(0, 120):
            if self._test_line in self._container.logs().decode("utf-8"):
                break
            else:
                sys.stdout.write(next(spinner))
                sys.stdout.flush()
                sleep(0.5)
                sys.stdout.write("\b")
        else:
            self._stop_keycloak()
            raise KeycloakDriverException("Timout starting Keycloak")

    def start(self) -> None:
        self._start_keycloak()

    def _stop_keycloak(self) -> None:
        if self._container:
            try:
                self._container.kill()
                self._container = None
            except Exception:
                # this container is potentially already stopped
                self._container = None

    def stop(self) -> None:
        self._stop_keycloak()

    def get_url(self) -> Optional[str]:
        if self.port:
            host, port = self.get_server_host_port()
            return f"http://{host}:{port}/"
        return None

    def _get_admin_session(self, username: str = None, password: str = None):
        if username is None:
            username = self._default_username
        if password is None:
            password = self._default_password

        if base_url := self.get_url():
            token_url = urljoin(base_url, "auth/realms/master/protocol/openid-connect/token")
            body_data = {"grant_type": "password", "client_id": "admin-cli", "username": username, "password": password}
            self._client_session = requests.session()
            # admin login seems to support only form-urlencoded media
            self._client_session.headers.update({"Content-Type": "application/x-www-form-urlencoded"})
            response = self._client_session.post(token_url, data=body_data, timeout=10)
            response.raise_for_status()
            token = response.json()["access_token"]
            self._client_session.headers.update({"Authorization": f"bearer {token}"})
            self._client_session.headers.update({"Content-Type": "application/json"})
            return self._client_session
        return None

    admin_client = property(_get_admin_session)

    def create_realm(self, name: str = None):
        if name is None:
            name = self.get_realm_name()
        if base_url := self.get_url():
            realm_url = urljoin(base_url, "auth/admin/realms")
            realm_body = {"realm": name, "enabled": True, "editUsernameAllowed": True}
            response = self.admin_client.post(realm_url, json=realm_body)
            return response
        else:
            raise KeycloakDriverException("Keycloak not yet started")

    def create_realm_client(self, realm_name: str = None, config: dict = None):
        """
        realm_name: the realm name to create this client in
        config: a dict holding a ClientRepresentation
            (see: https://www.keycloak.org/docs-api/5.0/rest-api/index.html#_clientrepresentation)
        """
        if realm_name is None:
            realm_name = self.get_realm_name()
        if base_url := self.get_url():
            client_url = urljoin(base_url, f"auth/admin/realms/{realm_name}/clients")
            if config is None:
                config = {
                    "clientId": self.get_client_id(),
                    "secret": self.get_client_secret(),
                    "redirectUris": ["*"],
                    "authorizationServicesEnabled": True,
                    "serviceAccountsEnabled": True,
                    "authorizationSettings": {},
                }
            response = self.admin_client.post(client_url, json=config)
            # update service account user
            sau_url = urljoin(
                base_url, f"auth/admin/realms/{realm_name}/users?username=service-account-{self.get_client_id()}"
            )
            t_res = self.admin_client.get(sau_url)
            t_res.raise_for_status()
            sau = t_res.json()[0]
            realm_mgmt_url = urljoin(base_url, f"auth/admin/realms/{realm_name}/clients?clientId=realm-management")
            r_res = self.admin_client.get(realm_mgmt_url)
            r_res.raise_for_status()
            realm_mgmt = r_res.json()[0]
            # get role id
            roles_id_url = urljoin(
                base_url, f"auth/admin/realms/{realm_name}/" f"clients/{realm_mgmt['id']}/roles?search=realm-admin"
            )

            roles_res = self.admin_client.get(roles_id_url)
            roles_res.raise_for_status()
            sau_rolemappings = roles_res.json()
            sau_mappings_url = urljoin(
                base_url,
                f"auth/admin/realms/{realm_name}/users/{sau['id']}" f"/role-mappings/clients/{realm_mgmt['id']}",
            )
            self.admin_client.post(sau_mappings_url, json=sau_rolemappings)
            return response
        else:
            raise KeycloakDriverException("Keycloak not yet started")
