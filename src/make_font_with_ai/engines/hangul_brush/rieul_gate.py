"""Targeted rendered-ink oracle for ㄹ: three bars AND alternating returns.
This is a readability regression constraint, not an aesthetic equivalence score.
Independent of master names/cache labels. All tests inspect compiled glyph ink.
"""
import io,hashlib,json,unicodedata,collections,argparse
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from fontTools.ttLib import TTFont
import freetype
from qa_v4 import bitmap,inspect_ink
from shaping_support import target

FINAL_RIEUL=set('ᆯᆰᆱᆲᆳᆴᆵᆶ')

def affected(text):
    return ''.join(c for c in text if len(d:=unicodedata.normalize('NFD',c))==3 and d[-1] in FINAL_RIEUL)

def runs(v):
    a=np.r_[False,v,False].astype(np.int8);d=np.diff(a)
    return [(int(s),int(e)) for s,e in zip(np.flatnonzero(d==1),np.flatnonzero(d==-1))]

def inspect(a,cluster=False):
    mask=a>96
    if cluster:
        occupied=mask.any(axis=0);w=mask.shape[1]
        gaps=[(s,e) for s,e in runs(~occupied) if s>w*.3 and e<w*.7 and e-s>=max(1,w*.03)]
        if not gaps:return {'pass':False,'reasons':['CLUSTER_NO_MEMBER_GAP']}
        s,e=min(gaps,key=lambda se:abs((se[0]+se[1])/2-w*.5));mask=mask[:,:s]
    ys,xs=np.nonzero(mask)
    if len(xs)==0:return {'pass':False,'reasons':['EMPTY_RIEUL']}
    mask=mask[ys.min():ys.max()+1,xs.min():xs.max()+1];h,w=mask.shape
    structure=inspect_ink(mask.astype(np.uint8)*255)
    probes=[]
    for frac in (.30,.37,.44,.51,.58,.65):
        x=min(w-1,round(w*frac));rs=[(s,e) for s,e in runs(mask[:,x]) if e-s>=max(1,h*.04)]
        if len(rs)==3:
            probes.append({'x':x,'bands':rs,'gaps':[rs[1][0]-rs[0][1],rs[2][0]-rs[1][1]]})
    reason=[]
    if len(probes)<4:reason.append('THREE_BARS_NOT_RESOLVED')
    if structure['components']!=1:reason.append('RETURN_DISCONNECTED')
    # Peripheral dry-brush channels can alias into tiny lower-edge pinholes.
    # They are not one of ㄹ's two main open counters. Main/upper cavities,
    # including a wrongly closed upper return, remain hard failures.
    hh=ndi.binary_fill_holes(mask)&~mask
    hl,hn=ndi.label(hh,np.ones((3,3)));structural_holes=0;texture_pinholes=0
    for hid in range(1,hn+1):
        yy,xxh=np.nonzero(hl==hid);area=len(yy)
        if area<2:continue
        if (yy.mean()>=h*.75 or xxh.mean()<w*.27 or xxh.mean()>w*.73) and area<=max(2,mask.sum()*.025):
            texture_pinholes+=1
        else:structural_holes+=1
    if structural_holes:reason.append('OPEN_COUNTER_CLOSED')
    out={'ink_box_px':[w,h],'three_bar_probes':len(probes),'components':structure['components'],'holes':structure['holes'],'structural_holes':structural_holes,'peripheral_texture_pinholes':texture_pinholes}
    if len(probes)>=4:
        # Fit the two negative-space centerlines from observed central runs.
        xx=np.asarray([p['x'] for p in probes]);gaps=[];features=[]
        for k in (0,1):
            cy=np.asarray([(p['bands'][k][1]+p['bands'][k+1][0]-1)/2 for p in probes])
            coef=np.polyfit(xx,cy,1)
            scan=np.asarray([mask[int(np.clip(round(np.polyval(coef,x)),0,h-1)),x] for x in range(w)])
            left=scan[max(0,round(w*.075)):max(1,round(w*.265))]
            right=scan[round(w*.70):max(round(w*.70)+1,round(w*.91))]
            value={'left_ink_fraction':float(left.mean()),'right_ink_fraction':float(right.mean()),'min_gap_px':min(p['gaps'][k] for p in probes)}
            features.append(value);gaps.append(value['min_gap_px'])
        if features[0]['left_ink_fraction']>.35 or features[0]['right_ink_fraction']<.30:reason.append('UPPER_RETURN_NOT_RIGHT')
        if features[1]['left_ink_fraction']<.30 or features[1]['right_ink_fraction']>.35:reason.append('LOWER_RETURN_NOT_LEFT')
        if min(gaps)<max(1,int(h*.055)):reason.append('GAPS_COLLAPSED')
        out['negative_space']=features
    out.update(pass_=not reason,reasons=reason)
    out['pass']=out.pop('pass_')
    return out

def run(data,manifest=None,sizes=(32,64,128)):
    f=TTFont(io.BytesIO(data));cm=f.getBestCmap();face=freetype.Face(io.BytesIO(data));chars=affected(target())
    records=[];fails=[];unique={};counts=collections.Counter()
    for c in chars:
        n=cm[ord(c)];g=f['glyf'][n];cluster=unicodedata.normalize('NFD',c)[-1]!='ᆯ'
        if not g.isComposite():fails.append({'char':c,'reason':'NOT_COMPOSITE'});continue
        part=g.components[-1].glyphName;counts['cluster' if cluster else 'single']+=1
        for size in sizes:
            key=(part,size,cluster)
            if key not in unique:unique[key]=inspect(bitmap(face,f.getGlyphID(part),size),cluster)
            rr=unique[key];row={'char':c,'codepoint':f'U+{ord(c):04X}','part':part,'size':size,'cluster':cluster,**rr};records.append(row)
            if not rr['pass']:fails.append(row)
    return {'pass':not fails,'font_sha256':hashlib.sha256(data).hexdigest(),'affected_syllables':len(chars),'single_final':counts['single'],'cluster_final':counts['cluster'],'raster_cases':len(records),'unique_form_size_cases':len(unique),'failures':fails,'failure_counts':dict(collections.Counter(r for f in fails for r in f.get('reasons',[f.get('reason','UNKNOWN')]))),'rows':records}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--font',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=run(a.font.read_bytes());a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in r.items() if k not in ('rows','failures')},ensure_ascii=False,indent=2));raise SystemExit(0 if r['pass'] else 1)
