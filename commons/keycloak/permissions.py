import fnmatch
import uuid
from functools import lru_cache
from typing import KeysView, List, Union


class KeycloakPermissions:
    def __init__(self, permission_data: List[dict]):
        self._kc_permission_data = permission_data
        self.permission_data = self._convert_resource(permission_data)

    @lru_cache(10)
    def get_resources_by_scope(self, scope: str) -> dict:
        """
        Return a list of resources with the given scope. Supports to filter with wildcards
        e.g. organization:*.
        """
        results = {}
        for _uuid, resource in self.permission_data.items():
            if "scopes" in resource:
                # 'scopes': ['organization:view', 'organization:edit']
                scopes = resource["scopes"]
                matched = fnmatch.filter(scopes, scope)
                if matched:
                    results[_uuid] = resource
        return results

    @lru_cache(10)
    def get_resource_id_by_scope(self, scope: str) -> KeysView[str]:
        """
        Return a list of resource ids with the given scope. Supports to filter with wildcards
        e.g. organization:*.
        """
        res_objs = self.get_resources_by_scope(scope)
        return res_objs.keys()

    def has_permission(self, resource: Union[List[str], str], scope: str = None) -> bool:
        """
        Returns True of False if the given scope (or any scope if no scope provided) is applicable
        for the requested resources.
        """
        if isinstance(resource, str):
            _uuid = frozenset([resource])
        else:
            _uuid = frozenset(resource)
        return self._has_permission(_uuid, scope)

    @lru_cache(10)
    def _has_permission(self, _uuid: set, scope: str = None):
        if scope:
            resources = self.get_resources_by_scope(scope)
        else:
            resources = self.permission_data
        return set(_uuid).issubset(resources.keys())

    def _convert_resource(self, raw_data: List[dict]) -> dict:
        results = {}
        for resource in raw_data:
            rsid = resource.pop("rsid")
            rsname = resource.pop("rsname")
            resource["id"] = str(uuid.UUID(rsid))
            resource["name"] = rsname
            results[str(uuid.UUID(rsid))] = resource
        return results
