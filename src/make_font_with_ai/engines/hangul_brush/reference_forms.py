"""Optical Hangul allographs, chosen from the ENTIRE syllable's context.
This changes stroke construction and internal proportions, not just glyph boxes.
Coordinates use a downward-positive 1000-unit design space.  No random jitter.
"""
from functools import lru_cache
import numpy as np
from shapely import affinity
from shapely.geometry import Polygon
from shapely.ops import unary_union, transform

VERTICAL=set('ㅏㅐㅑㅒㅓㅔㅕㅖㅣ')
HORIZONTAL=set('ㅗㅛㅜㅠㅡ')
PAIRED=set('ㅐㅔㅒㅖ')
MIXED={'ㅘ':('ㅗ','ㅏ'),'ㅙ':('ㅗ','ㅐ'),'ㅚ':('ㅗ','ㅣ'),
       'ㅝ':('ㅜ','ㅓ'),'ㅞ':('ㅜ','ㅔ'),'ㅟ':('ㅜ','ㅣ'),'ㅢ':('ㅡ','ㅣ')}
DOUBLE={'ㄲ':'ㄱㄱ','ㄸ':'ㄷㄷ','ㅃ':'ㅂㅂ','ㅆ':'ㅅㅅ','ㅉ':'ㅈㅈ'}
CLUSTER={'ㄳ':'ㄱㅅ','ㄵ':'ㄴㅈ','ㄶ':'ㄴㅎ','ㄺ':'ㄹㄱ','ㄻ':'ㄹㅁ',
         'ㄼ':'ㄹㅂ','ㄽ':'ㄹㅅ','ㄾ':'ㄹㅌ','ㄿ':'ㄹㅍ','ㅀ':'ㄹㅎ','ㅄ':'ㅂㅅ'}

def orientation(v):return 'V' if v in VERTICAL else 'H' if v in HORIZONTAL else 'M'
def lead_family(l):
    if l in DOUBLE:return 'double'
    if l=='ㅇ':return 'round'
    if l in 'ㅁㅂㅍㅎ':return 'closed'
    if l in 'ㅅㅈㅊ':return 'diagonal'
    if l in 'ㄱㅋ':return 'corner'
    return 'openbox'
def final_family(t):
    if not t.strip():return 'none'
    if t in CLUSTER or t in DOUBLE:return 'cluster'
    if t=='ㄹ':return 'rieul'
    if t in 'ㅁㅇㅂㅍㅎ':return 'counter'
    if t in 'ㅅㅈㅊ':return 'diagonal'
    return 'corner'

def layout(l,v,t):
    """Leading/vowel regions yield room to the actual trailing form.
    Long reference tails are NOT used to compute a whole-syllable scale.
    """
    has=bool(t.strip());o=orientation(v);lf=lead_family(l);tf=final_family(t)
    top_end=605 if tf!='rieul' else 590
    if has:
        if t=='ㄹ':tb=(35,620,940,370)
        elif t=='ㅇ':tb=(208,659,592,322)
        elif t=='ㅁ':tb=(166,650,670,338)
        elif tf=='cluster':tb=(60,650,870,338)
        elif tf=='diagonal':tb=(135,653,740,334)
        elif t in ('ㄱ','ㅋ'):tb=(148,640,800,348)
        else:tb=(145,650,725,338)
        # Mixed vowels have a heavy right stem; shift a narrow final a little left.
        if o=='M' and t in ('ㅇ','ㅁ'):
            x,y,w,h=tb;tb=(x-12,y,w,h)
    else:tb=None
    if o=='V':
        if has:
            if v in PAIRED:cb=(25,65,560,475);vb=(510,0,475,top_end)
            elif v=='ㅣ':cb=(35,60,600,485);vb=(700,0,255,top_end)
            else:cb=(25,65,550,470);vb=(565,0,420,top_end)
        else:
            if v in PAIRED:cb=(10,130,595,730);vb=(495,0,495,995)
            elif v=='ㅣ':cb=(35,140,600,730);vb=(690,0,280,995)
            else:cb=(10,140,580,730);vb=(555,0,435,995)
        if lf=='round':
            x,y,w,h=cb;cb=(x+w*.06,y+h*.05,w*.88,h*.88)
        if lf=='double':
            x,y,w,h=cb;cb=(x-5,y+h*.12,w+10,h*.78)
            # Double initials receive width; vowel's side branch gives back space.
            if v in ('ㅓ','ㅕ','ㅔ','ㅖ'):
                x,y,w,h=vb;vb=(x+10,y,w-10,h)
        return cb,[(v,vb)],tb
    if o=='H':
        if has:
            if v=='ㅡ':cb=(85,0,815,445);vb=(40,480,915,118)
            else:
                width=690 if lf=='round' else (820 if lf=='double' else 790)
                height=355 if v in ('ㅗ','ㅛ') else 390
                cb=((1000-width)/2-10,0,width,height)
                vb=(35,370 if v in ('ㅗ','ㅛ') else 385,925,top_end-(370 if v in ('ㅗ','ㅛ') else 385))
        else:
            width=715 if lf=='round' else 820
            if v=='ㅡ':cb=((1000-width)/2,0,width,705);vb=(35,790,930,185)
            elif v in ('ㅗ','ㅛ'):cb=((1000-width)/2,0,width,565);vb=(35,565,930,420)
            else:cb=((1000-width)/2,0,width,610);vb=(35,615,930,370)
        return cb,[(v,vb)],tb
    low,right=MIXED[v];paired=right in PAIRED
    rx=520 if paired else (690 if right=='ㅣ' else 610)
    rw=470 if paired else (280 if right=='ㅣ' else 375)
    if has:
        cb=(25,15,rx-55,340)
        lowb=(25,370,rx-30,top_end-370)
        if low=='ㅡ':cb=(25,10,rx-45,420);lowb=(25,472,rx-25,110)
        vbs=[(low,lowb),(right,(rx,0,rw,top_end))]
    else:
        cb=(20,75,rx-50,555)
        lowb=(20,615,rx-20,370)
        if low=='ㅡ':cb=(25,65,rx-35,670);lowb=(25,790,rx-25,170)
        vbs=[(low,lowb),(right,(rx,0,rw,995))]
    if lf=='round':
        x,y,w,h=cb;cb=(x+w*.04,y+h*.05,w*.91,h*.88)
    if lf=='double':
        x,y,w,h=cb;cb=(x,y+h*.045,w,h*.91)
    return cb,vbs,tb


