"""Static UI contract: guard against the T3 DOM mismatch seen in Chrome."""
from pathlib import Path
from html.parser import HTMLParser
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

class IdParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.ids.append(attributes["id"])

class WebContractTests(unittest.TestCase):
    def test_javascript_dom_ids_match_html(self):
        js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        parser = IdParser()
        parser.feed(html)
        self.assertEqual(len(parser.ids), len(set(parser.ids)), "Duplicate DOM id")
        ids = set(parser.ids)
        for name in re.findall(r"\$\('([a-zA-Z][a-zA-Z0-9-]*)'\)", js):
            self.assertIn(name, ids, f"No HTML element for JS id {name}")
        for name in re.findall(r"text\('([a-zA-Z][a-zA-Z0-9-]*)'\s*,", js):
            self.assertIn(name, ids, f"No HTML element for JS text target {name}")

    def test_roles_do_not_style_a_nonexistent_progress_bar(self):
        js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        role_code = js.split('function renderRoles(data){', 1)[1].split('function render(data){', 1)[0]
        self.assertNotIn('.bar > span', role_code)
        self.assertNotIn('p.planned', role_code)
        program_code = js.split('function renderPrograms(data){', 1)[1].split('function renderRoles(data){', 1)[0]
        self.assertIn('.bar > span', program_code)

    def test_client_failure_is_not_always_called_relate_failure(self):
        js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("phase='UI rendering'", js)
        self.assertIn('`${phase} FAILED`', js)

if __name__ == '__main__':
    unittest.main()
