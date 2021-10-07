from unittest import TestCase

import requests
import yaml

from commons.helm import utils
from commons.helm.data_classes import DeckData, RenderEnvironment
from commons.helm.parser import HelmRepositoryParser

GIT_REPO_URL = "https://github.com/Blueshoe/buzzword-charts.git"
deck_data_check = [
    {"title": "buzzword-counter"},
]


class HelmRepositoryParserTests(TestCase):
    def test_parse(self):
        parser = HelmRepositoryParser(GIT_REPO_URL)
        parser.parse()
        self.assertEqual(len(parser.deck_data), len(deck_data_check))
        for i in parser.deck_data:
            self.assertIn({"title": i.title}, deck_data_check)

    def test_render(self):
        parser = HelmRepositoryParser(GIT_REPO_URL)
        parser.parse()
        deck = parser.deck_data[0]
        environment = RenderEnvironment(specs_data=[], values_path="buzzword-counter/values.yaml")
        result = parser.render(*[(deck, environment)])
        deck, updated_environment = result[0]
        self.assertTrue(bool(updated_environment.specs_data))

    def test_parameters_are_parsed_from_render_environment(self):
        deck = DeckData("Test", "test", "test", "dir/path", {}, [])
        environment = RenderEnvironment(specs_data=[], values_path="buzzword-counter/values.yaml")
        environment.set_value("environmentVariables.DATABASE_NAME", "bumble-bee")
        params = utils.get_additional_render_parameters(deck, environment)
        self.assertIn("environmentVariables.DATABASE_NAME=bumble-bee", params)

    def test_parameters_are_read_from_yaml(self):
        deck = DeckData("Test", "test", "test", "dir/path", {}, [])
        environment = RenderEnvironment(specs_data=[], values_path="buzzword-counter/values.yaml")
        yaml = """
          a: Anna
          b:
            c: Cobra
            d:
             - name: first
               value: 1
             - name: second
               value: 2
        """
        environment.update_values_from_yaml(yaml)
        params = utils.get_additional_render_parameters(deck, environment)
        self.assertIn("b.d[0].name=first", params)

    def test_yaml_files_merging(self):
        yaml1 = """
          a: Anna
          b:
            c: Cobra
            d:
             - name: first
               value: 1
             - name: second
               value: 2
        """
        yaml2 = """
          a: Anton
          b:
            d:
             - name: first
               value: 1
             - name: third
               value: 2
          z: Zorro
        """
        result = utils.merge_multiple_yaml_files(yaml1, yaml2)
        expected_structure = {
            "a": "Anton",
            "b": {"c": "Cobra", "d": [{"name": "first", "value": 1}, {"name": "third", "value": 2}]},
            "z": "Zorro",
        }
        self.assertEqual(result, yaml.dump(expected_structure))

    def test_yaml_files_merging_from_git_repo(self):
        parser = HelmRepositoryParser(GIT_REPO_URL, branch="sops")
        parser.parse()
        deck = parser.deck_data[0]
        environment = RenderEnvironment(specs_data=[], values_path="buzzword-counter/helm_vars/development")
        result = parser.render(*[(deck, environment)])
        deck, updated_environment = result[0]
        data = yaml.load(updated_environment.values_yaml, Loader=yaml.SafeLoader)
        self.assertIn("DJANGO_DEBUG", data["environmentVariables"])
        self.assertIn("CELERY_UID", data["environmentVariables"])
        self.assertIn("imageCredentials", data)

    def test_render_with_values(self):
        parser = HelmRepositoryParser(GIT_REPO_URL)
        parser.parse()
        deck = parser.deck_data[0]
        environment = RenderEnvironment(specs_data=[], values_path="buzzword-counter/values.yaml")
        environment.set_value("environmentVariables.DATABASE_NAME", "bumble-bee")
        result = parser.render(*[(deck, environment)])
        deck, updated_environment = result[0]
        self.assertTrue(any(["bumble-bee" in i.content for i in updated_environment.specs_data]))

    def test_values_yaml_retrieval(self):
        parser = HelmRepositoryParser(GIT_REPO_URL)
        parser.parse()
        deck = parser.deck_data[0]
        environment = RenderEnvironment(specs_data=[], values_path="buzzword-counter/values.yaml")
        result = parser.render(*[(deck, environment)])
        deck, updated_environment = result[0]

        res = requests.get(
            "https://raw.githubusercontent.com/Blueshoe/buzzword-charts/master/buzzword-counter/values.yaml"
        )

        self.assertEqual(updated_environment.values_yaml, res.text)

    def test_get_specs_data_for_deck_hash(self):
        parser = HelmRepositoryParser(GIT_REPO_URL)
        environment = RenderEnvironment(specs_data=[], values_path="buzzword-counter/values.yaml")
        deck_hash = "c586a647818175e36bd0b17ab9a726a73e526fd3e3930205c60f90defee45f9e"
        specs_data = parser.get_specs(deck_hash, sops=None, environment=environment)
        self.assertTrue(bool(specs_data))
