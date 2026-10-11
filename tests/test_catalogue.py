"""Catalogue gaps must fail before translated screens ship."""
import json
import re
import unittest
from pathlib import Path


class CatalogueTests(unittest.TestCase):
    def test_every_key_has_all_languages_and_matching_placeholders(self):
        data = json.loads((Path(__file__).resolve().parents[1] / 'assets/catalogue.json').read_text(encoding='utf-8'))
        for key, row in data['entries'].items():
            for language in ('en', 'hi', 'mr'):
                with self.subTest(key=key, language=language):
                    self.assertTrue(row.get(language, '').strip(), 'Missing translation')
                    self.assertEqual(sorted(re.findall(r'\{\d+\}', row['en'])), sorted(re.findall(r'\{\d+\}', row[language])))
        for language in ('hi', 'mr'):
            self.assertEqual(data['meta'][language]['review'], 'needs native review')
