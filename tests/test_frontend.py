import os
import unittest


ROOT = os.path.dirname(os.path.dirname(__file__))


class FrontendVisualContractTests(unittest.TestCase):
    def test_mobile_viewport_and_relationship_diagram_are_present(self):
        """A lightweight visual contract without requiring a browser runtime."""
        static = os.path.join(ROOT, "decentral", "web", "static")
        with open(os.path.join(static, "index.html"), "r") as handle:
            html = handle.read()
        with open(os.path.join(static, "styles.css"), "r") as handle:
            css = handle.read()
        with open(os.path.join(static, "app.js"), "r") as handle:
            js = handle.read()
        self.assertIn('name="viewport"', html)
        self.assertIn('id="diagram"', html)
        self.assertIn('@media (max-width: 700px)', css)
        self.assertIn('renderDiagram', js)
