"""The interview is an enforceable input gate, not a paragraph of suggestions."""
from __future__ import annotations
from pathlib import Path
import re
from PIL import Image
from .common import GateError, require, read_json, write_json, digest, safe_path, sha, now

COVERAGE_MODES = ('custom', 'ascii', 'ksx1001', 'modern_hangul')

def characters(brief: dict) -> str:
    c = brief['coverage']; mode = c['mode']
    if mode == 'ascii': text = ''.join(chr(x) for x in range(32, 127))
    elif mode == 'ksx1001':
        text = ''.join(bytes((a, b)).decode('euc_kr') for a in range(0xB0, 0xC9)
                       for b in range(0xA1, 0xFF))
    elif mode == 'modern_hangul': text = ''.join(chr(x) for x in range(0xAC00, 0xD7A4))
    elif mode == 'custom': text = c.get('characters')
    else: raise GateError('COVERAGE_MODE', str(mode))
    require(isinstance(text, str) and 0 < len(text) <= 20000,
            'COVERAGE_EMPTY', 'Choose an explicit character set, not an empty placeholder')
    require(len(set(text)) == len(text), 'COVERAGE_DUPLICATE', 'Characters must be unique')
    require(all(ord(x) >= 32 and not 0xD800 <= ord(x) <= 0xDFFF and ord(x) not in (127,)
                for x in text), 'INVALID_CODEPOINT', 'Control/surrogate codepoints are unsupported')
    return text

def integer(v, lo, hi, name):
    require(type(v) is int and lo <= v <= hi, 'INVALID_NUMBER', f'{name}: {v!r}')

