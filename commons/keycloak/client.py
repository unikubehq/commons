from functools import lru_cache
from typing import Callable, Optional, Union
from urllib.parse import urljoin

from keycloak.admin import KeycloakAdmin
from keycloak.authz import KeycloakAuthz
from keycloak.openid_connect import KeycloakOpenidConnect
from keycloak.realm import KeycloakRealm
from keycloak.uma import KeycloakUMA

from commons.keycloak.conf import config


@lru_cache(1)
def get_realm():
    return KeycloakRealm(server_url=config.SERVER_URL, realm_name=config.REALM_NAME)


def get_oidc_client() -> KeycloakOpenidConnect:
    realm = get_realm()
    return realm.open_id_connect(client_id=config.CLIENT_ID, client_secret=config.CLIENT_SECRET)


@lru_cache(1)
def get_uma_client() -> KeycloakUMA:
    realm = get_realm()
    uma_client = realm.uma()
    # patch uma client urls as Keycloak does not properly return then
    _well_know = uma_client.well_known.contents
    _well_know["resource_registration_endpoint"] = urljoin(
        config.SERVER_URL, _well_know["resource_registration_endpoint"].split("/", 3)[-1]
    )
    _well_know["policy_endpoint"] = urljoin(config.SERVER_URL, _well_know["policy_endpoint"].split("/", 3)[-1])
    _well_know["permission_endpoint"] = urljoin(config.SERVER_URL, _well_know["permission_endpoint"].split("/", 3)[-1])
    return uma_client


@lru_cache(1)
def get_authz_client() -> KeycloakAuthz:
    realm = get_realm()
    return realm.authz(client_id=config.CLIENT_ID)


def admin_token_getter() -> str:
    return get_oidc_client().client_credentials()["access_token"]


def get_admin(token: Optional[Union[Callable[[], str], str]] = None) -> KeycloakAdmin:
    """
    :param token: Can be provided to avoid extra api call to obtain a client token
    :return:
    """
    if token is None:
        token = admin_token_getter
    if callable(token):
        token = token()
    realm = get_realm()
    admin = realm.admin
    admin.set_token(token)
    return admin
