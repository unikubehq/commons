from commons.keycloak.conf import config
from commons.keycloak.handler import UUID, KCAdminHandler


class UserHandler(KCAdminHandler):
    base_path = f"auth/admin/realms/{config.REALM_NAME}/users/"

    def join_group(self, user_id: str, group_id: str):
        url = f"{self.admin.get_full_url(self.base_path)}{user_id}/groups/{group_id}"
        return self._call_api(url, method="put")["status_code"]

    def leave_group(self, user_id: str, group_id: str):
        url = f"{self.admin.get_full_url(self.base_path)}{user_id}/groups/{group_id}"
        return self._call_api(url, method="delete")["status_code"]

    def count_groups(self, user_id: str) -> int:
        url = f"{self.admin.get_full_url(self.base_path)}{user_id}/groups/count"
        return self._call_api(url)["data"]["count"]

    def groups(self, user_id: str):
        url = f"{self.admin.get_full_url(self.base_path)}{user_id}/groups"
        return self._call_api(url)["data"]

    def create(self, data: dict) -> str:
        url = f"{self.admin.get_full_url(self.base_path)}"
        response_data = self._call_api(url, method="post", json=data)
        return UUID.search(response_data["headers"]["location"]).group(0)

    def update(self, user_id: str, data: dict) -> dict:
        """
        A "username" update is silently ignored by the API if the keycloak realm does not permit username updates.
        """
        url = f"{self.admin.get_full_url(self.base_path)}{user_id}"
        response_data = self._call_api(url, method="put", json=data)
        return response_data["status_code"]
