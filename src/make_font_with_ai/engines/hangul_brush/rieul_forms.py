"""R36 brush restoration: pressure-shaped final ㄹ with two open returns.
The old R28 readability skeleton is retained as a constraint, not as the outline.
Reference-derived edge fluctuations are placed on hand-shaped pressure contours.
No texture bitmap is substituted for a glyph, and no commercial outline is used.
"""
from functools import lru_cache
import numpy as np
from scipy.ndimage import gaussian_filter1d
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union

CLUSTERS={'ㄺ':'ㄱ','ㄻ':'ㅁ','ㄼ':'ㅂ','ㄽ':'ㅅ','ㄾ':'ㅌ','ㄿ':'ㅍ','ㅀ':'ㅎ'}

class RieulForms:
    def __init__(self,ctx):
        self.ctx=ctx
        # Actual reference edges; macro pressure is separately designed.
        xs=np.linspace(90,900,181)
        traces=[]
        for x in xs:
            s=ctx.d.H.intersection(LineString([(x,-200),(x,1200)]))
            traces.append([s.bounds[1],s.bounds[3]] if not s.is_empty else [0,0])
        traces=np.asarray(traces)
        self.edge=(traces-gaussian_filter1d(traces,4.2,axis=0))/65.
        self.edge=np.clip(self.edge,-1.35,1.35)

    def stroke(self,xs,ys,widths,phase=0,bristles=False):
        u=np.linspace(0,1,181)
        nodes=np.linspace(0,1,len(xs))
        x=np.interp(u,nodes,xs);cy=np.interp(u,nodes,ys)
        ww=np.interp(u,np.linspace(0,1,len(widths)),widths)
        e=np.roll(self.edge,phase,axis=0)
        # Independent edges preserve thick-to-thin pressure rather than equal bars.
        top=cy-ww*.5+e[:,0]*15
        bot=cy+ww*.5+e[:,1]*13
        pts=list(zip(x,top))+list(zip(x[::-1],bot[::-1]))
        g=Polygon(pts).buffer(0)
        if bristles:
            # Fine directional separations confined to the final release tip.
            cuts=[
              Polygon([(x[-1]-210,cy[-1]-15),(x[-1]+8,cy[-1]+5),
                       (x[-1]+8,cy[-1]+12),(x[-1]-65,cy[-1]-1)]),
              Polygon([(x[-1]-148,cy[-1]+18),(x[-1]+4,cy[-1]+15),
                       (x[-1]+4,cy[-1]+23),(x[-1]-40,cy[-1]+23)])]
            g=g.difference(unary_union(cuts)).buffer(0)
        return g

    def joint(self,x0,y0,x1,y1,w0,w1):
        # Broad-nib descending turn with asymmetric pressure.
        dx=x1-x0;dy=y1-y0
        pts=[(x0-w0*.44,y0-30),(x0+w0*.52,y0-35),
             (x0+dx*.55+w0*.44,y0+dy*.5),
             (x1+w1*.48,y1+30),(x1-w1*.57,y1+35),
             (x0+dx*.4-w0*.53,y0+dy*.44)]
        return Polygon(pts).buffer(0)

    @lru_cache(None)
    def master(self,o,cluster=False,down=False):
        from reference_forms import _warp
        # Preserve actual native brush pressure and dry edges. Reallocate the
        # reading body separately from the final release; no equal-width bars.
        g=self.ctx.d.rieul_final
        xdst=[0,315,790,946,1000] if cluster else [0,305,765,935,1000]
        g=_warp(g,xsrc=[0,220,550,780,1000],xdst=xdst)
        # Native pressure-shaped return strokes move the hinges outward.
        # This frees two actual open counters without replacing the outside
        # pressure curve by three regular parallel bars.
        I=self.ctx._i(True)
        turns=[self.ctx.fit(I,(655 if cluster else 675,45,240 if cluster else 185,420)),
               self.ctx.fit(I,(125,425,185,555))]
        g=unary_union([g,*turns]).buffer(0)
        upper=self.stroke([-80,155,345,540,701,758],
                          [507,402,309,226,166,147],
                          [z*(1.25 if cluster else 1) for z in [122,136,138,133,119,8]],27)
        lower=self.stroke([238,292,435,650,870,1075],
                          [694,672,623,570,562,632],
                          [z*(1.06 if cluster else 1) for z in [8,126,139,135,123,76]],71)
        g=g.difference(unary_union([upper,lower])).buffer(0)
        # Remove tiny detached dust and pinholes, not brush-edge slots.
        polys=[]
        for pp in (list(g.geoms) if hasattr(g,'geoms') else [g]):
            if not isinstance(pp,Polygon) or pp.area<1100:continue
            holes=[]  # ㄹ has open channels; isolated pinholes are not structural counters.
            polys.append(Polygon(pp.exterior.coords,holes))
        g=unary_union(polys).buffer(0)
        if o=='H':
            from shapely import affinity
            g=affinity.affine_transform(g,[1,0,.045,1,0,0])
        return self.ctx.unit(g)

    @lru_cache(None)
    def glyph(self,ch,key):
        _,o,lf,v,tf=key
        if ch=='ㄹ':return self.master(o,False,v=='down')
        other=CLUSTERS[ch]
        left=self.master(o,True,v=='down')
        from reference_forms import _warp
        fit=self.ctx.fit;unit=self.ctx.unit;U=self.ctx.union
        H=self.ctx._h(o!='V');I=self.ctx._i(True)
        right=self.ctx.d.c(other,'TC')
        if other in 'ㄱㅋ':right=unit(U(fit(H,(0,0,1000,435)),fit(I,(570,180,425,820))))
        right=_warp(right,ysrc=[0,250,760,1000],ydst=[0,215,785,1000])
        return U(fit(left,(0,25,470,970)),fit(right,(535,0,465,1000)))
