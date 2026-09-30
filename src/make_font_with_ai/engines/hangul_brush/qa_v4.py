#!/usr/bin/env python3
"""V4: functional gates are NOT an artistic quality oracle.
The ㅐ/ㅒ oracle tests actual raster connectivity, not the name of a component.
"""
from __future__ import annotations
import argparse,hashlib,io,json,unicodedata,collections
from pathlib import Path
import numpy as np
import freetype
from scipy import ndimage as ndi
from fontTools.ttLib import TTFont
from PIL import Image,ImageDraw,ImageFont
from build_font import ROOT,build_font,serialize
from shaping_support import target,expected,Shaper

HOLES={'ㅁ':1,'ㅇ':1,'ㅂ':1,'ㅍ':1,'ㅎ':1,'ㅒ':1}
SEQUENCES={'ㄲ':'ㄱㄱ','ㄸ':'ㄷㄷ','ㅃ':'ㅂㅂ','ㅆ':'ㅅㅅ','ㅉ':'ㅈㅈ','ㄳ':'ㄱㅅ','ㄵ':'ㄴㅈ','ㄶ':'ㄴㅎ','ㄺ':'ㄹㄱ','ㄻ':'ㄹㅁ','ㄼ':'ㄹㅂ','ㄽ':'ㄹㅅ','ㄾ':'ㄹㅌ','ㄿ':'ㄹㅍ','ㅀ':'ㄹㅎ','ㅄ':'ㅂㅅ'}
def minimum_holes(c):return sum(HOLES.get(x,0) for x in SEQUENCES.get(c,c))

def bitmap(face,gid,size):
    face.set_pixel_sizes(0,size)
    face.load_glyph(gid,freetype.FT_LOAD_RENDER|freetype.FT_LOAD_NO_HINTING)
    b=face.glyph.bitmap
    if not b.rows or not b.width:return np.zeros((1,1),dtype=np.uint8)
    return np.array(b.buffer,dtype=np.uint8).reshape(b.rows,abs(b.pitch))[:,:b.width]

def inspect_ink(a):
    mask=np.pad(a>96,3)
    lab,n=ndi.label(mask,np.ones((3,3)))
    sizes=np.bincount(lab.ravel())[1:];cut=max(3,float(mask.sum())*.018)
    components=int(np.sum(sizes>=cut))
    holes=ndi.binary_fill_holes(mask)&~mask
    h,nh=ndi.label(holes,np.ones((3,3)));areas=sorted([int(x) for x in np.bincount(h.ravel())[1:] if x>=2],reverse=True)
    # One-pixel erosion is a stability stress test, not the base semantic oracle.
    eroded=ndi.binary_erosion(mask)
    ll,nn=ndi.label(eroded,np.ones((3,3)));ss=np.bincount(ll.ravel())[1:]
    robust=int(np.sum(ss>=max(3,float(eroded.sum())*.04)))
    return {'components':components,'holes':len(areas),'hole_areas':areas,'erosion_components':robust,'ink_pixels':int(mask.sum())}

def right_arm_bands(a):
    """Right-facing arms distinguish ㅌ from a visually collapsed ㄷ.
    Probe four columns away from the shared spine; ignore one-pixel bristles.
    """
    mask=a>96;h,w=mask.shape;counts=[]
    for frac in (.60,.67,.74,.81):
        x=round(w*frac);profile=mask[:,max(0,x-1):min(w,x+2)].mean(axis=1)>.45
        labels,_=ndi.label(profile);lengths=np.bincount(labels)[1:]
        counts.append(int(np.sum(lengths>=max(2,h*.035))))
    return counts

