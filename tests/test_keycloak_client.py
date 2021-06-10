import uuid

from django.test import SimpleTestCase
from keycloak.exceptions import KeycloakClientError
from requests import HTTPError

from commons.keycloak.conf import configure
from commons.keycloak.groups import GroupHandler
from commons.keycloak.resources import ResourceHandler
from commons.keycloak.testing.driver import KeycloakDriver
from commons.keycloak.users import UserHandler
from tests.testapp.models import AnotherTestResource, TestResource


class KeycloakClientTests(SimpleTestCase):
    driver: KeycloakDriver = None
    group_id: str = None
    resource_id1: str = None
    resource_id2: str = None
    resource_name: str = None
    testresource1: str = None
    testresource2: str = None
    organization_contenttype = "organization"

    @classmethod
    def setUpClass(cls):
        realm_name = "unikube"
        client_id = "test"
        client_secret = "test"
        cls.resource_id1 = str(uuid.uuid4())
        cls.resource_id2 = str(uuid.uuid4())
        cls.resource_name = "testshoe"

        cls.driver = KeycloakDriver(9999, realm_name=realm_name, client_id=client_id, client_secret=client_secret)
        cls.driver.start()
        host, port = cls.driver.get_server_host_port()
        configure(
            scheme="http", host=host, port=port, realm_name=realm_name, client_id=client_id, client_secret=client_secret
        )
        cls.driver.create_realm()
        cls.driver.create_realm_client()

    def test_a_create_group(self):
        gh = GroupHandler()
        self.__class__.group_id = gh.create("testgroup")

    def test_b_inspect_group(self):
        gh = GroupHandler()
        group = gh.get(self.__class__.group_id)
        self.assertEqual(group["name"], "testgroup")

    def test_c_delete_group(self):
        gh = GroupHandler()
        status = gh.delete(self.__class__.group_id)
        self.assertEqual(status, 204)

    def test_d1_create_user(self):
        uh = UserHandler()
        self.__class__.user_id = uh.create({"username": "testface", "email": "test@blueshoe.de"})

    def test_d2_inspect_user(self):
        uh = UserHandler()
        user = uh.get(self.__class__.user_id)
        self.assertEqual(user["email"], "test@blueshoe.de")
        self.assertEqual(user["username"], "testface")

    def test_d3_join_and_leave_group(self):
        uh = UserHandler()
        gh = GroupHandler()
        group_id = gh.create("project_group")
        status = uh.join_group(self.__class__.user_id, group_id)
        self.assertEqual(status, 204)
        user_groups = uh.groups(self.__class__.user_id)
        self.assertIs(uh.count_groups(self.__class__.user_id), 1)
        self.assertIs(len(user_groups), 1)
        self.assertEqual(user_groups[0]["name"], "project_group")
        self.assertEqual(user_groups[0]["id"], group_id)
        members = gh.members(group_id)
        self.assertIs(len(members), 1)
        self.assertEqual(members[0]["email"], "test@blueshoe.de")
        self.assertEqual(members[0]["id"], self.__class__.user_id)
        status = uh.leave_group(self.__class__.user_id, group_id)
        self.assertEqual(status, 204)
        self.assertIs(uh.count_groups(self.__class__.user_id), 0)

    def test_d4_delete_user(self):
        uh = UserHandler()
        status = uh.delete(self.__class__.user_id)
        self.assertEqual(status, 204)

    def test_e1_create_resource_with_name(self):
        rh = ResourceHandler()
        rh.create(self.organization_contenttype, object_uuid=self.resource_id1, name=self.resource_name)

    def test_e2_create_resource_without_name(self):
        rh = ResourceHandler()
        rh.create(self.organization_contenttype, object_uuid=self.resource_id2)

    def test_f1_inspect_resource_with_name(self):
        rh = ResourceHandler()
        resource = rh.get(self.__class__.resource_id1)
        self.assertEqual(resource["type"], "kind:" + self.organization_contenttype)
        self.assertEqual(resource["name"], f"{self.organization_contenttype} {self.resource_name}")

    def test_f2_inspect_resource_with_name(self):
        rh = ResourceHandler()
        resource = rh.get(self.__class__.resource_id2)
        self.assertEqual(resource["type"], "kind:" + self.organization_contenttype)
        self.assertEqual(resource["name"], f"{self.organization_contenttype} {self.resource_id2}")

    def test_g1_delete_resource(self):
        rh = ResourceHandler()
        status = rh.delete(self.__class__.resource_id1)
        self.assertEqual(status, 204)

    def test_g2_delete_resource(self):
        rh = ResourceHandler()
        status = rh.delete(self.__class__.resource_id2)
        self.assertEqual(status, 204)

    def test_h1_create_model_resource(self):
        tr = TestResource.objects.create()
        self.__class__.testresource1 = tr.id

    def test_h2_create_model_resource(self):
        atr = AnotherTestResource.objects.create(title="test")
        self.__class__.testresource2 = atr.id

    def test_h3_inspect_model_resources(self):
        atr = AnotherTestResource.objects.get(id=self.__class__.testresource2)
        tr = TestResource.objects.get(id=self.__class__.testresource1)
        rh = ResourceHandler()
        atr_resource = rh.get(str(atr.id))
        tr_resource = rh.get(str(tr.id))
        self.assertEqual(atr_resource["name"], "anothertestresource test")
        self.assertEqual(tr_resource["name"], f"testresource {tr.pk}")

    def test_h4_inspect_model_resource(self):
        atr = AnotherTestResource.objects.get(id=self.__class__.testresource2)
        tr = TestResource.objects.get(id=self.__class__.testresource1)
        self.assertEqual(len(atr.keycloak_data["groups"].keys()), 2)
        self.assertEqual(len(tr.keycloak_data["groups"].keys()), 2)
        gh = GroupHandler()
        atr_admin_group = gh.get(atr.keycloak_data["groups"]["admins"])
        atr_member_group = gh.get(atr.keycloak_data["groups"]["members"])
        tr_admin_group = gh.get(tr.keycloak_data["groups"]["admins"])
        tr_member_group = gh.get(tr.keycloak_data["groups"]["members"])
        self.assertEqual(atr_admin_group["name"], "anothertestresource-test-admins")
        self.assertEqual(atr_member_group["name"], "anothertestresource-test")
        self.assertEqual(tr_admin_group["name"], f"testresource-{tr.pk}-admins")
        self.assertEqual(tr_member_group["name"], f"testresource-{tr.pk}")

    def test_i_delete_model_resource(self):
        atr = AnotherTestResource.objects.get(id=self.__class__.testresource2)
        tr = TestResource.objects.get(id=self.__class__.testresource1)
        atr_data = atr.keycloak_data
        atr_id = atr.pk
        tr_data = tr.keycloak_data
        tr_id = tr.pk
        atr.delete()
        tr.delete()
        gh = GroupHandler()
        rh = ResourceHandler()
        self.assertRaises(HTTPError, gh.get, atr_data["groups"]["admins"])
        self.assertRaises(HTTPError, gh.get, atr_data["groups"]["members"])
        self.assertRaises(HTTPError, gh.get, tr_data["groups"]["admins"])
        self.assertRaises(HTTPError, gh.get, tr_data["groups"]["members"])
        self.assertRaises(KeycloakClientError, rh.get, atr_id)
        self.assertRaises(KeycloakClientError, rh.get, tr_id)

    def test_k_associate_permissions(self):
        atr: AnotherTestResource = AnotherTestResource.objects.create(title="another test")
        rh = ResourceHandler()
        # this does not fail though we created these permissions in all tests above
        atr.associate_permission(
            f"Edit AnotherTestResource {atr.title}",
            scopes=[rh.EDIT, rh.VIEW],
            group_ids=[atr.get_group_id(AnotherTestResource.ADMINS)],
        )
        atr.associate_permission(
            f"View AnotherTestResource {atr.title}",
            scopes=[rh.VIEW],
            group_ids=[atr.get_group_id(AnotherTestResource.MEMBERS)],
        )

    @classmethod
    def tearDownClass(cls):
        cls.driver.stop()
