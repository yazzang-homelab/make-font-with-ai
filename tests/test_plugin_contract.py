from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]

def test_plugin_metadata_and_skill():
    p=json.loads((ROOT/'.claude-plugin/plugin.json').read_text())
    m=json.loads((ROOT/'.claude-plugin/marketplace.json').read_text())
    assert p['name']=='make-font-with-ai' and p['license']=='PolyForm-Noncommercial-1.0.0'
    assert m['plugins'][0]['source']=='./'
    s=(ROOT/'skills/make-font/SKILL.md').read_text()
    assert s.startswith('---\nname: make-font\n')
    assert 'Stage 2A' in s and '16x16' in s and 'explicit user confirmation' in s

def test_license_is_noncommercial_not_mit():
    assert '# PolyForm Noncommercial License 1.0.0' in (ROOT/'LICENSE').read_text()
    assert 'Required Notice:' in (ROOT/'NOTICE').read_text()

def test_schema_matches_examples():
    from jsonschema import Draft202012Validator
    schema=json.loads((ROOT/'schemas/design-brief.schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    for folder in ('pixel16','vector','hangul-brush'):
        b=json.loads((ROOT/'examples'/folder/'design-brief.json').read_text())
        assert not list(Draft202012Validator(schema).iter_errors(b))
