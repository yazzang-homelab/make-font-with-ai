#!/usr/bin/env python3
"""Jaechulgyeok Ink V6: uniform modern-Hangul composition; no logo overrides.
Builds from reference brush contour seeds, not an existing typeface.
Default builds in memory; --candidate-output explicitly writes a test file. Python 3.10+.
"""
from __future__ import annotations
import argparse, io, json, hashlib
from pathlib import Path
from functools import lru_cache
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from shapely import affinity
from shapely.geometry import Polygon, GeometryCollection, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from contextual_forms import ContextForms,layout,signature
from optical_balance import InkBalancer

ROOT=Path(__file__).resolve().parent
UPM=1000
VERSION='0.636'
INITIALS='ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'
VOWELS='ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'
FINALS=' ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ'
DOUBLE={'ㄲ':'ㄱㄱ','ㄸ':'ㄷㄷ','ㅃ':'ㅂㅂ','ㅆ':'ㅅㅅ','ㅉ':'ㅈㅈ'}
CLUSTER={'ㄳ':'ㄱㅅ','ㄵ':'ㄴㅈ','ㄶ':'ㄴㅎ','ㄺ':'ㄹㄱ','ㄻ':'ㄹㅁ','ㄼ':'ㄹㅂ','ㄽ':'ㄹㅅ','ㄾ':'ㄹㅌ','ㄿ':'ㄹㅍ','ㅀ':'ㄹㅎ','ㅄ':'ㅂㅅ'}
MIXED={'ㅘ':('ㅗ','ㅏ'),'ㅙ':('ㅗ','ㅐ'),'ㅚ':('ㅗ','ㅣ'),'ㅝ':('ㅜ','ㅓ'),'ㅞ':('ㅜ','ㅔ'),'ㅟ':('ㅜ','ㅣ'),'ㅢ':('ㅡ','ㅣ')}
VERTICAL=set('ㅏㅐㅑㅒㅓㅔㅕㅖㅣ'); HORIZONTAL=set('ㅗㅛㅜㅠㅡ'); PAIRED=set('ㅐㅔㅒㅖ')


def polygons(g):
    if isinstance(g,Polygon):
        if g.area>1: yield g
    elif hasattr(g,'geoms'):
        for p in g.geoms: yield from polygons(p)


def decode(rs): return unary_union([Polygon(r['outer'],r.get('holes',[])).buffer(0) for r in rs])
def unit(g):
    x,y,xx,yy=g.bounds
    if xx<=x or yy<=y: raise ValueError('Empty brush seed')
    return affinity.affine_transform(g,[1000/(xx-x),0,0,1000/(yy-y),-1000*x/(xx-x),-1000*y/(yy-y)])
def place(g,b):
    x,y,w,h=b
    return affinity.affine_transform(g,[w/1000,0,0,h/1000,x,y])
def fit(g,b): return place(unit(g),b)
def union(*gs): return unary_union(gs).buffer(0)
def gn(cp): return f'uni{cp:04X}'


