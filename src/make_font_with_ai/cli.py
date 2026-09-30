from __future__ import annotations
import argparse
import json
import platform
import sys
from pathlib import Path
from . import __version__
from .common import GateError


def parser():
    p=argparse.ArgumentParser(prog='mfai',description='Interview -> real candidate -> review -> verified font file')
    p.add_argument('--version',action='version',version=__version__)
    sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('init');q.add_argument('project',type=Path);q.add_argument('--kind',choices=['bitmap','vector'],default='bitmap');q.add_argument('--cell',type=int,default=16)
    q=sub.add_parser('check-brief');q.add_argument('project',type=Path)
    q=sub.add_parser('confirm-brief');q.add_argument('project',type=Path);q.add_argument('--by',required=True)
    q=sub.add_parser('prepare');q.add_argument('project',type=Path)
    q=sub.add_parser('status');q.add_argument('project',type=Path)
    q=sub.add_parser('review');q.add_argument('project',type=Path);q.add_argument('--reviewer',required=True)
    q.add_argument('--reviewer-type',choices=['human','ai'],required=True);q.add_argument('--notes',required=True)
    q.add_argument('--accept',action='store_true');q.add_argument('--all-pages',action='store_true')
    q.add_argument('--reference-match',action='store_true');q.add_argument('--native-readable',action='store_true')
    q=sub.add_parser('build');q.add_argument('project',type=Path);q.add_argument('--output-dir',default='output')
    q=sub.add_parser('snapshot');q.add_argument('project',type=Path);q.add_argument('--label',required=True)
    q=sub.add_parser('import-atlas');q.add_argument('project',type=Path);q.add_argument('image',type=Path)
    q.add_argument('--columns',type=int,required=True);q.add_argument('--threshold',type=int,default=128);q.add_argument('--dark-ink',action='store_true')
    q=sub.add_parser('trace-glyph');q.add_argument('project',type=Path);q.add_argument('image',type=Path)
    q.add_argument('--char',required=True);q.add_argument('--box',nargs=4,type=int);q.add_argument('--threshold',type=int,default=128);q.add_argument('--dark-ink',action='store_true')
    sub.add_parser('doctor')
    return p


def main(argv=None):
    args=parser().parse_args(argv)
    try:
        from . import brief,pipeline,authoring
        c=args.command
        root=args.project.resolve() if hasattr(args,'project') else None
        if c=='init':result=authoring.init_project(root,args.kind,args.cell)
        elif c=='check-brief':result=brief.validate(root)
        elif c=='confirm-brief':result=brief.confirm(root,args.by)
        elif c=='prepare':
            result=pipeline.prepare(root)
            print(json.dumps(result,ensure_ascii=False,indent=2))
            return 0 if result['technical_pass'] else 2
        elif c=='status':
            b,s,_=pipeline.load_current(root,need_pass=False)
            result={'current':s,'review_exists':(root/'.mfai/visual-review.json').is_file()}
        elif c=='review':result=pipeline.review(root,args.reviewer,args.reviewer_type,args.notes,
            accepted=args.accept,all_pages=args.all_pages,reference_match=args.reference_match,native_readable=args.native_readable)
        elif c=='build':result=pipeline.build(root,args.output_dir)
        elif c=='snapshot':result=pipeline.snapshot(root,args.label)
        elif c=='import-atlas':result=authoring.import_atlas(root,args.image,args.columns,args.threshold,args.dark_ink)
        elif c=='trace-glyph':result=authoring.trace_glyph(root,args.image,args.char,args.threshold,args.dark_ink,args.box)
        elif c=='doctor':
            from importlib.metadata import version,PackageNotFoundError
            packages={}
            for n in ('fonttools','Pillow','freetype-py','uharfbuzz','numpy','shapely','scipy','scikit-image'):
                try:packages[n]=version(n)
                except PackageNotFoundError:packages[n]='not installed (may be optional)'
            result={'mfai':__version__,'python':platform.python_version(),'os':platform.system(),
                    'packages':packages,'actual_font_built':False,'target_engine_tested':False}
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except GateError as exc:
        print(str(exc),file=sys.stderr);return 2
    except (OSError,ValueError,KeyError,TypeError,AttributeError,RuntimeError) as exc:
        print(f'BLOCKED_{type(exc).__name__}: {exc}',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
