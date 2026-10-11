"""The same fixed phrase catalogue used by the frontend; no machine translation."""
import json
from pathlib import Path

CATALOGUE = json.loads((Path(__file__).resolve().parents[1] / 'assets' / 'catalogue.json').read_text(encoding='utf-8'))


def phrase(key, language='en'):
    entry = CATALOGUE['entries'][key]
    return entry.get(language, entry['en'])


def action_message(code, language='en'):
    return phrase('action.' + code, language)