class Designs:
    """Reference-first jamo masters; topology of ㅐ/ㅒ is not synthesized as spaced letters."""
    def __init__(self):
        raw=json.loads((ROOT/'artwork/reference_contours.json').read_text(encoding='utf-8'))
        C={ch:unit(decode(v)) for ch,v in raw['consonants'].items()}
        V={ch:unit(decode(v)) for ch,v in raw['vowels'].items()}
        R={key:unit(decode(value)) for key,value in raw['additional_raw'].items()}
        I=R['stroke_vertical'];H=R['stroke_horizontal']
        # Restore the connected, two-stem original ㅐ, rather than ㅏ plus a detached ㅣ.
        V['ㅐ']=R['V_ae']
        # ㅒ requires TWO continuous bridges. Build and union into a single vowel master.
        a1=fit(I,(35,90,465,850));a2=fit(I,(550,0,450,1000))
        bridge1=fit(H,(240,285,540,185));bridge2=fit(H,(200,520,565,205))
        V['ㅒ']=unit(union(a1,a2,bridge1,bridge2))
        # Trace the energetic open ㄹ from 출, retaining its long brush exit.
        self.rieul_final=R['C_rieul']
        self.giyeok_initial=R['C_giyeok_initial']
        C['ㄹ']=C['ㄹ']
        V['ㅜ']=unit(union(fit(H,(0,0,1000,480)),fit(I,(360,255,340,745))))
        V['ㅠ']=unit(union(fit(H,(0,0,1000,465)),fit(I,(160,260,285,740)),fit(I,(605,215,285,780))))
        V['ㅗ']=unit(union(fit(I,(380,0,295,650)),fit(H,(0,480,1000,520))))
        V['ㅛ']=unit(union(fit(I,(160,20,275,640)),fit(I,(590,0,275,650)),fit(H,(0,480,1000,520))))
        # Use lower-title weight consistently, not a thin top-line stem next to fat ㅐ.
        V['ㅣ']=I
        V['ㅏ']=unit(union(fit(I,(0,0,630,1000)),fit(H,(335,380,665,255))))
        V['ㅓ']=unit(union(fit(I,(360,0,640,1000)),fit(H,(0,380,750,255))))
        V['ㅑ']=unit(union(fit(I,(0,0,620,1000)),fit(H,(330,255,670,205)),fit(H,(300,505,700,205))))
        V['ㅕ']=unit(union(fit(I,(370,0,630,1000)),fit(H,(50,260,730,205)),fit(H,(0,515,765,205))))
        for ch,base in [('ㅔ','ㅓ'),('ㅖ','ㅕ')]:
            V[ch]=unit(union(fit(V[base],(0,80,615,880)),fit(I,(670,0,330,1000))))
        # Match the heavy stroke family in letters absent from the nine-letter reference.
        C['ㄴ']=unit(union(fit(I,(-40,0,465,965)),fit(H,(10,555,1000,445))))
        C['ㅂ']=unit(union(fit(I,(-30,0,470,1000)),fit(I,(530,-10,470,990)),fit(H,(170,315,710,315)),fit(H,(90,660,910,340))))
        C['ㅌ']=unit(union(fit(I,(-30,40,410,930)),fit(C['ㄷ'].intersection(box(-10,-10,1010,440)),(0,0,1000,300)),fit(H,(150,350,805,240)),fit(C['ㄷ'].intersection(box(-10,490,1010,1010)),(35,690,960,315))))
        C['ㄹ']=unit(union(fit(H,(0,0,940,320)),fit(I,(605,25,420,440)),fit(H,(75,350,855,285)),fit(I,(0,415,445,550)),fit(H,(20,695,985,325))))
        # A visible short brush mark distinguishes ㅎ from an accidental ㅇ.
        C['ㅎ']=unit(union(fit(I,(385,0,270,225)),fit(H,(55,210,915,240)),fit(C['ㅇ'],(155,435,730,565))))
        C['ㅍ']=unit(union(fit(C['ㅁ'],(135,85,730,830)),fit(H,(0,0,1000,245)),fit(H,(-20,710,1040,295))))
        # Moderate counter opening: V3's blanket 1.5 expansion thinned the reference ink.
        for ch in ('ㅁ','ㅇ'):
            g=C[ch];holes=[]
            for poly in polygons(g):
                for ring in poly.interiors:
                    h=Polygon(ring)
                    if h.area>10000:holes.append(affinity.scale(h,xfact=1.12,yfact=1.12,origin='centroid'))
            if holes:C[ch]=g.difference(unary_union(holes)).buffer(0)
        self.cs=C;self.vs=V;self.I=I;self.H=H
        self.raw=raw
    @lru_cache(None)
    def c(self,ch,role='L'):
        if ch=='ㄹ' and role=='T':return self.rieul_final
        if ch=='ㄱ' and role=='L':return self.giyeok_initial
        if ch in self.cs:return self.cs[ch]
        seq=DOUBLE.get(ch) or CLUSTER.get(ch)
        if not seq:raise ValueError('Unknown consonant '+ch)
        # Optical unequal placement is deliberate; do not squeeze the full syllable afterwards.
        child_role='TC' if ch in CLUSTER else role
        left=self.c(seq[0],child_role);right=self.c(seq[1],child_role)
        # Doubled diagonal consonants need a contextual heavier master. Squeezing
        # the single ㅅ/ㅈ twice creates needle-thin strokes, unlike the reference.
        if ch in ('ㅆ','ㅉ') or (ch=='ㄲ' and role=='L'):
            def heavy(g):
                return unit(union(g,affinity.translate(g,xoff=-105),affinity.translate(g,xoff=105)))
            left=heavy(left);right=heavy(right)
        if ch=='ㅃ':
            def heavier_b(g):
                return unit(union(g,affinity.translate(g,xoff=-42),affinity.translate(g,xoff=42)))
            left=heavier_b(left);right=heavier_b(right)
        return union(place(left,(0,30,475,960)),place(right,(540,0,460,1000)))
    @lru_cache(None)
    def v(self,ch):
        if ch in self.vs:return self.vs[ch]
        a,b=MIXED[ch]
        # ㅢ has a horizontal ㅡ, not the full-height low ㅗ/ㅜ region.
        # Stretching ㅡ to 435 high turned it into a diagonal lump in R12.
        lower=(0,800,610,115) if a=='ㅡ' else (0,565,610,435)
        return union(place(self.v(a),lower),place(self.v(b),(610,0,390,1000)))


