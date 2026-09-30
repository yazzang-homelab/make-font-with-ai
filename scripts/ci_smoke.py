"""Cross-OS build smoke: technical candidates, not artificial visual approvals.
Reports and PNG proofs may be uploaded by CI. Font binaries are never uploaded.
"""
from pathlib import Path
import argparse,json,shutil,platform,sys
from make_font_with_ai import brief,pipeline
from make_font_with_ai.common import read_json,write_json,sha
from make_font_with_ai.fingerprint import fingerprint
ROOT=Path(__file__).resolve().parents[1]

def run(name,dest):
    src=ROOT/'examples'/name;project=dest/name
    shutil.copytree(src,project,ignore=shutil.ignore_patterns('.mfai','output'),dirs_exist_ok=True)
    brief.confirm(project,'CI technical fixture; NOT user-facing design approval')
    state=pipeline.prepare(project)
    report=read_json(project/state['technical'])
    if state['technical_pass'] is not True:raise RuntimeError(json.dumps(report['failures'][:10],ensure_ascii=False))
    font=project/state['candidate'];data=font.read_bytes();fp=fingerprint(data)
    proofs=dest/'proofs'/name;shutil.copytree(project/state['proofs_dir'],proofs,dirs_exist_ok=True)
    result={'example':name,'os':platform.system(),'python':platform.python_version(),
        'pass':True,'actual_candidate_written_and_reopened':font.exists(),
        'font_bytes':len(data),'raw_sha256':sha(data),'semantic_sha256':fp['semantic_sha256'],
        'character_count':report['character_count'],'raster_cases':report['raster_cases'],
        'native_pixel_equality_cases':report['native_pixel_equality_cases'],
        'specialized_checks':report['specialized_checks'],'new_visual_review_performed':False,
        'font_binary_uploaded':False}
    write_json(dest/(name+'-result.json'),result)
    print('SMOKE_PASS',json.dumps(result,ensure_ascii=False),flush=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'_ci');p.add_argument('--brush',action='store_true');a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    names=['hangul-brush'] if a.brush else ['pixel16','vector']
    for name in names:run(name,a.out)
