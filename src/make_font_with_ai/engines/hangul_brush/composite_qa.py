#!/usr/bin/env python3
"""Inspect the assembled glyph, not only separately correct component masters.
Numbers flag optical ambiguities for review; they are not an artistic oracle.
"""
import io,json,hashlib,collections
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from fontTools.ttLib import TTFont
import freetype
from build_font import ROOT,build_font,serialize
from shaping_support import target,expected
from qa_v4 import minimum_holes,inspect_ink

def frame(face,gid,size=128):
 face.set_pixel_sizes(0,size);face.load_glyph(gid,freetype.FT_LOAD_RENDER|freetype.FT_LOAD_NO_HINTING)
 b=face.glyph.bitmap;out=np.zeros((size*2,size*2),np.uint8)
 if b.rows and b.width:
  a=np.array(b.buffer,np.uint8).reshape(b.rows,abs(b.pitch))[:,:b.width]
  x=round(size*.25)+face.glyph.bitmap_left;y=round(size*1.15)-face.glyph.bitmap_top
  assert x>=0 and y>=0 and x+b.width<=size*2 and y+b.rows<=size*2
  out[y:y+b.rows,x:x+b.width]=a
 return out

def run(data,manifest):
 f=TTFont(io.BytesIO(data));face=freetype.Face(io.BytesIO(data));cm=f.getBestCmap();parts={};findings=[];rows=[]
 used={p.glyphName for c in target() for p in f['glyf'][cm[ord(c)]].components}
 for name in used:parts[name]=frame(face,f.getGlyphID(name))>96
 for c in target():
  n=cm[ord(c)];g=f['glyf'][n];masks=[parts[ch.glyphName] for ch in g.components]
  whole=frame(face,f.getGlyphID(n));mask=whole>96
  whole_holes=ndi.binary_fill_holes(mask)&~mask
  visible=[];retained=[]
  for i,ch in enumerate(g.components):
   pm=masks[i];others=np.zeros_like(pm)
   for j,q in enumerate(masks):
    if j!=i:others|=q
   vis=float(np.count_nonzero(pm&~others)/max(1,pm.sum()));visible.append(vis)
   holes=ndi.binary_fill_holes(pm)&~pm;labs,num=ndi.label(holes,np.ones((3,3)))
   kept=0
   for k in range(1,num+1):
    aperture=labs==k
    if aperture.sum()>=2 and np.count_nonzero(aperture&~mask)>=max(2,aperture.sum()*.35):kept+=1
   need=minimum_holes(manifest['parts'][ch.glyphName]['char'])
   retained.append({'part':ch.glyphName,'need':need,'kept':kept,'visible_ink_fraction':round(vis,4)})
   if vis<.25:findings.append({'char':c,'kind':'COMPONENT_MOSTLY_OCCLUDED','part':ch.glyphName,'visible':vis})
   if kept<need:findings.append({'char':c,'kind':'COUNTER_OCCLUDED_IN_SYLLABLE','part':ch.glyphName,'need':need,'kept':kept})
  rows.append({'char':c,'min_visible_ink':round(min(visible),4),'parts':retained})
 return {'font_sha256':hashlib.sha256(data).hexdigest(),'size':128,'syllables':2350,'pass':not findings,'findings':findings,'minimum_component_visible_ink':min(r['min_visible_ink'] for r in rows)},rows
if __name__=='__main__':
 import sys
 f,m=build_font();data=serialize(f);r,rows=run(data,m);out=ROOT/'reports'/sys.argv[1];out.mkdir(exist_ok=True,parents=True)
 (out/'composite_ink.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));(out/'composite_details.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
 print(json.dumps(r,ensure_ascii=False,indent=2))
