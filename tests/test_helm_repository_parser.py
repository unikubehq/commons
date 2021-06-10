from unittest import TestCase

from commons.helm.data_classes import RenderEnvironment
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
        self.assertEqual(len(updated_environment.specs_data), 18)

    def test_get_specs_data_for_deck_hash(self):
        parser = HelmRepositoryParser(GIT_REPO_URL)
        environment = RenderEnvironment(specs_data=[], values_path="buzzword-counter/values.yaml")
        deck_hash = "c586a647818175e36bd0b17ab9a726a73e526fd3e3930205c60f90defee45f9e"
        specs_data = parser.get_specs(deck_hash, sops=None, environment=environment)
        self.assertEqual(len(specs_data), 18)
