import io
import json
from pathlib import Path
import pytest
from fontTools.ttLib import TTFont
from make_font_with_ai import brief,pipeline,authoring
from make_font_with_ai.common import GateError,read_json,write_json,safe_path
from make_font_with_ai.fingerprint import fingerprint
from make_font_with_ai.raster import verify
from make_font_with_ai.engine import compile_font


def prep(root):
    brief.confirm(root,'pytest fixture confirmation, not a production interview')
    return pipeline.prepare(root)

def simulated_review(root):
    return pipeline.review(root,'pytest explicit approval fixture','ai',
        'Synthetic review fixture to exercise the gate, not human or artistic certification.',
        accepted=True,all_pages=True,reference_match=True,native_readable=True)


def test_draft_cannot_confirm(tmp_path):
    p=tmp_path/'new';authoring.init_project(p)
    with pytest.raises(GateError,match='INTERVIEW_INCOMPLETE'):brief.confirm(p,'someone')


def test_prepare_requires_interview(pixel):
    with pytest.raises(GateError,match='MISSING_FILE'):pipeline.prepare(pixel)


def test_pixel_end_to_end_actual_write_reopen(pixel):
    state=prep(pixel)
    assert state['technical_pass'] is True
    technical=read_json(pixel/state['technical'])
    assert technical['native_pixel_equality_cases']==20
    assert technical['normalization_cases']==10
    with pytest.raises(GateError,match='MISSING_FILE'):pipeline.build(pixel)
    simulated_review(pixel)
    receipt=pipeline.build(pixel)
    path=pixel/receipt['output'];assert path.exists() and path.read_bytes()[:4]==b'\0\1\0\0'
    assert receipt['mode']=='ACTUAL_WRITE_AND_REOPEN'
    assert read_json(pixel/'output/atlas/atlas.json')['glyphs']['갈']['advance_px']==16
    assert pipeline.build(pixel)['semantic_sha256']==receipt['semantic_sha256']


def test_vector_curves_actual_build(vector):
    state=prep(vector)
    assert state['technical_pass'],read_json(vector/state['technical'])['failures']
    simulated_review(vector);receipt=pipeline.build(vector)
    assert (vector/receipt['output']).stat().st_size>1000


@pytest.mark.parametrize('change', ['cell','coverage','reference','metrics'])
def test_stale_brief_blocks_implementation(pixel,change):
    brief.confirm(pixel,'fixture')
    b=read_json(pixel/'design-brief.json')
    if change=='cell':b['target']['native_cell_px']=[17,16]
    if change=='coverage':b['coverage']['characters']=b['coverage']['characters'][:-1]
    if change=='reference':b['reference']['notes']+=' changed'
    if change=='metrics':b['metrics']['line_gap']=64
    write_json(pixel/'design-brief.json',b)
    with pytest.raises(GateError):pipeline.prepare(pixel)


def test_source_edit_invalidates_review(pixel):
    prep(pixel);simulated_review(pixel)
    src=read_json(pixel/'glyphs.json');src['glyphs']['A']['pixels'][0]='#'+'.'*15
    write_json(pixel/'glyphs.json',src)
    with pytest.raises(GateError,match='STALE_CANDIDATE'):pipeline.build(pixel)


@pytest.mark.parametrize('kind',['png','report','font'])
def test_tamper_rejected(pixel,kind):
    s=prep(pixel);simulated_review(pixel)
    if kind=='png':p=pixel/s['proofs_dir']/s['proofs'][0]['file']
    elif kind=='report':p=pixel/s['technical']
    else:p=pixel/s['candidate']
    if kind=='font':
        f=TTFont(p);f['hmtx'][f.getBestCmap()[ord('A')]]=(900,0);f.save(p)
    else:p.write_bytes(p.read_bytes()+b' changed')
    with pytest.raises((GateError,ValueError)):pipeline.build(pixel)


@pytest.mark.parametrize('decision',[False,'true',1,None])
def test_nonliteral_review_does_not_release(pixel,decision):
    prep(pixel);simulated_review(pixel)
    p=pixel/'.mfai/visual-review.json';r=read_json(p);r['accepted']=decision;write_json(p,r)
    with pytest.raises(GateError,match='VISUAL_REVIEW_REQUIRED'):pipeline.build(pixel)


def test_partial_review_blocked(pixel):
    prep(pixel)
    pipeline.review(pixel,'fixture','ai','Only a subset was inspected.',accepted=True,
                    all_pages=False,reference_match=True,native_readable=True)
    with pytest.raises(GateError,match='VISUAL_REVIEW_REQUIRED'):pipeline.build(pixel)


