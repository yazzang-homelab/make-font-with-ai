import io,json
from pathlib import Path
import pytest
from PIL import Image,ImageDraw
from fontTools.ttLib import TTFont
from make_font_with_ai import brief,authoring,pipeline
from make_font_with_ai.common import GateError,read_json,write_json
from make_font_with_ai.engine import compile_font
from make_font_with_ai.raster import Renderer
from make_font_with_ai.fingerprint import fingerprint


def test_trace_keeps_real_hole(vector,tmp_path):
    b=read_json(vector/'design-brief.json');b['coverage']['characters']='O';b['acceptance']['specimen_text']='OOO'
    write_json(vector/'design-brief.json',b);write_json(vector/'glyphs.json',{'format':'vector-v1','glyphs':{}})
    im=Image.new('L',(100,100));d=ImageDraw.Draw(im);d.rectangle((20,15,79,84),fill=255);d.rectangle((35,30,64,69),fill=0)
    im.save(vector/'ring.png');brief.confirm(vector,'test explicit crop identity')
    authoring.trace_glyph(vector,vector/'ring.png','O')
    data,_,_=compile_font(vector,brief.validate(vector));a,clip=Renderer(data,brief.validate(vector)).glyph('O',100)
    assert not clip and a[50,50]==0 and a[50,24]>0


def test_unknown_hybrid_not_silently_built(pixel):
    b=read_json(pixel/'design-brief.json');b['production_kind']='hybrid';write_json(pixel/'design-brief.json',b)
    with pytest.raises(GateError,match='PRODUCTION_KIND'):brief.confirm(pixel,'fixture')


def test_legacy_encoding_requires_adapter(pixel):
    b=read_json(pixel/'design-brief.json');b['coverage']['encoding']='shift-jis';write_json(pixel/'design-brief.json',b)
    with pytest.raises(GateError,match='COVERAGE_ENCODING'):brief.confirm(pixel,'fixture')


def test_invalid_nested_fields_rejected(pixel):
    b=read_json(pixel/'design-brief.json');b['font']['execute']='evil';write_json(pixel/'design-brief.json',b)
    with pytest.raises(GateError,match='BRIEF_SCHEMA'):brief.confirm(pixel,'fixture')


def test_confirmation_cannot_follow_state_symlink(pixel,tmp_path):
    other=tmp_path/'outside';other.mkdir()
    try:(pixel/'.mfai').symlink_to(other,target_is_directory=True)
    except OSError:pytest.skip('No symlink privilege')
    with pytest.raises(GateError,match='PATH_ESCAPE'):brief.confirm(pixel,'fixture')
    assert list(other.iterdir())==[]


def test_reference_image_replacement_stales_approval(pixel):
    brief.confirm(pixel,'fixture');Image.new('L',(64,48),255).save(pixel/'reference.png')
    with pytest.raises(GateError,match='BRIEF_NOT_APPROVED'):pipeline.prepare(pixel)


def test_release_cannot_use_another_candidates_report(pixel):
    brief.confirm(pixel,'fixture');state=pipeline.prepare(pixel)
    path=pixel/state['technical'];r=read_json(path);r['font_raw_sha256']='0'*64;write_json(path,r)
    with pytest.raises(GateError,match='REPORT_CHANGED'):pipeline.load_current(pixel)


def test_numeric_coordinate_nan_never_compiles(vector):
    raw=(vector/'glyphs.json').read_text();raw=raw.replace('140','NaN',1)
    # Invalid SVG syntax as well as JSON nonfinite numbers is rejected.
    (vector/'glyphs.json').write_text(raw)
    with pytest.raises(Exception):compile_font(vector,brief.validate(vector))


def test_outline_winding_not_normalized_away(vector):
    b=brief.validate(vector);data,_,_=compile_font(vector,b);f=TTFont(io.BytesIO(data))
    g=f['glyf'][f.getBestCmap()[ord('A')]]
    g.coordinates[1]=(g.coordinates[1][0]+3,g.coordinates[1][1])
    buf=io.BytesIO();f.save(buf)
    assert fingerprint(data)['semantic_sha256']!=fingerprint(buf.getvalue())['semantic_sha256']
