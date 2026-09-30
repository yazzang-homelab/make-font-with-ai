#!/usr/bin/env python3
"""Independent font gates. Never infer legibility solely from cmap coverage."""
from __future__ import annotations
import io, json, hashlib, unicodedata, ctypes as C, ctypes.util, platform, statistics
from pathlib import Path
from collections import Counter, defaultdict
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont, features
ROOT=Path(__file__).resolve().parent
# Independently stated Unicode modern jamo correspondence, not imported from builder.
L='ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'
V='ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'
T='ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ'
MIX={'ㅘ':('ㅗ','ㅏ'),'ㅙ':('ㅗ','ㅐ'),'ㅚ':('ㅗ','ㅣ'),'ㅝ':('ㅜ','ㅓ'),'ㅞ':('ㅜ','ㅔ'),'ㅟ':('ㅜ','ㅣ'),'ㅢ':('ㅡ','ㅣ')}

def target():
    # Decode the actual 25x94 KS X 1001 syllable rows; avoid cp949 extension confusion.
    chars=''.join(bytes([a,b]).decode('euc_kr') for a in range(0xB0,0xC9) for b in range(0xA1,0xFF))
    assert len(chars)==len(set(chars))==2350
    fixture=(ROOT/'tests/ksx1001_2350.txt').read_text(encoding='utf-8')
    assert fixture==chars, 'KS X 1001 fixture was changed'
    return chars

def expected(ch):
    ds=unicodedata.normalize('NFD',ch)
    l=L[ord(ds[0])-0x1100];v=V[ord(ds[1])-0x1161]
    t=T[ord(ds[2])-0x11A8] if len(ds)==3 else ''
    expected_parts=[('L',l)]+[('V'+str(i),x) for i,x in enumerate(MIX.get(v,(v,)))]+([('T',t)] if t else [])
    return [l,v,t], expected_parts

def ghash(g,gs):
    coords,ends,flags=g.getCoordinates(gs)
    return hashlib.sha256(json.dumps([list(map(list,coords)),list(ends),list(flags)],separators=(',',':')).encode()).hexdigest()

class Info(C.Structure):
    _fields_=[('codepoint',C.c_uint32),('mask',C.c_uint32),('cluster',C.c_uint32),('var1',C.c_uint32),('var2',C.c_uint32)]
class Pos(C.Structure):
    _fields_=[('x_advance',C.c_int32),('y_advance',C.c_int32),('x_offset',C.c_int32),('y_offset',C.c_int32),('var',C.c_uint32)]
class Shaper:
    def __init__(self,data):
        lib=ctypes.util.find_library('harfbuzz')
        self.pyhb=None
        if not lib:
            try: import uharfbuzz as hb
            except ImportError as e: raise RuntimeError('Install uharfbuzz; no shaping engine available') from e
            self.pyhb=hb; self.pyfont=hb.Font(hb.Face(data)); self.pyfont.scale=(1000,1000)
            self.version=hb.version_string(); return
        self.hb=C.CDLL(lib)
        sig={'hb_blob_create':([C.c_void_p,C.c_uint,C.c_int,C.c_void_p,C.c_void_p],C.c_void_p),'hb_face_create':([C.c_void_p,C.c_uint],C.c_void_p),'hb_font_create':([C.c_void_p],C.c_void_p),'hb_ot_font_set_funcs':([C.c_void_p],None),'hb_font_set_scale':([C.c_void_p,C.c_int,C.c_int],None),'hb_buffer_create':([],C.c_void_p),'hb_buffer_reset':([C.c_void_p],None),'hb_buffer_add_utf8':([C.c_void_p,C.c_char_p,C.c_int,C.c_uint,C.c_int],None),'hb_buffer_guess_segment_properties':([C.c_void_p],None),'hb_shape':([C.c_void_p,C.c_void_p,C.c_void_p,C.c_uint],None),'hb_buffer_get_glyph_infos':([C.c_void_p,C.POINTER(C.c_uint)],C.POINTER(Info)),'hb_buffer_get_glyph_positions':([C.c_void_p,C.POINTER(C.c_uint)],C.POINTER(Pos)),'hb_version_string':([],C.c_char_p)}
        for k,(a,r) in sig.items():fn=getattr(self.hb,k);fn.argtypes=a;fn.restype=r
        for kind in ('buffer','font','face','blob'):
            fn=getattr(self.hb,'hb_'+kind+'_destroy');fn.argtypes=[C.c_void_p];fn.restype=None
        self.data=C.create_string_buffer(data);h=self.hb
        self.blob=h.hb_blob_create(self.data,len(data),0,None,None);self.face=h.hb_face_create(self.blob,0);self.font=h.hb_font_create(self.face)
        h.hb_ot_font_set_funcs(self.font);h.hb_font_set_scale(self.font,1000,1000);self.buf=h.hb_buffer_create()
        self.version=h.hb_version_string().decode()
    def shape(self,text):
        if self.pyhb is not None:
            b=self.pyhb.Buffer();b.add_str(text);b.guess_segment_properties();self.pyhb.shape(self.pyfont,b)
            return [(i.codepoint,p.x_advance,p.y_advance,p.x_offset,p.y_offset) for i,p in zip(b.glyph_infos,b.glyph_positions)]
        h=self.hb;h.hb_buffer_reset(self.buf);b=text.encode('utf-8');h.hb_buffer_add_utf8(self.buf,b,len(b),0,len(b));h.hb_buffer_guess_segment_properties(self.buf);h.hb_shape(self.font,self.buf,None,0)
        n=C.c_uint();p=h.hb_buffer_get_glyph_infos(self.buf,C.byref(n));q=h.hb_buffer_get_glyph_positions(self.buf,C.byref(n))
        return [(p[i].codepoint,q[i].x_advance,q[i].y_advance,q[i].x_offset,q[i].y_offset) for i in range(n.value)]
    def close(self):
        if self.pyhb is not None:return
        h=self.hb;h.hb_buffer_destroy(self.buf);h.hb_font_destroy(self.font);h.hb_face_destroy(self.face);h.hb_blob_destroy(self.blob)