def test_rejected_reference_style_blocks_release(pixel):
    prep(pixel)
    pipeline.review(pixel,'fixture','ai','Readable but unlike the chosen reference.',accepted=True,
                    all_pages=True,reference_match=False,native_readable=True)
    with pytest.raises(GateError,match='VISUAL_REVIEW_REQUIRED'):pipeline.build(pixel)


def test_no_unrelated_overwrite(pixel):
    prep(pixel);simulated_review(pixel)
    p=pixel/'output/Native-Sixteen-Regular.ttf';p.parent.mkdir();p.write_bytes(b'existing unrelated file')
    with pytest.raises(Exception):pipeline.build(pixel)
    assert p.read_bytes()==b'existing unrelated file'


@pytest.mark.parametrize('value',['../outside','/tmp/escape','C:/Windows/a','C:\\Windows\\a','a/../../x'])
def test_path_traversal(tmp_path,value):
    with pytest.raises(GateError,match='PATH_ESCAPE'):safe_path(tmp_path,value,exists=False)


def test_symbolic_path_escape(tmp_path):
    p=tmp_path/'project';p.mkdir();other=tmp_path/'outside';other.mkdir()
    try:(p/'link').symlink_to(other,target_is_directory=True)
    except OSError:pytest.skip('Symlink permission not available in this Windows runner')
    with pytest.raises(GateError,match='PATH_ESCAPE'):safe_path(p,'link/out',exists=False)


def test_snapshot_no_fonts_or_credentials(pixel):
    s=prep(pixel);(pixel/'.env').write_text('SECRET=not_a_real_key')
    result=pipeline.snapshot(pixel,'after-candidate')
    import zipfile
    with zipfile.ZipFile(pixel/result['snapshot']) as z:
        assert not any(n.endswith('.ttf') or Path(n).name=='.env' for n in z.namelist())
        assert 'glyphs.json' in z.namelist()


def test_equivalent_serialization_accepted(pixel):
    b=brief.validate(pixel);data,_,_=compile_font(pixel,b);f=TTFont(io.BytesIO(data))
    f.recalcTimestamp=False;f['head'].modified+=100000
    out=io.BytesIO();f.save(out,reorderTables=False);other=out.getvalue()
    assert data!=other
    assert fingerprint(data)['semantic_sha256']==fingerprint(other)['semantic_sha256']


def test_one_coordinate_is_not_a_serialization_difference(pixel):
    b=brief.validate(pixel);data,_,_=compile_font(pixel,b);f=TTFont(io.BytesIO(data))
    gl=f['glyf'][f.getBestCmap()[ord('갈')]];x,y=gl.coordinates[0];gl.coordinates[0]=(x+1,y)
    out=io.BytesIO();f.save(out)
    assert fingerprint(data)['semantic_sha256']!=fingerprint(out.getvalue())['semantic_sha256']


def test_pixel_native_gate_catches_wrong_actual_output(pixel):
    b=brief.validate(pixel);data,meta,src=compile_font(pixel,b);f=TTFont(io.BytesIO(data))
    f['cmap'].tables[0].cmap[ord('갈')]=f.getBestCmap()[ord('각')]
    # Change every Unicode cmap, not just an unused encoding table.
    for tab in f['cmap'].tables:
        if tab.isUnicode():tab.cmap[ord('갈')]=f.getBestCmap()[ord('각')]
    out=io.BytesIO();f.save(out);r=verify(out.getvalue(),b,src,meta)
    assert not r['pass']
    assert any(x['code']=='NATIVE_PIXEL_MISMATCH' and x['char']=='갈' for x in r['failures'])


def test_atlas_import_does_not_resize(pixel):
    brief.confirm(pixel,'fixture');result=authoring.import_atlas(pixel,pixel/'reference.png',4)
    assert result['resized'] is False and result['glyphs_imported']==10
    with pytest.raises(GateError,match='ATLAS_DIMENSIONS'):authoring.import_atlas(pixel,pixel/'reference.png',5)


def test_crlf_json_no_version_failure(pixel):
    brief.confirm(pixel,'fixture');b=brief.approved(pixel)
    p=pixel/'glyphs.json';p.write_bytes(p.read_bytes().replace(b'\n',b'\r\n'))
    a,_,_=compile_font(pixel,b);assert fingerprint(a)['glyph_count']>10


def test_duplicate_json_and_nan_rejected(tmp_path):
    p=tmp_path/'x.json'
    p.write_text('{"a":1,"a":2}')
    with pytest.raises(GateError):read_json(p)
    p.write_text('{"a":NaN}')
    with pytest.raises(GateError):read_json(p)


def test_string_permission_not_approval(pixel):
    b=read_json(pixel/'design-brief.json');b['reference']['permission_confirmed']='true'
    write_json(pixel/'design-brief.json',b)
    with pytest.raises(GateError,match='REFERENCE_PERMISSION'):brief.confirm(pixel,'fixture')
