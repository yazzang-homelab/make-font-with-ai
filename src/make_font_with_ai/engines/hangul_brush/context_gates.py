#!/usr/bin/env python3
"""Actual-ink contextual gates. Not a typographic aesthetic-equivalence score."""
from __future__ import annotations
import io,json,copy,hashlib,argparse
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from fontTools.ttLib import TTFont
import freetype
from build_font import ROOT,Designs,to_glyph,place,serialize
from qa_v4 import bitmap
from shaping_support import target

def left_arm_bands(a):
    mask=a>96;h,w=mask.shape;out=[]
    for frac in (.16,.23,.30,.37):
        x=round(w*frac);p=mask[:,max(0,x-1):min(w,x+2)].mean(axis=1)>.45
        labs,_=ndi.label(p);lengths=np.bincount(labs)[1:]
        out.append(int(np.sum(lengths>=max(2,h*.04))))
    return out

def lower_return_x(a):
    mask=a>96;h,w=mask.shape;_,xs=np.where(mask[int(h*.70):])
    return float(xs.mean()/max(1,w-1)) if len(xs) else 0.

def crowded(meta):
    ctx=meta.get('context',[])
    return bool(ctx) and (ctx[1]!='V' or ctx[-1]!='none')

def inspect(data,m):
    f=TTFont(io.BytesIO(data));face=freetype.Face(io.BytesIO(data));rows=[];fail=[]
    used=set()
    for c in target():
        used.update(x.glyphName for x in f['glyf'][f.getBestCmap()[ord(c)]].components)
    for name,meta in m['parts'].items():
        if name not in used or meta['role']!='L' or meta['char'] not in ('ㄱ','ㅋ') or not crowded(meta):continue
        for size in (64,128):
            a=bitmap(face,f.getGlyphID(name),size);ch=meta['char'];stats={}
            if ch=='ㄱ':
                value=lower_return_x(a);stats['lower_return_x']=value
                ok=value>=.68 # lower return must predominantly stay in the right third
            else:
                values=left_arm_bands(a);stats['left_arm_bands']=values
                ok=sum(n==2 for n in values)>=3
            row={'part':name,'char':ch,'size':size,'pass':bool(ok),'context':meta['context'],**stats}
            rows.append(row)
            if not ok:fail.append(row)
    return {'pass':not fail,'cases':len(rows),'failures':fail},rows

def mutate(f,m,ch,outline):
    bad=copy.deepcopy(f)
    for name,meta in m['parts'].items():
        if meta['role']=='L' and meta['char']==ch and crowded(meta):
            g=to_glyph(place(outline,meta['box']));bad['glyf'][name]=g;g.recalcBounds(bad['glyf']);bad['hmtx'].metrics[name]=(1000,g.xMin)
    return serialize(bad)

def run(data,m,prior_bad=None):
    f=TTFont(io.BytesIO(data));d=Designs();baseline,details=inspect(data,m);controls=[]
    wrong=mutate(f,m,'ㄱ',d.giyeok_initial)
    r,_=inspect(wrong,m)
    controls.append({'name':'LONG_DIAGONAL_G_IN_CROWDED_SLOT','rejected':not r['pass'],'failed_cases':len(r['failures'])})
    from contextual_forms import ContextForms,signature
    from build_font import fit,unit
    forms=ContextForms(d,fit,unit)
    wrong=mutate(f,m,'ㅋ',forms.glyph('ㄱ','c','L',signature('L','ㄱ','ㅘ','ㄱ')))
    r,_=inspect(wrong,m)
    controls.append({'name':'KIEUK_REPLACED_BY_GIYEOK','rejected':not r['pass'],'failed_cases':len(r['failures'])})
    if prior_bad:
        p=Path(prior_bad);b=(p/'compiled.ttf').read_bytes();pm=json.loads((p/'manifest.json').read_text());r,_=inspect(b,pm)
        controls.append({'name':'R19_MERGED_KIEUK_REGRESSION','rejected':not r['pass'],'failed_cases':len(r['failures']),'font_sha256':hashlib.sha256(b).hexdigest()})
    # Compare internal design outlines before placement, normalizing both to unit boxes.
    # This quantifies actual allograph changes; it is not a legibility score.
    changes=[]
    for role,ch,kind,a,b in [
        ('L','ㄱ','c','가','각'),('L','ㄱ','c','가','곽'),('L','ㄷ','c','다','도'),
        ('V0','ㅏ','v','가','각'),('V0','ㅏ','v','각','감'),('V0','ㅏ','v','감','갈'),
        ('V0','ㅏ','v','각','악'),('V0','ㅐ','v','개','객'),('V0','ㅐ','v','객','갬'),
        ('V0','ㅗ','v','고','곡'),('T','ㄱ','c','각','곽'),('T','ㄱ','c','곡','국')]:
        from shaping_support import expected
        da=expected(a)[0];db=expected(b)[0]
        ga=unit(forms.glyph(ch,kind,role,signature(role,*da)))
        gb=unit(forms.glyph(ch,kind,role,signature(role,*db)))
        ratio=float(ga.symmetric_difference(gb).area/ga.union(gb).area)
        changes.append({'role':role,'jamo':ch,'syllables':a+b,'normalized_outline_difference':round(ratio,6),'not_just_affine_box_scaling':ratio>.001})
    pass_=baseline['pass'] and all(r['rejected'] for r in controls) and all(r['not_just_affine_box_scaling'] for r in changes)
    r={'pass':pass_,'font_sha256':hashlib.sha256(data).hexdigest(),'context_ink':baseline,'negative_controls':controls,'outline_changes':changes,'artistic_reference_quality_pass':False}
    return r,details

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--cache-dir',type=Path,required=True);ap.add_argument('--prior-bad',type=Path);ap.add_argument('--iteration',required=True);a=ap.parse_args()
    data=(a.cache_dir/'compiled.ttf').read_bytes();m=json.loads((a.cache_dir/'manifest.json').read_text());r,rows=run(data,m,a.prior_bad)
    p=ROOT/'reports'/a.iteration;p.mkdir(parents=True,exist_ok=True)
    for name,obj in [('context_gates.json',r),('context_ink_details.json',rows)]: (p/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2))
    print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r['pass'] else 1)
