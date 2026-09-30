#!/usr/bin/env python3
"""ㅢ lower-ㅡ aspect oracle measured on actual compiled ink; rejects R12."""
import io,json,hashlib,importlib.util
import numpy as np
from scipy import ndimage as ndi
import freetype
from fontTools.ttLib import TTFont
from build_font import ROOT,build_font,serialize
from composite_qa import frame
from qa_v4 import bitmap
from shaping_support import target

def aspect(a):
 y,x=np.nonzero(a>64)
 if not len(x):return 0.0
 return float((x.max()-x.min()+1)/(y.max()-y.min()+1))

def scan(data,m):
 f=TTFont(io.BytesIO(data));face=freetype.Face(io.BytesIO(data));cm=f.getBestCmap();names=set();n=0
 for c in target():
  if (ord(c)-0xAC00)//28%21==19:
   n+=1
   for comp in f['glyf'][cm[ord(c)]].components:
    meta=m['parts'][comp.glyphName]
    if meta['kind']=='v' and meta['char']=='ㅡ':names.add(comp.glyphName)
 rows=[]
 for size in (64,128):
  for name in sorted(names):
   ratio=aspect(bitmap(face,f.getGlyphID(name),size))
   rows.append({'kind':'composed_lower_eu','glyph':name,'size':size,'ratio':round(ratio,4),'pass':ratio>=3.0})
  for cp in (0x3162,0x1174):
   a=frame(face,f.getGlyphID(cm[cp]),size)
   # Identify the real disconnected strokes rather than a guessed x crop.
   # The font's standalone side bearing makes a fixed .60em crop include
   # the vertical stem's tail; that crop was an oracle error in R13.
   mask=a>64; labels,count=ndi.label(mask,np.ones((3,3)))
   strokes=[np.where(labels==k,a,0) for k in range(1,count+1) if (labels==k).sum()>=mask.sum()*.03]
   ratio=max((aspect(stroke) for stroke in strokes),default=0.0)
   rows.append({'kind':'standalone_ui_left_stroke','char':chr(cp),'size':size,'ratio':round(ratio,4),'pass':ratio>=3.0})
 return {'pass':all(x['pass'] for x in rows),'target_ui_syllables':n,'cases':len(rows),'observations':rows}

def run():
 f,m=build_font();data=serialize(f);pos=scan(data,m)
 spec=importlib.util.spec_from_file_location('r12_ui_negative',ROOT/'history/R12/build_font.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);old.ROOT=ROOT
 f0,m0=old.build_font();negative=scan(old.serialize(f0),m0)
 return {'font_sha256':hashlib.sha256(data).hexdigest(),'pass':pos['pass'] and not negative['pass'],'candidate':pos,'R12_rejected':not negative['pass'],'R12_observations':negative,'artistic_equivalence':False,'oracle_revision':'Connected-component stroke isolation replaces invalid fixed-x crop. Aspect threshold remains 3.0; no threshold relaxation.'}
if __name__=='__main__':
 import sys
 r=run();out=ROOT/'reports'/sys.argv[1];out.mkdir(parents=True,exist_ok=True);(out/'ui_horizontal_gate.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps(r,ensure_ascii=False,indent=2))
