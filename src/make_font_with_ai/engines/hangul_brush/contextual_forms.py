"""V6 optical allocation.
Public commercial specimens inform proportions, NOT source contours.
R22's own brush masters remain in reference_forms; no licensed font is imported.
"""
from functools import lru_cache
from reference_forms import (ContextForms as BaseForms, layout as base_layout,
                            orientation,lead_family,MIXED,DOUBLE,CLUSTER,VERTICAL,
                            HORIZONTAL,PAIRED,_warp)

def final_family(t):
    if not t.strip():return 'none'
    if t=='ㄴ':return 'open_right'
    if t in CLUSTER or t in DOUBLE:return 'cluster'
    if t=='ㄹ':return 'rieul'
    if t in 'ㅁㅇㅂㅍㅎ':return 'counter'
    if t in 'ㅅㅈㅊ':return 'diagonal'
    return 'corner'

def branch_family(v):
    if v in ('ㅓ','ㅔ','ㅕ','ㅖ'):return 'left'
    if v in ('ㅏ','ㅐ','ㅑ','ㅒ'):return 'right'
    if v in ('ㅗ','ㅛ','ㅘ','ㅙ','ㅚ'):return 'up'
    if v in ('ㅜ','ㅠ','ㅝ','ㅞ','ㅟ'):return 'down'
    return 'neutral'

def signature(role,l,v,t):
    o=orientation(v);tf=final_family(t)
    if role=='L':return role,o,lead_family(l),branch_family(v),tf
    if role=='T':return role,o,'_',branch_family(v),tf
    return role,o,lead_family(l),branch_family(v),tf

def layout(l,v,t):
    """Allocate around the final's actual occupied roof, not just its presence."""
    cb,vbs,tb=base_layout(l,v,t)
    has=bool(t.strip());o=orientation(v);tf=final_family(t);lf=lead_family(l)
    if not has:return cb,vbs,tb
    if tf=='open_right':tb=(130,682,720,305)
    elif tf=='rieul':tb=(125,608,770,382) if o=='V' else (105,610,790,380) if o=='H' else (120,614,785,376)
    if o=='V':
        x,y,w,h=cb
        # More bowl room over an open ㄴ; a crowded ㄹ/cluster needs a compact body.
        if tf=='open_right':cb=(x,y-8,w,h+34)
        elif tf in ('rieul','cluster'):cb=(x,y+3,w,h-10)
        # A left-facing vowel branch competes with the initial's descending diagonal.
        if branch_family(v)=='left' and lf in ('diagonal','double'):
            x,y,w,h=cb;cb=(x-5,y,w-28,h)
        end=710 if tf=='open_right' else 585 if tf in ('rieul','cluster') else 615
        vc,b=vbs[0];x,y,w,h=b;vbs=[(vc,(x,y,w,end-y))]
    elif o=='H':
        # Body height is an optical constraint; tails do not dictate it.
        width=625 if l=='ㅇ' else 690 if l=='ㅁ' else 715 if lf=='closed' else 780 if lf=='double' else 735
        x=(1000-width)/2-8
        if v=='ㅡ':cb=(x,0,width,495);vb=(40,530,915,95)
        elif v in ('ㅗ','ㅛ'):cb=(x,0,width,410);vb=(35,420,925,205)
        else:cb=(x,0,width,445);vb=(35,455,925,170)
        if tf=='rieul':
            x,y,w,h=cb;cb=(x,y,w,h-28)
            x,y,w,h=vb;vb=(x,y-28,w,h-8)
        vbs=[(v,vb)]
    else:
        x,y,w,h=cb
        if MIXED[v][0]!='ㅡ':
            cb=(x,y,w,h+30)
            low,b=vbs[0];bx,by,bw,bh=b;vbs[0]=(low,(bx,by+22,bw,620-(by+22)))
        # Only the right stem enters ㄴ's open corner; never push the entire low vowel down.
        vr,b=vbs[1];bx,by,bw,bh=b
        end=700 if tf=='open_right' else 595 if tf in ('rieul','cluster') else 625
        vbs[1]=(vr,(bx,by,bw,end-by))
        if tf=='rieul':
            low,b=vbs[0];x,y,w,h=b;vbs[0]=(low,(x,y-12,w,h-13))
    return cb,vbs,tb

class ContextForms(BaseForms):
    def __init__(self,*a,**k):
        super().__init__(*a,**k)
        from rieul_forms import RieulForms
        self.rieul=RieulForms(self)

    @lru_cache(None)
    def glyph(self,ch,kind,role,key):
        _,o,lf,v,tf=key
        if kind=='c' and role=='T' and ch in ('ㄹ','ㄺ','ㄻ','ㄼ','ㄽ','ㄾ','ㄿ','ㅀ'):
            return self.rieul.glyph(ch,key)
        old_tf='corner' if tf=='open_right' else tf
        old_key=(role,o,lf,'down' if v=='down' else '_',old_tf)
        g=super().glyph(ch,kind,role,old_key)
        if kind=='c' and role=='L' and ch=='ㄲ':
            # Two return strokes need their own weight, not two shrunken single ㄱ.
            fit=self.fit;U=self.union;unit=self.unit
            I=self._i(tf!='none' or o!='V');H=self._h(o!='V')
            elbow=unit(U(fit(H,(0,0,1000,480 if o=='V' else 435)),fit(I,(410,170,575,830))))
            g=U(fit(elbow,(0,30,470,955)),fit(elbow,(535,0,465,1000)))
        if tf=='none':return g
        if kind=='c' and role=='L':
            # Different counter/cap anchors are selected for different final roofs.
            # Maps are monotone, retaining connectedness and the source's dry-brush edges.
            if tf=='open_right':dst=[0,218,690,895,1000]
            elif tf in ('rieul','cluster'):dst=[0,265,630,838,1000]
            elif tf=='counter':dst=[0,230,665,870,1000]
            else:dst=[0,242,650,856,1000]
            g=_warp(g,ysrc=[0,250,650,850,1000],ydst=dst)
            if v=='left' and lf in ('diagonal','double'):
                # Give the outer diagonal a little more weight without moving its terminal into the vowel.
                g=_warp(g,xsrc=[0,550,820,1000],xdst=[0,575,845,1000])
            return self.unit(g)
        if kind=='v' and ch in VERTICAL:
            if tf=='open_right':dst=[0,540,875,1000]
            elif tf in ('rieul','cluster'):dst=[0,625,845,1000]
            elif tf=='counter':dst=[0,590,865,1000]
            else:dst=[0,610,860,1000]
            # The branch remains near the initial body while the stem length changes.
            return self.unit(_warp(g,ysrc=[0,620,860,1000],ydst=dst))
        if role=='T' and ch=='ㄹ' and o in ('H','M'):
            # Preserve, but shorten the long terminal's share of the total width.
            return self.unit(_warp(g,xsrc=[0,500,760,1000],xdst=[0,580,815,1000]))
        return g
