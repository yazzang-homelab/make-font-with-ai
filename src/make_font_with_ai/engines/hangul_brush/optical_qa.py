"""Checks compiled contours against frozen optical constraints, independent of selector keys.
These are targeted design constraints, NOT an artistic-equivalence classifier.
"""
from __future__ import annotations
import io,json,hashlib,unicodedata,argparse
from pathlib import Path
import numpy as np
from fontTools.ttLib import TTFont
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import affinity
from shaping_support import target

PAIRS=[('L','민','밀'),('L','민','밈'),('L','만','말'),('L','만','맘'),
       ('V','민','밀'),('V','빈','빌'),('V','긴','길'),('V','인','일')]
STEMS=[('민','밀'),('만','말'),('빈','빌'),('간','갈'),('인','일'),('관','괄')]

def child(f,c,role):
    name=f.getBestCmap()[ord(c)];g=f['glyf'][name]
    if not g.isComposite():raise ValueError('Not a composite: '+c)
    index=0 if role=='L' else -1 if role=='T' else (2 if unicodedata.normalize('NFD',c)[1] in 'ᅪᅫᅬᅯᅰᅱᅴ' else 1)
    return g.components[index].glyphName

def bounds(f,name):
    g=f['glyf'][name];g.recalcBounds(f['glyf']);return g.xMin,g.yMin,g.xMax,g.yMax

def geometry(f,name,normalize=True):
    coords,ends,_=f['glyf'][name].getCoordinates(f['glyf']);coords=np.asarray(coords,float)
    outer=[];holes=[];start=0
    for end in ends:
        ring=coords[start:end+1];start=end+1
        if len(ring)<3:continue
        signed=float(np.sum(ring[:,0]*np.roll(ring[:,1],-1)-np.roll(ring[:,0],-1)*ring[:,1]))
        p=Polygon(ring).buffer(0)
        (outer if signed<0 else holes).append(p)
    g=unary_union(outer).difference(unary_union(holes)).buffer(0)
    if normalize:
        x,y,xx,yy=g.bounds;g=affinity.affine_transform(g,[1000/(xx-x),0,0,1000/(yy-y),-1000*x/(xx-x),-1000*y/(yy-y)])
    return g

def run(data):
    f=TTFont(io.BytesIO(data));failures=[];ratios=[];stems=[];changes=[]
    # Actual initial ink box; no dependence on the builder's cached context names.
    for c in target():
        ds=unicodedata.normalize('NFD',c)
        if len(ds)==3 and ds[0] in ('ᄆ','ᄋ') and ds[1] in 'ᅩᅭᅮᅲᅳ':
            x,y,xx,yy=bounds(f,child(f,c,'L'));ratio=(xx-x)/(yy-y)
            r={'char':c,'ratio':round(ratio,6),'pass':ratio<=1.85};ratios.append(r)
            if not r['pass']:failures.append({'gate':'G03_BODY_ASPECT',**r})
    for a,b in STEMS:
        low_a=900-bounds(f,child(f,a,'V'))[1];low_b=900-bounds(f,child(f,b,'V'))[1]
        r={'pair':a+b,'open_right_bottom':low_a,'crowded_bottom':low_b,'difference':low_a-low_b,'pass':low_a-low_b>=40};stems.append(r)
        if not r['pass']:failures.append({'gate':'G02_OPEN_RIGHT_STEM',**r})
    for role,a,b in PAIRS:
        ga=geometry(f,child(f,a,role));gb=geometry(f,child(f,b,role))
        difference=ga.symmetric_difference(gb).area/ga.union(gb).area
        boxes=[bounds(f,child(f,c,role)) for c in (a,b)]
        # Integer compilation and bbox normalization can produce nonzero differences
        # for the SAME master. Exclude a 3-original-grid-unit uncertainty band.
        eps=max(3000/min(x2-x1,y2-y1) for x1,y1,x2,y2 in boxes)
        novelty=(ga.difference(gb.buffer(eps)).area+gb.difference(ga.buffer(eps)).area)/ga.union(gb).area
        r={'role':role,'pair':a+b,'normalized_ink_difference':round(difference,6),'outside_rounding_band_difference':round(novelty,6),'rounding_band':round(eps,4),'pass':difference>.006 and novelty>.002};changes.append(r)
        if not r['pass']:failures.append({'gate':'G04_COMPILED_ALLOGRAPH',**r})
    return {'pass':not failures,'font_sha256':hashlib.sha256(data).hexdigest(),'body_aspect_cases':len(ratios),'body_aspect_max':max(r['ratio'] for r in ratios),'stem_cases':stems,'allograph_cases':changes,'failures':failures,'body_aspect_details':ratios,'artistic_equivalence':False}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--cache',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    r=run((a.cache/'compiled.ttf').read_bytes());a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in r.items() if k!='body_aspect_details'},ensure_ascii=False,indent=2));raise SystemExit(0 if r['pass'] else 1)
