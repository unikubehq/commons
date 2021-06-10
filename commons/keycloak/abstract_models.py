import uuid
from typing import List, Optional

try:
    from django.contrib.postgres.fields import JSONField
except ModuleNotFoundError:
    # use django_extensions' JSONField as a fallback
    from django_extensions.db.fields.json import JSONField

from django.db import models
from keycloak.exceptions import KeycloakClientError
from requests import HTTPError

from commons.keycloak.groups import GroupHandler
from commons.keycloak.resources import ResourceHandler


class KeycloakResource(models.Model):
    _default_kc_data = {"groups": {}}
    ADMINS = "admins"
    MEMBERS = "members"
    resource_handler = ResourceHandler

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    keycloak_data = JSONField(default=_default_kc_data)

    class Meta:
        abstract = True

    def create_keycloak_resource(self) -> None:
        rh = self._get_resource_handler()
        try:
            rh.get(str(self.id))
        except KeycloakClientError:
            rh.create(self._meta.model_name, str(self.pk), self.get_keycloak_name())
            # if this resource is new, create groups too
            self.create_keycloak_groups()

    def get_keycloak_resource(self) -> dict:
        rh = self._get_resource_handler()
        return rh.get(str(self.id))

    def delete_keycloak_resource(self, obj_id: uuid.UUID) -> None:
        rh = self._get_resource_handler()
        try:
            rh.delete(str(obj_id))
        except HTTPError as e:
            # if this resource was deleted already move on
            if e.response.status_code != 404:
                raise e
        # delete related kc groups too
        gh = GroupHandler()
        for _, group_id in self.keycloak_data["groups"].items():
            try:
                gh.delete(group_id)
            except HTTPError as e:
                # if this group was deleted already move on
                if e.response.status_code != 404:
                    raise e

    def get_keycloak_name(self) -> Optional[str]:
        """This return value must be unique for this content type"""
        return str(self.pk)

    def delete(self, *args, **kwargs):
        # since we lose self.pk after deletion, we must temporary keep it
        _del_id = self.pk
        super(KeycloakResource, self).delete(*args, **kwargs)
        if not kwargs.pop("kc_ignore", False):
            self.delete_keycloak_resource(_del_id)

    def save(self, *args, **kwargs):
        super(KeycloakResource, self).save(*args, **kwargs)
        if not kwargs.pop("kc_ignore", False):
            self.create_keycloak_resource()

    def create_keycloak_groups(self, associate_perms=True):
        gh = GroupHandler()
        # admin group
        admin_group_id = gh.create(f"{self._meta.model_name}-{self.get_keycloak_name()}-{self.ADMINS}")
        # member group
        member_group_id = gh.create(f"{self._meta.model_name}-{self.get_keycloak_name()}")
        self.keycloak_data["groups"] = {self.ADMINS: admin_group_id, self.MEMBERS: member_group_id}
        self.save(update_fields=("keycloak_data",))
        if associate_perms:
            # add admin permissions to admin group
            self.associate_permission(
                f"Edit {self._meta.model_name} {self.get_keycloak_name()}",
                scopes=[self.resource_handler.EDIT, self.resource_handler.VIEW],
                group_ids=[self.get_group_id(self.ADMINS)],
            )
            # add member permission to member group
            self.associate_permission(
                f"View {self._meta.model_name} {self.get_keycloak_name()}",
                scopes=[self.resource_handler.VIEW],
                group_ids=[self.get_group_id(self.MEMBERS)],
            )

    def associate_permission(
        self,
        name: str,
        scopes: List[str],
        group_ids: List[uuid.UUID],
        logic: str = "POSITIVE",
        decision_strategy: str = "UNANIMOUS",
    ) -> dict:
        rh = self._get_resource_handler()
        gh = GroupHandler()
        data = rh.associate_permission(
            str(self.id),
            name,
            scopes=[rh._scope(self._meta.model_name, scope) for scope in scopes],
            groups=[gh.get(str(group))["path"] for group in group_ids],
            logic=logic,
            decision_strategy=decision_strategy,
        )
        return data

    def get_group_id(self, name: str) -> Optional[uuid.UUID]:
        if self.keycloak_data and "groups" in self.keycloak_data:
            return self.keycloak_data["groups"].get(name, None)
        return None

    def _get_resource_handler(self):
        return self.resource_handler()