def validate(root: Path) -> dict:
    b = read_json(root/'design-brief.json', 1_000_000)
    require(isinstance(b, dict), 'BRIEF_TYPE', 'Expected a JSON object')
    needed = {'schema_version', 'font', 'purpose', 'production_kind', 'target', 'metrics',
              'coverage', 'reference', 'source', 'exports', 'acceptance'}
    require(set(b) == needed, 'BRIEF_FIELDS', f'Missing/unknown fields: {set(b)^needed}')
    require(b['schema_version'] == '1.0', 'BRIEF_VERSION', str(b['schema_version']))
    for k in ('use_case', 'typography_role'):
        require(isinstance(b['purpose'].get(k), str) and b['purpose'][k].strip(),
                'INTERVIEW_INCOMPLETE', 'purpose.'+k)
    require(b['production_kind'] in ('bitmap', 'vector'), 'PRODUCTION_KIND',
            'Choose bitmap or vector. Hybrid is two independently reviewed projects in v0.1.')
    f = b['font']; family = f.get('family')
    require(isinstance(family, str) and bool(family.strip()) and len(family) <= 90 and
            all(ord(c) >= 32 for c in family), 'FAMILY_NAME', 'A safe, non-empty family is required')
    require(isinstance(f.get('version'), str) and re.fullmatch(r'\d+\.\d+(?:\.\d+)?', f['version']),
            'FONT_VERSION', 'Use a numeric dotted version')
    integer(f.get('upm'), 64, 16384, 'font.upm')
    m = b['metrics']; integer(m.get('ascent'), 1, 32000, 'ascent')
    integer(m.get('descent'), -32000, 0, 'descent')
    integer(m.get('line_gap'), 0, 32000, 'line_gap')
    integer(m.get('advance'), 1, 32000, 'advance')
    require(m.get('spacing') in ('monospace', 'proportional'), 'SPACING', str(m.get('spacing')))
    t = b['target']
    for k in ('engine', 'renderer'):
        require(isinstance(t.get(k), str) and t[k].strip(), 'INTERVIEW_INCOMPLETE', 'target.'+k)
    require(type(t.get('antialiasing')) is bool, 'INTERVIEW_INCOMPLETE', 'target.antialiasing')
    sizes = t.get('sizes_px')
    require(isinstance(sizes, list) and 0 < len(sizes) <= 8, 'SIZES_REQUIRED', 'Choose actual output sizes')
    for size in sizes: integer(size, 4, 512, 'target.sizes_px')
    require(len(sizes) == len(set(sizes)), 'DUPLICATE_SIZE', 'Sizes must be distinct')
    src = b['source']
    require(src.get('kind') in ('bitmap-json', 'vector-json', 'r36-hangul'), 'SOURCE_KIND', str(src.get('kind')))
    if b['production_kind'] == 'bitmap':
        require(src['kind'] == 'bitmap-json', 'PIXEL_SOURCE', 'Native pixels require bitmap-json')
        cell = t.get('native_cell_px')
        require(isinstance(cell, list) and len(cell) == 2, 'CELL_REQUIRED', 'Set width and height')
        for n in cell: integer(n, 4, 128, 'cell')
        w,h = cell
        require(t['antialiasing'] is False, 'PIXEL_SMOOTHING', 'Native pixel review cannot silently smooth')
        require(h in sizes and all(s % h == 0 for s in sizes), 'PIXEL_SCALE', 'Review 1x plus integer scales')
        require(f['upm'] % h == 0, 'GRID_METRICS', 'UPM must divide evenly by native cell height')
        unit = f['upm']//h
        require(m['ascent']-m['descent'] == f['upm'] and m['ascent'] % unit == 0,
                'GRID_METRICS', 'Baseline and total height must be on the native grid')
        require(m['spacing']=='monospace' and m['advance']==w*unit, 'GRID_ADVANCE', 'Use the approved cell width')
    else:
        require(src['kind'] in ('vector-json','r36-hangul'), 'VECTOR_SOURCE', 'Choose a vector source')
        require(t.get('native_cell_px') is None, 'VECTOR_CELL', 'Use null native_cell_px for vector projects')
    require(isinstance(b['exports'], list) and 'ttf' in b['exports'] and
            set(b['exports']) <= {'ttf','atlas'}, 'EXPORTS', 'v0.1 supports ttf and optional PNG atlas+JSON')
    require(b['coverage'].get('encoding') == 'unicode', 'COVERAGE_ENCODING', 'v0.1 exports Unicode cmap and Unicode atlas mapping; legacy byte encodings require a separate adapter')
    text = characters(b)
    a=b['acceptance']
    integer(a.get('max_font_bytes'),1000,100_000_000,'max_font_bytes')
    offset=a.get('max_center_offset_em')
    require(type(offset) in (float,int) and 0 < offset <= .5, 'CENTER_LIMIT', 'Choose an optical flag threshold')
    require(isinstance(a.get('specimen_text'), str) and a['specimen_text'].strip(),
            'SPECIMEN_REQUIRED', 'Real use-case text must be reviewed')
    require(set(a['specimen_text']) <= set(text)|{' ','\n'}, 'SPECIMEN_COVERAGE', 'Specimen uses uncovered characters')
    pairs=a.get('critical_pairs')
    require(isinstance(pairs,list) and all(isinstance(p,str) and len(p)==2 and set(p)<=set(text)
                                         and p[0]!=p[1] for p in pairs), 'CRITICAL_PAIRS', 'Use covered two-character pairs')
    require(isinstance(a.get('style_notes'), str) and a['style_notes'].strip(), 'STYLE_NOTES', 'What must survive from the reference?')
    r=b['reference']; path=safe_path(root,r.get('path'))
    require(r.get('permission_confirmed') is True, 'REFERENCE_PERMISSION', 'Confirm permission/provenance')
    require(r.get('source') in ('owned','generated','permitted'), 'REFERENCE_SOURCE', 'Record owned/generated/permitted')
    require(isinstance(r.get('notes'),str) and r['notes'].strip(), 'REFERENCE_NOTES', 'Record relevant style and limitations')
    require(path.stat().st_size<=30_000_000, 'REFERENCE_SIZE', 'Reference is too large')
    try:
        with Image.open(path) as im:
            require(im.format in ('PNG','JPEG','WEBP'), 'REFERENCE_FORMAT', 'Use PNG/JPEG/WEBP')
            require(im.width*im.height<=32_000_000, 'REFERENCE_SIZE', 'Too many image pixels')
            im.verify()
    except (OSError, Image.DecompressionBombError) as e:
        raise GateError('REFERENCE_IMAGE',str(e)) from e
    from jsonschema import Draft202012Validator
    schema=read_json(Path(__file__).with_name('brief.schema.json'))
    errors=sorted(Draft202012Validator(schema).iter_errors(b),key=lambda e:str(e.path))
    require(not errors,'BRIEF_SCHEMA',str(errors[0].message) if errors else '')
    return b

def brief_identity(root:Path,b:dict) -> str:
    return digest({'brief':b,'reference_sha256':sha(safe_path(root,b['reference']['path']).read_bytes())})

def confirm(root:Path,reviewer:str) -> dict:
    b=validate(root)
    require(bool(reviewer.strip()), 'CONFIRMATION_NAME', 'Record who confirmed the interview')
    approval={'brief_sha256':brief_identity(root,b),'confirmed_by':reviewer,'time':now(),
              'note':'Explicit attestation; not an authentication or legal-rights certificate'}
    write_json(safe_path(root,'.mfai/brief-approval.json',exists=False),approval)
    return approval

def approved(root:Path) -> dict:
    b=validate(root);a=read_json(safe_path(root,'.mfai/brief-approval.json'))
    require(a.get('brief_sha256')==brief_identity(root,b) and bool(a.get('confirmed_by')),
            'BRIEF_NOT_APPROVED', 'Reconfirm the interview after changing brief/reference')
    return b
