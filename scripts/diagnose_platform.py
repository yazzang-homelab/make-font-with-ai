"""Hash-only, no-font-export investigation of platform-dependent R36 arithmetic."""
from pathlib import Path
import argparse,builtins,hashlib,io,json,sys,platform,time
import make_font_with_ai
from make_font_with_ai.fingerprint import fingerprint
from make_font_with_ai.engine import setup_names
from make_font_with_ai.common import write_json,digest
from fontTools.fontBuilder import FontBuilder
from fontTools.ttLib import TTFont
ROOT=Path(__file__).resolve().parents[1]
ENGINE=Path(make_font_with_ai.__file__).parent/'engines/hangul_brush'
sys.path.insert(0,str(ENGINE))
import build_font as legacy
import optical_balance as balance

def build(mode):
    operation=(lambda x:builtins.round(builtins.round(float(x),7))) if mode=='stable_round7' else builtins.round
    for module in (legacy,balance):
        if hasattr(module,'font_unit_round'):module.font_unit_round=operation
        else:module.round=operation
    f,_=legacy.build_font();data=legacy.serialize(f)
    f=TTFont(io.BytesIO(data),recalcTimestamp=False)
    brief=json.loads((ROOT/'examples/hangul-brush/design-brief.json').read_text(encoding='utf-8'))
    setup_names(FontBuilder(font=f),brief);out=io.BytesIO();f.save(out);data=out.getvalue()
    fp=fingerprint(data);reopen=TTFont(io.BytesIO(data),recalcTimestamp=False)
    fp['head_flags']=reopen['head'].flags
    fp['glyph_order_sha256']=digest(reopen.getGlyphOrder())
    fp['cmap_sha256']=digest(sorted(reopen.getBestCmap().items()))
    fp['names_sha256']=digest(sorted([[n.nameID,n.platformID,n.platEncID,n.langID,n.toUnicode()] for n in reopen['name'].names]))
    fp['platform']=platform.platform();fp['python']=platform.python_version();fp['mode']=mode
    import shapely,numpy,scipy,fontTools
    fp['libraries']={'shapely':shapely.__version__,'GEOS':shapely.geos_version_string,'numpy':numpy.__version__,'scipy':scipy.__version__,'fonttools':fontTools.__version__}
    return fp

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'_diagnostic');p.add_argument('--mode',choices=['native','stable_round7','both'],default='both');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    for mode in (['native','stable_round7'] if a.mode=='both' else [a.mode]):
        t=time.time();print('BUILD_DIAGNOSTIC',mode,flush=True);r=build(mode)
        write_json(a.out/(mode+'-fingerprint.json'),r)
        print('DIAGNOSTIC_DONE',mode,r['semantic_sha256'],'seconds',round(time.time()-t,1),flush=True)
