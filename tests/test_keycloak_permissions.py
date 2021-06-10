import copy
from typing import Iterable
from unittest import TestCase

from commons.keycloak.permissions import KeycloakPermissions

RESOURCE1 = {
    "scopes": ["organization:view", "organization:edit"],
    "rsid": "ab0fcb95-e3af-4960-a4cb-1b949f76a81b".upper(),
    "rsname": "organization redshoe",
}
RESOURCE2 = {
    "scopes": ["organization:view", "organization:edit"],
    "rsid": "2ef0261b42e8454fbd9140d3445dbbef".upper(),
    "rsname": "organization blueshoe",
}
RESOURCE3 = {"scopes": [], "rsid": "111a4bbd109d4f1c94b92231a4e638a1", "rsname": "organization greenshoe"}
RESOURCE4 = {
    "scopes": ["organization:edit"],
    "rsid": "411cfeed-bbf9-49bd-a642-80ab4eef3384",
    "rsname": "organization magentashoe",
}
RESOURCE5 = {
    "scopes": ["organization:view", "organization:edit", "organization:members:add"],
    "rsid": "2f053a88-5379-4e7d-881c-a7d1cc1054c9",
    "rsname": "organization purpleshoe",
}
RESOURCE6 = {
    "scopes": ["project:view", "project:edit", "project:members:add"],
    "rsid": "265a06d4-8b48-4d98-8cdd-d57a823b2398",
    "rsname": "project unikube",
}
RESOURCE7 = {"scopes": ["project:view"], "rsid": "8258fa5e-3f70-4763-87b2-eb1e2da1cd78", "rsname": "project metakube"}


