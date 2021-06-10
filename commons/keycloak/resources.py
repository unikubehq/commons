from typing import List, Optional

from keycloak.uma import KeycloakUMA

from commons.keycloak.client import admin_token_getter, get_uma_client


class ResourceHandler:
    VIEW = "view"
    EDIT = "edit"
    SCOPE_SEP = ":"

    KIND = "kind"
    KIND_SEP = ":"

    def __init__(self, token: Optional[str] = None):
        self.uma_client: KeycloakUMA = get_uma_client()
        if token is None:
            self.token = admin_token_getter()

    def _kind(self, content_type: str) -> str:
        return f"{self.KIND}{self.SCOPE_SEP}{content_type.lower()}"

    def _scope(self, content_type: str, verb: str) -> str:
        return f"{content_type.lower()}{self.SCOPE_SEP}{verb}"

    def create(self, content_type: str, object_uuid: str, name: Optional[str] = None) -> str:
        ct = content_type.lower()
        name = f"{ct} {name or object_uuid}"
        self.uma_client.resource_set_create(
            self.token,
            _id=object_uuid,
            name=name,
            type=self._kind(content_type),
            scopes=self.get_available_scopes(content_type),
            ownerManagedAccess="true",
        )
        return object_uuid

    def get_available_scopes(self, content_type: str) -> List[str]:
        """
        Return a list of available scopes for this resource to be created.
        """
        return [self._scope(content_type, self.EDIT), self._scope(content_type, self.VIEW)]

    def get(self, resource_id: str) -> dict:
        data = self.uma_client.resource_set_read(self.token, resource_id)
        return data

    def delete(self, resource_id: str) -> int:
        data = self.uma_client.resource_set_delete(self.token, resource_id)
        return data.status_code

    def associate_permission(
        self,
        resource_id: str,
        name: str,
        scopes: List[str],
        groups: List[str],
        logic: str = "POSITIVE",
        decision_strategy: str = "UNANIMOUS",
    ) -> dict:
        data = self.uma_client.resource_associate_permission(
            self.token,
            resource_id,
            name=name,
            scopes=scopes,
            groups=groups,
            logic=logic,
            decisionStrategy=decision_strategy,
        )
        return data