def to_glyph(g):
    g=affinity.affine_transform(g,[1,0,0,-1,0,900])
    pen=TTGlyphPen(None)
    for p in polygons(g):
        p=orient(p,sign=-1)
        for ring in [p.exterior,*p.interiors]:
            pts=[]
            for x,y in list(ring.coords)[:-1]:
                xy=(round(x),round(y))
                if not pts or xy!=pts[-1]:pts.append(xy)
            if len(set(pts))<3:continue
            pen.moveTo(pts[0])
            for xy in pts[1:]:pen.lineTo(xy)
            pen.closePath()
    return pen.glyph()


def build_font(subset=None):
    d=Designs();ctx=ContextForms(d,fit,unit);balancer=InkBalancer(ctx);glyphs={};metrics={};cmap={};cache={};master_cache={};manifest={};parts_meta={}
    def simple(n,g,adv=1000):
        gl=to_glyph(g);glyphs[n]=gl;gl.recalcBounds(glyphs);metrics[n]=(adv,getattr(gl,'xMin',0))
    def composite(n,children,adv=1000):
        pen=TTGlyphPen(glyphs)
        for child in children:pen.addComponent(child,(1,0,0,1,0,0))
        gl=pen.glyph();glyphs[n]=gl;gl.recalcBounds(glyphs);metrics[n]=(adv,getattr(gl,'xMin',0))
    def part(ch,b,kind,role,key):
        cachekey=(kind,ch,tuple(b),role,key)
        if cachekey not in cache:
            name=f'p{len(cache):05d}_{role}_{ord(ch):04X}'
            source=ctx.glyph(ch,kind,role,key)
            x,y,w,h=b
            mkey=(kind,ch,w,h,role,key)
            if mkey not in master_cache:
                base_name=f'm{len(master_cache):05d}_{role}_{ord(ch):04X}'
                simple(base_name,place(source,(0,0,w,h)))
                master_cache[mkey]=base_name
            pen=TTGlyphPen(glyphs)
            pen.addComponent(master_cache[mkey],(1,0,0,1,int(x),-int(y)))
            gl=pen.glyph();glyphs[name]=gl;gl.recalcBounds(glyphs)
            metrics[name]=(1000,getattr(gl,'xMin',0));cache[cachekey]=name
            parts_meta[name]={'char':ch,'kind':kind,'role':role,'box':list(b),'context':list(key)}
        return cache[cachekey]
    simple('.notdef',Polygon([(80,100),(920,100),(920,850),(80,850)], [[(170,190),(170,760),(830,760),(830,190)]]))
    simple('space',GeometryCollection(),350);cmap[32]=cmap[0xA0]='space'
    simple('ideographicspace',GeometryCollection());cmap[0x3000]='ideographicspace'
    for li,l in enumerate(INITIALS):
        for vi,v in enumerate(VOWELS):
            for ti,t in enumerate(FINALS):
                cp=0xAC00+(li*21+vi)*28+ti;name=gn(cp)
                if subset is not None and chr(cp) not in subset:continue
                cb,vbs,tb=layout(l,v,t)
                cb,vbs,tb=balancer.adjust(l,v,t,cb,vbs,tb,signature)
                children=[part(l,cb,'c','L',signature('L',l,v,t))]+[part(vc,vb,'v','V'+str(i),signature('V'+str(i),l,v,t)) for i,(vc,vb) in enumerate(vbs)]
                if ti:children.append(part(t,tb,'c','T',signature('T',l,v,t)))
                composite(name,children);cmap[cp]=name
                manifest[str(cp)]={'char':chr(cp),'decomposition':[l,v,t.strip()],'children':children}
    for cp in range(0x3131,0x3164):
        ch=chr(cp)
        if ch in VOWELS:
            b=(80,350,840,310) if ch in HORIZONTAL else ((390,0,220,950) if ch=='ㅣ' else (155,0,690,950))
            src=d.v(ch)
        else:
            b=(80,60,840,830)
            src=ctx.glyph(ch,'c','L',signature('L',ch,'ㅏ','')) if ch=='ㄲ' else d.c(ch)
        simple(gn(cp),place(src,b));cmap[cp]=gn(cp)
    for start,chs in [(0x1100,INITIALS),(0x1161,VOWELS),(0x11A8,FINALS[1:])]:
        for i,ch in enumerate(chs):
            cp=start+i;composite(gn(cp),[gn(ord(ch))]);cmap[cp]=gn(cp)
    for cp in [0x115F,0x1160,0x3164,0xFEFF,0x200C,0x200D]:
        simple(gn(cp),GeometryCollection(),1000 if cp==0x3164 else 0);cmap[cp]=gn(cp)
    # A minimal, clearly separate punctuation set. Latin/digits deliberately fall back.
    for ch in '.,!?-:':
        if ch in '.,:':
            gs=[Polygon([(200,810),(290,790),(295,890),(195,900)])]
            if ch==',':gs.append(Polygon([(245,850),(290,880),(195,970),(175,940)]))
            if ch==':':gs.append(Polygon([(200,350),(290,330),(295,430),(195,440)]))
        elif ch=='-':gs=[Polygon([(65,450),(730,405),(730,490),(60,550)])]
        elif ch=='!':gs=[Polygon([(220,40),(345,20),(290,680),(240,720),(200,670)]),Polygon([(200,810),(290,790),(295,890),(195,900)])]
        else:gs=[Polygon([(40,240),(100,80),(380,30),(520,130),(510,330),(295,550),(275,700),(205,700),(205,510),(380,290),(390,170),(150,160),(110,295)]),Polygon([(200,810),(290,790),(295,890),(195,900)])]
        simple(gn(ord(ch)),union(*gs),800 if ch=='-' else 580);cmap[ord(ch)]=gn(ord(ch))
    fb=FontBuilder(UPM,isTTF=True)
    fb.setupGlyphOrder(list(glyphs));fb.setupCharacterMap(cmap);fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics);fb.setupHorizontalHeader(ascent=1040,descent=-200,lineGap=0)
    fb.setupNameTable({'familyName':'Jaechulgyeok Ink BrushBalance R36','styleName':'Regular','uniqueFontIdentifier':'JaechulgyeokInkBrushBalanceR36-Regular-'+VERSION,'fullName':'Jaechulgyeok Ink BrushBalance R36 Regular','psName':'JaechulgyeokInkBrushBalanceR36-Regular','version':'Version '+VERSION,'description':'Reference-ink optical Hangul candidate. Semantic and artistic review are separate release gates. Monochrome.'})
    fb.setupOS2(version=4,sTypoAscender=1040,sTypoDescender=-200,sTypoLineGap=0,usWinAscent=1040,usWinDescent=200,usWeightClass=900,fsType=0,fsSelection=0xC0)
    fb.setupPost(underlinePosition=-130,underlineThickness=45)
    for nid,text in [(1,'재출격 잉크 브러시밸런스 R36'),(2,'레귤러'),(4,'재출격 잉크 브러시밸런스 R36 레귤러')]:fb.font['name'].setName(text,nid,3,1,0x0412)
    fb.font['head'].created=fb.font['head'].modified=3873484800;fb.font.recalcTimestamp=False
    fea=['languagesystem DFLT dflt;','languagesystem hang dflt;','lookup ComposeLV useExtension {']
    for li in range(19):
        for vi in range(21):
            cp=0xAC00+(li*21+vi)*28
            if cp in cmap:fea.append(f'sub {gn(0x1100+li)} {gn(0x1161+vi)} by {gn(cp)};')
    fea.append('} ComposeLV;')
    for li in range(19):
        fea.append(f'lookup ComposeLVT{li} useExtension {{')
        for vi in range(21):
            cp=0xAC00+(li*21+vi)*28
            for ti in range(1,28):
                if cp in cmap and cp+ti in cmap:fea.append(f'sub {gn(cp)} {gn(0x11A7+ti)} by {gn(cp+ti)};')
        fea.append(f'}} ComposeLVT{li};')
    fea+=['feature ccmp {','lookup ComposeLV;']+[f'lookup ComposeLVT{i};' for i in range(19)]+['} ccmp;']
    if subset is None:addOpenTypeFeaturesFromString(fb.font,'\n'.join(fea))
    fb.setupMaxp()
    return fb.font, {'syllables':manifest,'parts':parts_meta,'version':VERSION,'logo_overrides':False,'balance_measurements':balancer.records}


def serialize(f):
    s=io.BytesIO();f.save(s);return s.getvalue()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidate-output',type=Path,help='Explicit opt-in: write an UNRELEASED test candidate on this machine.')
    a=ap.parse_args();font,manifest=build_font();data=serialize(font)
    TTFont(io.BytesIO(data))
    print('CANDIDATE_NOT_ARTISTICALLY_ACCEPTED',VERSION,hashlib.sha256(data).hexdigest())
    if a.candidate_output:
        a.candidate_output.parent.mkdir(parents=True,exist_ok=True);a.candidate_output.write_bytes(data)
        print('UNRELEASED_TEST_FONT',a.candidate_output)
if __name__=='__main__':main()
