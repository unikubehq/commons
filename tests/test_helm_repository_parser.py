from unittest import TestCase

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

    def test_render_with_values(self):
        parser = HelmRepositoryParser(GIT_REPO_URL)
        parser.parse()
        deck = parser.deck_data[0]
        environment = RenderEnvironment(specs_data=[], values_path="buzzword-counter/values.yaml")
        environment.set_value("environmentVariables.DATABASE_NAME", "bumble-bee")
        result = parser.render(*[(deck, environment)])
        deck, updated_environment = result[0]
        self.assertTrue(any(["bumble-bee" in i.content for i in updated_environment.specs_data]))

    def test_get_specs_data_for_deck_hash(self):
        parser = HelmRepositoryParser(GIT_REPO_URL)
        environment = RenderEnvironment(specs_data=[], values_path="buzzword-counter/values.yaml")
        deck_hash = "c586a647818175e36bd0b17ab9a726a73e526fd3e3930205c60f90defee45f9e"
        specs_data = parser.get_specs(deck_hash, sops=None, environment=environment)
        self.assertTrue(bool(specs_data))
