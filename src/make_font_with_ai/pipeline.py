"""Approval-bound lifecycle: brief -> candidate -> actual proofs -> review -> export."""
from __future__ import annotations
import json
import platform
import re
import uuid
from pathlib import Path
from .common import require, read_json, write_json, safe_path, sha, digest, now, atomic_bytes
from .brief import approved, brief_identity
from .engine import compile_font, input_identity
from .fingerprint import fingerprint
from .raster import verify, proofs, atlas

def _root(root):
    root=Path(root).resolve();require(root.is_dir(),'PROJECT_MISSING',str(root));return root

def prepare(root:Path) -> dict:
    root=_root(root);b=approved(root);identity=input_identity(root,b)
    print('[BUILD] Creating and reloading the actual candidate. This may take several minutes.',flush=True)
    data,meta,source=compile_font(root,b);fp=fingerprint(data)
    token=identity[:12]+'-'+uuid.uuid4().hex[:10]
    folder=safe_path(root,'.mfai/candidates/'+token,exists=False);folder.mkdir(parents=True)
    atomic_bytes(folder/'candidate.ttf',data,overwrite=False)
    check=verify(data,b,source,meta);write_json(folder/'technical.json',check)
    pages=proofs(data,b,folder/'proofs')
    state={'format_version':1,'input_sha256':identity,'brief_sha256':brief_identity(root,b),
           'semantic_sha256':fp['semantic_sha256'],'raw_font_sha256':sha(data),
           'candidate':(folder/'candidate.ttf').relative_to(root).as_posix(),
           'technical':(folder/'technical.json').relative_to(root).as_posix(),
           'technical_sha256':sha((folder/'technical.json').read_bytes()),
           'proofs_dir':(folder/'proofs').relative_to(root).as_posix(),
           'proofs':pages,'proof_manifest_sha256':digest(pages),'technical_pass':check['pass'],
           'visual_approval':False,'created':now(),'host_os':platform.system()}
    write_json(folder/'fingerprint.json',fp);write_json(folder/'state.json',state)
    write_json(safe_path(root,'.mfai/current.json',exists=False),state)
    print('[CANDIDATE_WRITTEN]',state['candidate'],flush=True)
    print('[ACTUAL_PROOFS]',state['proofs_dir']+'/index.html',flush=True)
    return state

def load_current(root:Path,*,need_pass:bool=True):
    b=approved(root);current=read_json(safe_path(root,'.mfai/current.json'))
    require(current.get('input_sha256')==input_identity(root,b),'STALE_CANDIDATE','Brief, reference, drawing or engine changed')
    data=safe_path(root,current['candidate']).read_bytes();fp=fingerprint(data)
    require(sha(data)==current.get('raw_font_sha256') and fp['semantic_sha256']==current.get('semantic_sha256'),
            'CANDIDATE_CHANGED','Candidate no longer matches reviewed input')
    tp=safe_path(root,current['technical']);report=read_json(tp)
    require(sha(tp.read_bytes())==current.get('technical_sha256'),'REPORT_CHANGED','Technical report altered')
    require(report.get('font_raw_sha256')==sha(data),'REPORT_BINDING','Report belongs to another candidate')
    if need_pass:
        require(current.get('technical_pass') is True and report.get('pass') is True and report.get('failures')==[],
                'TECHNICAL_GATE_FAILED','Correct the actual candidate and prepare again')
    require(digest(current['proofs'])==current.get('proof_manifest_sha256'),'PROOF_MANIFEST_CHANGED','Proof list changed')
    proofdir=safe_path(root,current['proofs_dir'],exists=False)
    for row in current['proofs']:
        p=safe_path(proofdir,row['file'])
        require(sha(p.read_bytes())==row['sha256'],'PROOF_CHANGED',row['file'])
    return b,current,data

def review(root:Path,reviewer:str,reviewer_type:str,notes:str,*,accepted:bool,
           all_pages:bool,reference_match:bool,native_readable:bool) -> dict:
    root=_root(root);b,state,_=load_current(root)
    require(all(type(x)is bool for x in (accepted,all_pages,reference_match,native_readable)),
            'REVIEW_BOOLEAN','Review decisions must be booleans')
    require(reviewer_type in ('human','ai'),'REVIEWER_TYPE','Record human or AI review honestly')
    require(bool(reviewer.strip()) and len(notes.strip())>=8,'REVIEW_NOTES','State reviewer and actual findings')
    record={'input_sha256':state['input_sha256'],'semantic_sha256':state['semantic_sha256'],
            'proof_manifest_sha256':state['proof_manifest_sha256'],
            'reviewer':reviewer,'reviewer_type':reviewer_type,'notes':notes,
            'accepted':accepted,'all_pages_reviewed':all_pages,'reference_style_accepted':reference_match,
            'native_size_readable':native_readable,'time':now(),
            'attestation':'Explicit reviewer assertion; not proof of identity or automatic beauty certification'}
    write_json(safe_path(root,'.mfai/visual-review.json',exists=False),record)
    return record

