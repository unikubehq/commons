import re
from typing import Dict, Optional, Union

from requests import Response

from commons.keycloak.client import get_admin, get_realm

UUID = re.compile(r"\b[0-9a-f]{8}\b-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-\b[0-9a-f]{12}\b")


class KCAdminHandler:

    base_path = None

    def __init__(self, token: Optional[str] = None):
        self.realm = get_realm()
        self.admin = get_admin(token=token)

    def _call_api(
        self, url, method="get", params=None, data=None, json=None, headers=None
    ) -> Dict[str, Union[Dict, int]]:
        handler = getattr(self.realm.client.session, method)
        response: Response = handler(
            url, headers=self._add_auth_header(headers=headers), params=params, data=data, json=json
        )
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError:
            data = response.content
        return {
            "data": data,
            "headers": response.headers,
            "status_code": response.status_code,
        }

    def _add_auth_header(self, headers=None):
        t = self.admin._token
        if callable(t):
            t = t()
        headers = headers or {}
        headers["Authorization"] = "Bearer {}".format(t)
        headers["Content-Type"] = "application/json"
        return headers

    def get(self, _id: str) -> dict:
        url = f"{self.admin.get_full_url(self.base_path)}{_id}"
        return self._call_api(url)["data"]

    def delete(self, _id: str) -> int:
        url = f"{self.admin.get_full_url(self.base_path)}{_id}"
        return self._call_api(url, method="delete")["status_code"]