def signature(role,l,v,t):
    # Cache only distinctions that affect actual outline construction.
    o=orientation(v);has=bool(t.strip())
    if role=='L':return (role,o,'_', '_','present' if has else 'none')
    if role=='T':return (role,o,'_', 'down' if v in ('ㅜ','ㅝ','ㅞ','ㅟ','ㅠ') else 'other',final_family(t))
    return (role,o,lead_family(l),'_',final_family(t))


def _warp(g,xsrc=None,xdst=None,ysrc=None,ydst=None,tailshift=0):
    """Strict monotone piecewise maps preserve bridges and counters."""
    def fn(x,y,z=None):
        xx=np.asarray(x,dtype=float);yy=np.asarray(y,dtype=float)
        if xsrc is not None:xx=np.interp(xx,xsrc,xdst)
        if ysrc is not None:yy=np.interp(yy,ysrc,ydst)
        if tailshift:xx=xx+tailshift*np.clip((yy-620)/380,0,1)**1.4
        return (xx,yy) if z is None else (xx,yy,z)
    return transform(fn,g).buffer(0)

class ContextForms:
    def __init__(self,d,fit,unit):self.d=d;self.fit=fit;self.unit=unit
    def union(self,*gs):return unary_union(gs).buffer(0)
    @lru_cache(None)
    def _h(self,flat):
        # Reduce the slope of cramped horizontal elements, retaining real brush edges.
        return self.unit(affinity.affine_transform(self.d.H,[1,0,.31 if flat else .06,1,0,0]))
    @lru_cache(None)
    def _i(self,short):
        if not short:return self.d.I
        return self.unit(_warp(self.d.I,ysrc=[0,580,820,1000],ydst=[0,650,875,1000],tailshift=80))
    @lru_cache(None)
    def glyph(self,ch,kind,role,key):
        _,o,lf,v,tf=key;has=tf!='none';crowded=(has or o!='V')
        fit=self.fit;unit=self.unit;U=self.union;I=self._i(crowded);H=self._h(o!='V')
        if kind=='c':
            if role=='L':
                if (ch in ('ㄱ','ㅋ') and crowded) or ch=='ㄲ':
                    # A real elbow and near-vertical return; not a clipped diagonal tail.
                    g=unit(U(fit(H,(0,0,1000,520 if o=='V' else 475)),
                             fit(I,(585,200,400,800))))
                    if ch=='ㅋ':
                        # Keep the two left-facing arms independent of the shared right spine.
                        g=unit(U(fit(H,(0,0,1000,300)),fit(H,(40,440,850,225)),fit(I,(585,120,400,880))))
                    if ch=='ㄲ':g=U(fit(g,(0,30,470,955)),fit(g,(535,0,465,1000)))
                    return g
                g=self.d.c(ch,'L')
                if o!='V':
                    # Redistribute internal bands under vertical compression.
                    if ch in ('ㄹ','ㅌ'):g=_warp(g,ysrc=[0,300,650,1000],ydst=[0,270,680,1000])
                    elif ch in ('ㄴ','ㄷ','ㄸ','ㅂ','ㅃ','ㅍ','ㅁ','ㅇ'):
                        g=_warp(g,ysrc=[0,240,760,1000],ydst=[0,210,790,1000])
                    elif ch=='ㅎ':g=_warp(g,ysrc=[0,225,435,1000],ydst=[0,180,375,1000])
                    elif ch in ('ㅅ','ㅆ','ㅈ','ㅉ','ㅊ','ㅋ'):
                        g=_warp(g,ysrc=[0,530,820,1000],ydst=[0,575,850,1000],tailshift=35 if o=='M' else 0)
                elif has:
                    if ch in ('ㄹ','ㅌ'):g=_warp(g,ysrc=[0,300,650,1000],ydst=[0,275,665,1000])
                    else:g=_warp(g,ysrc=[0,550,850,1000],ydst=[0,585,870,1000])
                return unit(g)
            g=self.d.c(ch,'T')
            if tf=='cluster':
                # Keep both members readable rather than compressing one shared box.
                seq=DOUBLE.get(ch) or CLUSTER.get(ch)
                if seq:
                    gs=[]
                    for i,cc in enumerate(seq):
                        q=self.d.c(cc,'TC')
                        if cc in 'ㄱㅋ':
                            q=unit(U(fit(H,(0,0,1000,435)),fit(I,(570,180,425,820))))
                        q=_warp(q,ysrc=[0,250,760,1000],ydst=[0,215,785,1000])
                        gs.append(fit(q,(i*535,25 if i==0 else 0,470 if i==0 else 465,970 if i==0 else 1000)))
                    return U(*gs)
            # Vowel direction changes bottom-stroke emphasis and counter headroom.
            if o=='M':g=_warp(g,ysrc=[0,300,700,1000],ydst=[0,260,725,1000],tailshift=18)
            elif o=='H':g=_warp(g,ysrc=[0,300,700,1000],ydst=[0,275,735,1000])
            if v=='down':g=_warp(g,xsrc=[0,300,700,1000],xdst=[0,275,735,1000])
            return unit(g)
        # Vertical vowel arms really move with the initial and final context.
        if ch in ('ㅐ','ㅒ'):
            g=self.d.v(ch)
            move=(-45 if has else 10)+(25 if lf in ('round','closed') else -15 if lf=='double' else 0)
            move+=-16 if tf in ('rieul','cluster') else 12 if tf=='counter' else 0
            return unit(_warp(g,ysrc=[0,300,580,820,1000],ydst=[0,300+move*.6,580+move,835 if has else 820,1000]))
        if ch=='ㅣ':return I
        if ch in ('ㅏ','ㅑ','ㅓ','ㅕ','ㅔ','ㅖ'):
            branch=365 if has else 405
            if lf in ('round','closed'):branch+=45
            elif lf in ('double','diagonal'):branch-=25
            if o=='M':branch+=25
            branch+=-18 if tf in ('rieul','cluster') else 14 if tf=='counter' else 0
            stems=630 if not has else 660
            thick=245 if not has else 215
            def simple_v(base):
                right=base in ('ㅏ','ㅑ');double=base in ('ㅑ','ㅕ')
                sx=0 if right else 1000-stems
                gs=[fit(I,(sx,0,stems,1000))]
                ay=[branch] if not double else [branch-135,branch+135]
                for yy in ay:
                    gs.append(fit(H,((stems*.52 if right else 0),yy,(1000-stems*.52 if right else 735),thick if not double else 183)))
                return unit(U(*gs))
            if ch in ('ㅔ','ㅖ'):
                vv=simple_v('ㅓ' if ch=='ㅔ' else 'ㅕ')
                return unit(U(fit(vv,(0,70 if has else 85,615,900 if has else 880)),fit(I,(685,0,315,1000))))
            return simple_v(ch)
        if ch=='ㅡ':return H
        if ch in ('ㅗ','ㅛ','ㅜ','ㅠ'):
            up=ch in ('ㅗ','ㅛ');double=ch in ('ㅛ','ㅠ')
            # The projection avoids the leading elbow or follows the final optical center.
            center=405 if lf=='corner' and up else 515 if lf in ('round','closed') else 460
            if o=='M':center-=35
            if tf=='cluster':center-=12
            elif tf=='counter':center+=12
            centers=[235,680] if double else [center]
            sw=275 if double else 295
            # A final-bearing horizontal vowel gets more projection space and a
            # thinner bar; this is an internal allograph, not box compression.
            bar_y=(585 if has else 535) if up else 0
            bar_h=(415 if has else 465) if up else (380 if has else 420)
            stem_y=0 if up else (230 if has else 255)
            stem_h=710 if up else (770 if has else 745)
            gs=[fit(H,(0,bar_y,1000,bar_h))]
            for cx in centers:
                gs.append(fit(I,(cx-sw/2,stem_y,sw,stem_h)))
            return unit(U(*gs))
        return self.d.v(ch)