def build(root:Path,output_dir:str='output') -> dict:
    root=_root(root);b,state,_=load_current(root)
    record=read_json(safe_path(root,'.mfai/visual-review.json'))
    for k in ('input_sha256','semantic_sha256','proof_manifest_sha256'):
        require(record.get(k)==state.get(k),'STALE_REVIEW','Review must bind this exact candidate and proofs')
    for k in ('accepted','all_pages_reviewed','reference_style_accepted','native_size_readable'):
        require(record.get(k) is True,'VISUAL_REVIEW_REQUIRED',k)
    require(record.get('reviewer_type') in ('human','ai') and bool(record.get('reviewer')),
            'VISUAL_REVIEW_REQUIRED','Valid reviewer attribution required')
    print('[REBUILD] Verifying the output instead of trusting a prior process exit.',flush=True)
    data,meta,source=compile_font(root,b);fp=fingerprint(data)
    require(fp['semantic_sha256']==state['semantic_sha256'],'STRUCTURAL_MISMATCH',
            'Coordinates, metrics, mapping, shaping or metadata changed; timestamp-only differences are allowed')
    check=verify(data,b,source,meta)
    require(check.get('pass') is True,'OUTPUT_VERIFICATION_FAILED',json.dumps(check['failures'][:8],ensure_ascii=False))
    out=safe_path(root,output_dir,exists=False);out.mkdir(parents=True,exist_ok=True)
    require(not out.is_symlink(),'OUTPUT_SYMLINK','Output cannot be a symlink')
    filename=re.sub(r'[^A-Za-z0-9_-]+','-',b['font']['family']).strip('-')[:60] or 'AIFont'
    dest=safe_path(root,(out/f'{filename}-Regular.ttf').relative_to(root).as_posix(),exists=False)
    if dest.exists():
        existing=dest.read_bytes()
        require(fingerprint(existing)['semantic_sha256']==fp['semantic_sha256'],'OUTPUT_EXISTS',
                'Another font already occupies the target; choose a new output folder')
        data=existing
    else:atomic_bytes(dest,data,overwrite=False)
    saved=dest.read_bytes();savedfp=fingerprint(saved)
    require(savedfp['semantic_sha256']==fp['semantic_sha256'],'POSTWRITE_MISMATCH','Saved bytes changed')
    receipt={'success':True,'mode':'ACTUAL_WRITE_AND_REOPEN','output':dest.relative_to(root).as_posix(),
             'bytes':len(saved),'raw_sha256':sha(saved),'semantic_sha256':savedfp['semantic_sha256'],
             'source_input_sha256':state['input_sha256'],'reviewer_type':record['reviewer_type'],
             'review_notes':record['notes'],'host_os':platform.system(),'python':platform.python_version(),
             'target_engine_tested':False,'os_installation_tested':False,'time':now()}
    if 'atlas' in b['exports']:receipt['atlas']=atlas(saved,b,out/'atlas')
    write_json(out/'build-receipt.json',receipt)
    print('[FONT_SAVED_AND_REOPENED]',receipt['output'],flush=True)
    return receipt

def snapshot(root:Path,label:str) -> dict:
    import zipfile
    root=_root(root)
    require(bool(re.fullmatch('[A-Za-z0-9_-]{1,64}',label)),'SNAPSHOT_LABEL','Use letters/numbers/dashes')
    folder=safe_path(root,'.mfai/snapshots',exists=False);folder.mkdir(parents=True,exist_ok=True)
    file=folder/(label+'-'+uuid.uuid4().hex[:8]+'.zip')
    entries=[]
    with zipfile.ZipFile(file,'x',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(root.rglob('*')):
            if not p.is_file() or p.is_symlink():continue
            rel=p.relative_to(root)
            if any(x in rel.parts for x in ('.git','output','__pycache__','snapshots')) or any(x.startswith('.venv') for x in rel.parts):continue
            if p.suffix.lower() in ('.ttf','.otf','.woff','.woff2','.ttc','.pyc'):continue
            if p.name.startswith('.env'):continue
            require(p.stat().st_size<=50_000_000,'SNAPSHOT_FILE_SIZE',str(rel))
            z.write(p,rel.as_posix());entries.append(rel.as_posix())
    result={'snapshot':file.relative_to(root).as_posix(),'sha256':sha(file.read_bytes()),
            'files':entries,'kind':'Project source/evidence, not VM snapshot','time':now()}
    write_json(file.with_suffix('.json'),result);return result