def run(data,manifest,*,full=True,shape=True):
    chars=target();f=TTFont(io.BytesIO(data));cm=f.getBestCmap();gs=f['glyf'];met=f['hmtx'].metrics
    failures=collections.defaultdict(list);case_rows=[];parts_used={};rows=[]
    def fail(g,x):failures[g].append(x)
    allchars=''.join(chr(cp) for cp in range(0xAC00,0xD7A4)) if full else chars
    for c in allchars:
        n=cm.get(ord(c))
        if not n:fail('coverage',c);continue
        if n!=f'uni{ord(c):04X}':fail('wrong_mapping',c)
        g=gs[n];g.recalcBounds(gs)
        if g.numberOfContours==0:fail('empty',c);continue
        if met[n][0]!=1000:fail('advance',{'char':c,'advance':met[n][0]})
        if met[n][1]!=g.xMin:fail('side_bearing',c)
        if not (-5<=g.xMin<g.xMax<=1010 and -120<=g.yMin<g.yMax<=930):fail('bounds',{'char':c,'box':[g.xMin,g.yMin,g.xMax,g.yMax]})
        if not g.isComposite():fail('composition',c);continue
        roles=[]
        for child in g.components:
            meta=manifest['parts'].get(child.glyphName)
            if meta is None:fail('part_identity',c);continue
            roles.append((meta['role'],meta['char']))
            if c in chars:parts_used.setdefault(child.glyphName,[]).append(c)
            if child.getComponentInfo()[1]!=(1,0,0,1,0,0):fail('part_transform',c)
        d,e=expected(c)
        if roles!=e:fail('decomposition',{'char':c,'actual':roles,'expected':e})
        if c in chars:rows.append({'char':c,'codepoint':f'U+{ord(c):04X}','advance':met[n][0],'box':[g.xMin,g.yMin,g.xMax,g.yMax]})
    if 'GSUB' not in f:fail('shaping_table','missing')
    if f['hhea'].ascent!=f['OS/2'].sTypoAscender or f['hhea'].descent!=f['OS/2'].sTypoDescender:fail('line_metrics','inconsistent')
    face=freetype.Face(io.BytesIO(data));connected_cases=collections.Counter();counter_cases=0
    for part,users in parts_used.items():
        ch=manifest['parts'][part]['char'];kind=manifest['parts'][part]['kind'];gid=f.getGlyphID(part)
        for size in (64,128):
            a=bitmap(face,gid,size);rr=inspect_ink(a);why=[]
            if kind=='c' and ch=='ㅌ':
                rr['right_arm_bands']=right_arm_bands(a)
                if sum(x==3 for x in rr['right_arm_bands'])<3:why.append('TIEUT_COLLAPSED_TOWARD_DIGEUT')
            if kind=='v' and ch in ('ㅐ','ㅒ'):
                connected_cases[ch]+=len(users)
                if rr['components']!=1:why.append('DISCONNECTED_BRIDGE')
                if rr['erosion_components']!=1:why.append('FRAGILE_BRIDGE')
                if ch=='ㅒ' and not rr['holes']:why.append('SECOND_BRIDGE_OR_COUNTER_MISSING')
            if kind=='v' and ch in ('ㅔ','ㅖ') and rr['components']!=2:
                why.append('E_VOWEL_STEMS_OR_BRANCHES_INVALID')
            need=minimum_holes(ch)
            if need:
                counter_cases+=len(users)
                if rr['holes']<need:why.append('SEMANTIC_COUNTER_COLLAPSED')
            rec={'part':part,'char':ch,'role':manifest['parts'][part]['role'],'size':size,'occurrences':len(users),'stats':rr,'failures':why}
            case_rows.append(rec)
            if why:fail('ink_semantics',dict(rec,affected_characters=''.join(users)))
    raster={}
    for size in (32,64,128):
        hashes={};dens=[]
        for c in chars:
            a=bitmap(face,f.getGlyphID(cm[ord(c)]),size)
            if not np.any(a):fail('raster_blank',{'char':c,'size':size})
            h=hashlib.sha256(str(a.shape).encode()+a.tobytes()).hexdigest()
            if h in hashes and size>=64:fail('raster_duplicate',{'chars':[hashes[h],c],'size':size})
            hashes[h]=c;dens.append(float(a.sum()/255/(size*size)))
        raster[str(size)]={'cases':2350,'unique_bitmaps':len(hashes),'ink_area_range':[min(dens),max(dens)]}
    shape_cases=0
    if shape:
        shaper=Shaper(data)
        try:
            for c in allchars:
                x=shaper.shape(c);y=shaper.shape(unicodedata.normalize('NFD',c));shape_cases+=1
                if x!=y or len(x)!=1 or x[0][0]!=f.getGlyphID(cm[ord(c)]):fail('nfc_nfd',c)
        finally:shaper.close()
    report={'functional_pass':not failures,'artistic_reference_quality_pass':False,'font_sha256':hashlib.sha256(data).hexdigest(),'characters_checked':len(allchars),'ksx1001_checked':2350,'part_raster_cases':len(case_rows),'ae_yae_syllable_cases_by_two_sizes':dict(connected_cases),'counter_syllable_cases':counter_cases,'raster':raster,'nfc_nfd_cases':shape_cases,'failures':dict(failures),'failure_counts':{k:len(v) for k,v in failures.items()},'important':'Structural/raster/topology PASS does not authorize artistic release.'}
    return report,case_rows,rows

def main():
    p=argparse.ArgumentParser();p.add_argument('--iteration',required=True);p.add_argument('--no-shaping',action='store_true');a=p.parse_args()
    f,m=build_font();data=serialize(f);r,parts,metrics=run(data,m,shape=not a.no_shaping)
    out=ROOT/'reports'/a.iteration;out.mkdir(parents=True,exist_ok=True)
    for n,obj in [('functional.json',r),('part_ink_semantics.json',parts),('2350_metrics.json',metrics)]:
        (out/n).write_text(json.dumps(obj,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in r.items() if k!='failures'},ensure_ascii=False,indent=2))
    return r
if __name__=='__main__':
    result=main()
    raise SystemExit(0 if result['functional_pass'] else 1)
