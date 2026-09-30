"""Scan publishable files; generated fonts and machine-specific paths are not source."""
from pathlib import Path
import re,subprocess,json
ROOT=Path(__file__).resolve().parents[1]

def audit():
    result=subprocess.run(['git','ls-files','-z'],cwd=ROOT,capture_output=True)
    names=result.stdout.decode().split('\0') if result.returncode==0 else []
    if not any(names):names=[p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()
        and not any(x in p.parts for x in ('.git','.mfai','.venv','__pycache__','output','_ci'))]
    bad=[];checked=0
    forbidden={'.ttf','.otf','.woff','.woff2','.ttc','.eot','.pyc'}
    magic={b'\x00\x01\x00\x00',b'OTTO',b'wOFF',b'wOF2',b'ttcf'}
    keypat=re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)')
    for name in names:
        if not name:continue
        p=ROOT/name
        if not p.is_file():continue
        data=p.read_bytes();checked+=1
        if p.suffix.lower() in forbidden or data[:4] in magic:bad.append([name,'font/cache binary'])
        if keypat.search(data):bad.append([name,'credential pattern'])
        if name!= 'scripts/audit_repo.py' and any(s in data for s in (b'/mnt/synology_devdata',b'C:\\Users\\',b'/home/runner/work/_temp/')):
            bad.append([name,'private machine path'])
    assert not bad,json.dumps(bad)
    print('PUBLICATION_AUDIT_PASS',checked,'source/evidence files; no font binaries or key patterns')
if __name__=='__main__':audit()
