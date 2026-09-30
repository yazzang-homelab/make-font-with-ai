"""Isolated trusted R36 worker. JSON does not select modules or arbitrary commands."""
from pathlib import Path
import sys,json
from build_font import build_font,serialize

def main():
    job=json.loads(Path(sys.argv[1]).read_text());chars=job['characters']
    if not isinstance(chars,str) or not chars:raise ValueError('Missing selected character set')
    # Full source family preserves original modern-Jamo GSUB behavior and lets
    # the original KS X 1001-specific regression suite run without fake subsets.
    f,m=build_font();data=serialize(f)
    from rieul_gate import run as rieul
    from layout_audit import scan as balance
    from optical_qa import run as optical
    from context_gates import inspect as corners
    from composite_qa import run as composite
    checks={};summaries={}
    for name,fn in [('rieul',lambda:rieul(data,m)),('balance',lambda:balance(data)),
                    ('optical',lambda:optical(data)),('corners',lambda:corners(data,m)),
                    ('component_visibility',lambda:composite(data,m))]:
        result=fn();r=result[0] if isinstance(result,tuple) else result
        ok=r.get('pass') is True
        if name=='component_visibility':ok=ok and r.get('minimum_component_visible_ink',0)>=.8
        checks[name]=ok;summaries[name]={k:v for k,v in r.items() if k not in ('rows','failures','findings','body_aspect_details','allograph_cases')}
        print(name,ok,flush=True)
    Path(sys.argv[2]).write_bytes(data)
    Path(sys.argv[3]).write_text(json.dumps({'engine':'r36-hangul','specialized_checks':checks,
        'profile_checks':summaries,'actual_font_coverage':11172,
        'requested_review_coverage':len(chars),'new_visual_review_performed':False},ensure_ascii=False),encoding='utf-8')
if __name__=='__main__':main()
