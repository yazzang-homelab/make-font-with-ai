"""Neighbour-aware optical spacing for the complete Hangul syllable.

Measure visible ink, not the font's bounding rectangle. A trimmed ink core is
used ONLY for layout measurement; it never replaces a brush outline. Bounded
moves keep the original stroke pressure and semantic component identities.
"""
from functools import lru_cache
import numpy as np
from shapely import contains_xy
from reference_forms import orientation, CLUSTER

GRID=112
U=(np.arange(GRID)+.5)/GRID
XX,YY=np.meshgrid(U*1000,U*1000)

class InkBalancer:
    def __init__(self,ctx):
        self.ctx=ctx
        self.records={}

    @lru_cache(None)
    def info(self,ch,kind,role,key):
        g=self.ctx.glyph(ch,kind,role,key)
        # Ignore detached flecks and hairline terminals for alignment only.
        core=g.buffer(-13).buffer(9)
        if core.is_empty:core=g
        mask=contains_xy(core,XX,YY)
        ys,xs=np.nonzero(mask)
        if len(xs)==0:raise ValueError('Empty optical measurement')
        a=mask.sum(axis=0);c=np.cumsum(a)/a.sum()
        qx=np.interp([.02,.98],c,U)*1000
        # Blend silhouette and mass; neither equates optical balance with COM.
        center=.52*float(U[xs].mean()*1000)+.48*float(qx.mean())
        edges={}
        for axis in (0,1):
            m=mask if axis==0 else mask.T
            lo=np.full(GRID,np.nan);hi=lo.copy()
            good=m.any(axis=0)
            lo[good]=U[m.argmax(axis=0)[good]]*1000
            hi[good]=U[GRID-1-m[::-1].argmax(axis=0)[good]]*1000
            edges[axis]=(lo,hi)
        return dict(center=center,area=float(g.area),cx=float(g.centroid.x),
                    qlo=float(qx[0]),qhi=float(qx[1]),edges=edges)

    def anchor(self,items):
        area=0.;moment=0.;lo=[];hi=[]
        for desc,b in items:
            inf=self.info(*desc);x,y,w,h=b
            aa=inf['area']*w*h/1e6
            area+=aa;moment+=aa*(x+w*inf['cx']/1000)
            lo.append(x+w*inf['qlo']/1000)
            hi.append(x+w*inf['qhi']/1000)
        return .52*moment/area+.48*(min(lo)+max(hi))/2

    def profile(self,item,coords,axis,high):
        desc,b=item;x,y,w,h=b
        off,scale=(x,w) if axis==0 else (y,h)
        t=(coords-off)/scale
        p=self.info(*desc)['edges'][axis][int(high)]
        val=np.interp(t,U,p,left=np.nan,right=np.nan)/1000
        return (y+h*val) if axis==0 else (x+w*val)

    def gap(self,left,right,axis):
        # axis 0: upper/lower vertical separation; 1: left/right separation
        xy=np.linspace(20,980,97)
        la=np.array([self.profile(i,xy,axis,True) for i in left])
        ra=np.array([self.profile(i,xy,axis,False) for i in right])
        valid=np.any(np.isfinite(la),axis=0)&np.any(np.isfinite(ra),axis=0)
        if valid.sum()<5:return None
        la=np.max(np.where(np.isfinite(la),la,-1e5),axis=0)
        ra=np.min(np.where(np.isfinite(ra),ra,1e5),axis=0)
        vals=ra[valid]-la[valid]
        return float(np.percentile(vals,5 if axis==0 else 12))

    @staticmethod
    def shift(items,dx=0,dy=0):
        for i in items:i[1][0]+=dx;i[1][1]+=dy

    def align(self,items,target=500,cap=65):
        lo=min(i[1][0] for i in items);hi=max(i[1][0]+i[1][2] for i in items)
        if hi-lo>956:
            factor=956/(hi-lo)
            for _,b in items:
                b[0]=22+(b[0]-lo)*factor;b[2]*=factor
            lo=22;hi=978
        delta=float(np.clip(target-self.anchor(items),-cap,cap))
        delta=float(np.clip(delta,18-lo,982-hi))
        self.shift(items,dx=delta)

    def adjust(self,l,v,t,cb,vbs,tb,signature):
        o=orientation(v);has=bool(t.strip())
        top=[[(l,'c','L',signature('L',l,v,t)),list(cb)]]
        top += [[(vc,'v','V'+str(j),signature('V'+str(j),l,v,t)),list(b)]
                for j,(vc,b) in enumerate(vbs)]
        bottom=[] if not has else [[(t,'c','T',signature('T',l,v,t)),list(tb)]]
        allitems=top+bottom
        # Reserve real side bearings before moving ink; pressure varies with
        # context masters, not arbitrary glyph-specific width normalization.
        for _,b in allitems:b[0]=500+(b[0]-500)*.955;b[2]*=.955
        if t=='ㄹ':
            b=bottom[0][1];b[1]-=12;b[3]+=12
        elif t in ('ㄺ','ㄻ','ㄼ','ㄽ','ㄾ','ㄿ','ㅀ'):
            # Three turns must survive in a narrow cluster's physical size.
            # Preserve the baseline while reserving a compact-master minimum.
            b=bottom[0][1];increase=max(0,395-b[3])
            b[1]-=increase;b[3]+=increase
        pre=dict(center=self.anchor(allitems),top=self.anchor(top),
                 bottom=self.anchor(bottom) if has else None,
                 final_gap=self.gap(top,bottom,0) if has else None)
        if o=='V':
            gap=self.gap(top[:1],top[1:],1)
            if gap is not None:
                dx=float(np.clip(30-gap,-42,55))
                self.shift(top[:1],dx=-dx*.40);self.shift(top[1:],dx=dx*.60)
        elif o=='M':
            # The leading body nests above the lower-vowel arm, then the
            # combined left group is spaced against the right stem.
            aim=self.anchor(top[1:2])
            self.shift(top[:1],dx=float(np.clip(aim-self.anchor(top[:1]),-30,30)))
            gap=self.gap(top[:2],top[2:],1)
            if gap is not None:
                dx=float(np.clip(27-gap,-34,40))
                self.shift(top[:2],dx=-dx*.4);self.shift(top[2:],dx=dx*.6)
        else:
            # Align the reading bodies along a common optical axis, while the
            # vowel stem can remain intentionally offset inside its own master.
            self.align(top[:1],500,65)
            self.align(top[1:],500,40)
        self.align(top,500,65)
        if has:
            # Open-right ㄴ is aligned primarily by silhouette. Other finals
            # include their native pressure distribution in the anchor.
            if t=='ㄴ':
                b=bottom[0][1];b[0]+=(500-(b[0]+b[2]*.5))*.65
            else:self.align(bottom,self.anchor(top),85)
            gap=self.gap(top,bottom,0)
            if gap is not None:
                b=bottom[0][1];base=b[1]+b[3]
                # Allocate otherwise empty roof space to the final. Its baseline
                # is fixed; do not just float the whole glyph upward.
                minimum=395 if t in ('ㄺ','ㄻ','ㄼ','ㄽ','ㄾ','ㄿ','ㅀ') else 405 if t=='ㄹ' else 295
                grow=float(np.clip(gap-49,-24,110))
                grow=min(grow,475-b[3])
                grow=max(grow,minimum-b[3])
                b[1]-=grow;b[3]+=grow
                remaining=self.gap(top,bottom,0)
                if remaining is not None and remaining>90 and o=='V':
                    # Raise the leading body's depth in very open final roofs.
                    lb=top[0][1]
                    extra=float(np.clip(remaining-82,0,58))
                    lb[3]+=extra
                # Small residual correction stays anchored to the same base.
                minimum=395 if t in ('ㄺ','ㄻ','ㄼ','ㄽ','ㄾ','ㄿ','ㅀ') else 405 if t=='ㄹ' else 295
                for _ in range(4):
                    gap2=self.gap(top,bottom,0)
                    if gap2 is None or gap2>=25:break
                    need=min(28-gap2,35)
                    shrink=min(need,max(0,b[3]-minimum))
                    b[1]+=shrink;b[3]-=shrink
                    if shrink<need:
                        # Give a compact three-bar final its needed roof space
                        # by slightly redistributing the upper group's depth.
                        height=max(z[1][1]+z[1][3] for z in top)
                        scale=max(.94,(height-(need-shrink))/height)
                        for _,bb in top:bb[1]*=scale;bb[3]*=scale
                if o=='H' and t=='ㅎ':
                    # The small ㅎ crown is not its optical roof: preserve the
                    # baseline while closing excessive whitespace above it.
                    b[1]-=18;b[3]+=18
                assert abs(b[1]+b[3]-base)<.01
        self.align(allitems,500,30)
        for _,b in allitems:
            b[:]=[round(z) for z in b]
        post=dict(center=self.anchor(allitems),top=self.anchor(top),
                  bottom=self.anchor(bottom) if has else None,
                  final_gap=self.gap(top,bottom,0) if has else None)
        self.records[l+v+t.strip()]={'before':pre,'after':post}
        return tuple(top[0][1]),[(it[0][0],tuple(it[1])) for it in top[1:]],(tuple(bottom[0][1]) if has else None)
