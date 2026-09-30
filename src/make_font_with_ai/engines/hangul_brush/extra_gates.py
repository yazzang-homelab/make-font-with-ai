#!/usr/bin/env python3
"""Standalone jamo, whole-syllable minimal pairs, and an actual pixel negative.
No numeric gate is treated as reference-artwork equivalence.
"""
import io,copy,hashlib,json,unicodedata,collections
from pathlib import Path
import numpy as np
import freetype
from fontTools.ttLib import TTFont
from build_font import ROOT,build_font,serialize,Designs,to_glyph,place
from composite_qa import frame
from shaping_support import target,Shaper
from qa_v4 import bitmap,right_arm_bands,inspect_ink

def run(data,m):
 f=TTFont(io.BytesIO(data));cm=f.getBestCmap();face=freetype.Face(io.BytesIO(data));fails=[];jm=[]
 for cp in range(0x3131,0x3164):
  for sz in (32,64,128):
   a=bitmap(face,f.getGlyphID(cm[cp]),sz);s=inspect_ink(a)
   if s['ink_pixels']==0:fails.append(['jamo_blank',chr(cp),sz])
   if chr(cp) in 'ㅐㅒ' and sz>=64 and s['components']!=1:fails.append(['jamo_disconnected',chr(cp),sz])
   if chr(cp)=='ㅒ' and sz>=64 and s['holes']<1:fails.append(['jamo_yae_aperture_missing',chr(cp),sz])
   jm.append({'char':chr(cp),'size':sz,'ink':s})
 # Independently specified near-neighbor reading contrasts, on the final glyphs.
 v_pairs=[(0x1161,0x1162),(0x1162,0x1165),(0x1162,0x1166),(0x1163,0x1164),(0x1164,0x1168),(0x1165,0x1166),(0x1167,0x1168),(0x1169,0x116D),(0x116E,0x1172),(0x1169,0x116E)]
 l_pairs=[(0x1100,0x110F),(0x1103,0x1110),(0x1106,0x1111),(0x110B,0x1112),(0x1109,0x110C),(0x110C,0x110E)]
 chars=target();char_set=set(chars);pairs=set()
 for c in chars:
  ds=unicodedata.normalize('NFD',c)
  for pos,choices in [(0,l_pairs),(1,v_pairs)]:
   for a,b in choices:
    if ord(ds[pos]) not in (a,b):continue
    other=b if ord(ds[pos])==a else a
    alt=unicodedata.normalize('NFC',ds[:pos]+chr(other)+ds[pos+1:])
    if len(alt)==1 and alt in char_set:pairs.add(tuple(sorted((c,alt))))
 masks={c:frame(face,f.getGlyphID(cm[ord(c)]),64) for c in chars}
 pr=[]
 for a,b in sorted(pairs):
  x=masks[a].astype(np.int16);y=masks[b].astype(np.int16)
  difference=float(np.abs(x-y).sum()/255/64**2)
  # Exact pixel collapse is a hard failure; low contrast is only a review flag.
  if difference==0:fails.append(['minimal_pair_identical',a,b])
  pr.append({'pair':a+b,'difference_ink_per_em2':round(difference,6),'optical_review_flag':difference<.018})
 # Replace true ㅌ outlines by ㄷ, leaving mapping and component labels intact.
 bad=copy.deepcopy(f);d=Designs();targetparts=[]
 for name,meta in m['parts'].items():
  if meta['kind']=='c' and meta['char']=='ㅌ':
   g=to_glyph(place(d.c('ㄷ'),meta['box']));bad['glyf'][name]=g;g.recalcBounds(bad['glyf']);bad['hmtx'].metrics[name]=(1000,g.xMin);targetparts.append(name)
 bd=serialize(bad);bf=freetype.Face(io.BytesIO(bd));controls=[]
 for name in targetparts:
  for size in (64,128):
   counts=right_arm_bands(bitmap(bf,bad.getGlyphID(name),size));controls.append({'part':name,'size':size,'right_arm_bands':counts,'rejected':sum(x==3 for x in counts)<3})
 if not all(x['rejected'] for x in controls):fails.append(['tieut_mutation_escaped'])
 r={'font_sha256':hashlib.sha256(data).hexdigest(),'pass':not fails,'standalone_jamo_cases':len(jm),'minimal_pair_cases':len(pr),'minimal_pair_optical_flags':[x for x in pr if x['optical_review_flag']],'tieut_to_digeut_negative_cases':len(controls),'tieut_to_digeut_all_rejected':all(x['rejected'] for x in controls),'failures':fails,'artistic_reference_equivalence':False}
 return r,{'jamo':jm,'minimal_pairs':pr,'tieut_mutation':controls}
if __name__=='__main__':
 import sys
 f,m=build_font();r,details=run(serialize(f),m);out=ROOT/'reports'/sys.argv[1];out.mkdir(parents=True,exist_ok=True)
 (out/'extra_gates.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));(out/'extra_gate_details.json').write_text(json.dumps(details,ensure_ascii=False,indent=2))
 print(json.dumps(r,ensure_ascii=False,indent=2))
