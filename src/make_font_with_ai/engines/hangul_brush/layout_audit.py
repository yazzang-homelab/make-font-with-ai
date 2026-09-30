"""Whole-glyph optical audit using compiled FreeType pixels.
This audits spacing and alignment, not artistic equivalence.
"""
import io,hashlib,json,unicodedata
import numpy as np
from scipy import ndimage as ndi
from fontTools.ttLib import TTFont
import freetype
from composite_qa import frame
from shaping_support import target

def core(a):
    m=a>96
    opened=ndi.binary_opening(m,np.array([[0,1,0],[1,1,1],[0,1,0]],bool))
    return opened if opened.any() else m

def center(m,size=128):
    y,x=np.nonzero(m)
    if not len(x):raise ValueError('Empty glyph core')
    c=np.cumsum(m.sum(axis=0));c=c/c[-1]
    lo,hi=np.interp([.02,.98],c,np.arange(m.shape[1])+.5)
    cx=.52*(x.mean()+.5)+.48*(lo+hi)/2
    return (cx-size*.25)*1000/size

def vertical_gap(a,b,size=128):
    good=a.any(axis=0)&b.any(axis=0)
    if good.sum()<4:return None
    bottom=a.shape[0]-1-a[::-1].argmax(axis=0)
    top=b.argmax(axis=0)
    return float(np.percentile((top-bottom-1)[good],20)*1000/size)


def facing_gap(upper,lower,size=128):
    previous=np.zeros_like(lower);previous[1:]=lower[:-1]
    edge=lower&~previous
    if not edge.any():return None
    dist=ndi.distance_transform_edt(~upper)
    return float(np.percentile(dist[edge],10)*1000/size)

def scan(data,chars=None):
    f=TTFont(io.BytesIO(data));cm=f.getBestCmap();face=freetype.Face(io.BytesIO(data));rows=[];fail=[]
    for c in (target() if chars is None else chars):
        g=f['glyf'][cm[ord(c)]]
        masks=[]
        for part in g.components:
            _,tr=part.getComponentInfo()
            if tr[:4]!=(1,0,0,1):raise ValueError('Unexpected non-translation component transform')
            a=frame(face,f.getGlyphID(part.glyphName))
            # FreeType resolves internal master transforms. Apply the outer
            # syllable component's translation too; mutation tests alter it.
            dx,dy=round(tr[4]*128/1000),round(-tr[5]*128/1000)
            if dx or dy:a=ndi.shift(a,(dy,dx),order=0,mode='constant',cval=0,prefilter=False)
            masks.append(core(a))
        whole=core(frame(face,f.getGlyphID(cm[ord(c)])))
        has=len(unicodedata.normalize('NFD',c))==3
        ct=center(whole);inkx=np.nonzero(whole)[1]
        r={'char':c,'center':round(ct,2),'center_error':round(abs(ct-500),2),
           'left_core':round((inkx.min()-32)*1000/128,2),
           'right_core':round((inkx.max()+1-32)*1000/128,2)}
        if has:
            up=np.logical_or.reduce(masks[:-1]);bt=masks[-1]
            r.update(top_center=round(center(up),2),final_center=round(center(bt),2),
                     axis_difference=round(abs(center(up)-center(bt)),2),
                     final_gap=facing_gap(up,bt),projected_gap_diagnostic=vertical_gap(up,bt))
        errors=[]
        if abs(ct-500)>65:errors.append('WHOLE_INK_LATERAL_BIAS')
        if has and r['axis_difference']>100:errors.append('UPPER_FINAL_AXIS_SPLIT')
        if has and r['final_gap'] is not None and r['final_gap']<4:errors.append('FINAL_FACING_INK_TOUCHES')
        if has and r['final_gap'] is not None and r['final_gap']>120:errors.append('FINAL_GROUP_TOO_DETACHED')
        r['failures']=errors;rows.append(r)
        if errors:fail.append(r)
    vec=lambda k:[r[k] for r in rows if k in r and r[k] is not None]
    quant=lambda k:{str(q):round(float(np.percentile(vec(k),q)),3) for q in [0,50,95,100]}
    return {'pass':not fail,'font_sha256':hashlib.sha256(data).hexdigest(),'syllables':len(rows),
            'whole_center_error_units':quant('center_error'),'upper_final_axis_units':quant('axis_difference'),
            'final_gap_units':quant('final_gap'),'failures':fail,'rows':rows,
            'limits':{'whole_bias':65,'upper_final_axes':100,'facing_ink_separation':[4,120]},
            'interpretation':'Flagging constraints only, not a guarantee of calligraphic quality.'}
if __name__=='__main__':
    import argparse
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('font');p.add_argument('out');a=p.parse_args()
    r=scan(Path(a.font).read_bytes());Path(a.out).write_text(json.dumps(r,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in r.items() if k not in ('rows','failures')},ensure_ascii=False));print('FAILURES',len(r['failures']))
