from commons.keycloak.conf import config
from commons.keycloak.handler import UUID, KCAdminHandler


class GroupHandler(KCAdminHandler):
    base_path = f"auth/admin/realms/{config.REALM_NAME}/groups/"

    def create(self, name: str) -> str:
        url = f"{self.admin.get_full_url(self.base_path)}"
        response_data = self._call_api(url, method="post", json={"name": name})
        return UUID.search(response_data["headers"]["location"]).group(0)

    def members(self, group_id: str):
        url = f"{self.admin.get_full_url(self.base_path)}{group_id}/members"
        return self._call_api(url)["data"]