class KeycloakPermissionTest(TestCase):
    def test_get_resources_by_scope(self):
        permission_set = copy.deepcopy([RESOURCE1, RESOURCE2, RESOURCE3, RESOURCE4, RESOURCE6])
        permissions = KeycloakPermissions(permission_set)
        res = permissions.get_resources_by_scope("organization:view")
        self.assertEqual(len(res.keys()), 2)
        self.assertIn("ab0fcb95-e3af-4960-a4cb-1b949f76a81b", res.keys())
        self.assertIn("2ef0261b-42e8-454f-bd91-40d3445dbbef", res.keys())
        res = permissions.get_resources_by_scope("organization:*")
        self.assertIsInstance(res, dict)
        self.assertEqual(len(res.keys()), 3)
        self.assertIn("ab0fcb95-e3af-4960-a4cb-1b949f76a81b", res.keys())
        self.assertIn("2ef0261b-42e8-454f-bd91-40d3445dbbef", res.keys())
        self.assertIn("411cfeed-bbf9-49bd-a642-80ab4eef3384", res.keys())
        res = permissions.get_resources_by_scope("*")
        self.assertIsInstance(res, dict)
        self.assertEqual(len(res.keys()), 4)
        self.assertIn("ab0fcb95-e3af-4960-a4cb-1b949f76a81b", res.keys())
        self.assertIn("2ef0261b-42e8-454f-bd91-40d3445dbbef", res.keys())
        self.assertIn("411cfeed-bbf9-49bd-a642-80ab4eef3384", res.keys())
        self.assertIn("265a06d4-8b48-4d98-8cdd-d57a823b2398", res.keys())
        res = permissions.get_resources_by_scope("project:view")
        self.assertEqual(len(res.keys()), 1)
        self.assertIn("265a06d4-8b48-4d98-8cdd-d57a823b2398", res.keys())
        res = permissions.get_resources_by_scope("doesnotexist")
        self.assertEqual(len(res.keys()), 0)
        # we don't support empty scopes here, see RESOURCE3
        res = permissions.get_resources_by_scope("")
        self.assertEqual(len(res.keys()), 0)

    def test_get_resources_id_by_scope(self):
        permission_set = copy.deepcopy([RESOURCE5, RESOURCE4, RESOURCE6])
        permissions = KeycloakPermissions(permission_set)
        res = permissions.get_resource_id_by_scope("organization:members:add")
        self.assertIsInstance(res, Iterable)
        self.assertEqual(len(res), 1)
        self.assertIn("2f053a88-5379-4e7d-881c-a7d1cc1054c9", res)
        res = permissions.get_resource_id_by_scope("organization:edit")
        self.assertIsInstance(res, Iterable)
        self.assertEqual(len(res), 2)
        self.assertIn("2f053a88-5379-4e7d-881c-a7d1cc1054c9", res)
        self.assertIn("411cfeed-bbf9-49bd-a642-80ab4eef3384", res)

    def test_has_permission(self):
        permission_set = copy.deepcopy([RESOURCE1, RESOURCE3, RESOURCE5, RESOURCE4, RESOURCE7])
        permissions = KeycloakPermissions(permission_set)
        # RESOURCE2 not in permission_set
        self.assertFalse(permissions.has_permission("2ef0261b-42e8-454f-bd91-40d3445dbbef"))
        # RESOURCE5
        self.assertTrue(permissions.has_permission("2f053a88-5379-4e7d-881c-a7d1cc1054c9"))
        self.assertTrue(permissions.has_permission("2f053a88-5379-4e7d-881c-a7d1cc1054c9", "organization:view"))
        self.assertTrue(permissions.has_permission("2f053a88-5379-4e7d-881c-a7d1cc1054c9", "organization:edit"))
        self.assertTrue(permissions.has_permission("2f053a88-5379-4e7d-881c-a7d1cc1054c9", "organization:*"))
        self.assertTrue(permissions.has_permission("2f053a88-5379-4e7d-881c-a7d1cc1054c9", "*:*"))
        self.assertTrue(permissions.has_permission("2f053a88-5379-4e7d-881c-a7d1cc1054c9", "*"))
        self.assertFalse(permissions.has_permission("2f053a88-5379-4e7d-881c-a7d1cc1054c9", "organization:member:add"))
        # RESOURCE3
        # this is true, although there is no scope for this permission
        self.assertTrue(permissions.has_permission("111a4bbd-109d-4f1c-94b9-2231a4e638a1"))
        # this is different, "any" scope for RESOURCE3 has no permission
        self.assertFalse(permissions.has_permission("111a4bbd-109d-4f1c-94b9-2231a4e638a1", "*"))
        # RESOUCE7, RESOURCE4
        self.assertTrue(
            permissions.has_permission(
                ["8258fa5e-3f70-4763-87b2-eb1e2da1cd78", "411cfeed-bbf9-49bd-a642-80ab4eef3384"], "*"
            )
        )
        self.assertFalse(
            permissions.has_permission(
                ["8258fa5e-3f70-4763-87b2-eb1e2da1cd78", "411cfeed-bbf9-49bd-a642-80ab4eef3384"], "project:*"
            )
        )
        # RESOUCE1, RESOURCE5
        self.assertTrue(
            permissions.has_permission(
                ["ab0fcb95-e3af-4960-a4cb-1b949f76a81b", "2f053a88-5379-4e7d-881c-a7d1cc1054c9"], "*"
            )
        )
        self.assertTrue(
            permissions.has_permission(
                ["ab0fcb95-e3af-4960-a4cb-1b949f76a81b", "2f053a88-5379-4e7d-881c-a7d1cc1054c9"], "organization:*"
            )
        )
        self.assertTrue(
            permissions.has_permission(
                ["ab0fcb95-e3af-4960-a4cb-1b949f76a81b", "2f053a88-5379-4e7d-881c-a7d1cc1054c9"], "organization:view"
            )
        )
        self.assertFalse(
            permissions.has_permission(
                ["ab0fcb95-e3af-4960-a4cb-1b949f76a81b", "2f053a88-5379-4e7d-881c-a7d1cc1054c9"],
                "organization:members:add",
            )
        )
