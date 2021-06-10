from typing import Optional

from django.db import models

from commons.keycloak.abstract_models import KeycloakResource


class TestResource(KeycloakResource):
    pass


class AnotherTestResource(KeycloakResource):

    title = models.CharField(max_length=10)

    def get_keycloak_name(self) -> Optional[str]:
        return self.title
