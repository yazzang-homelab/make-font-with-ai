"""Exact semantic identity: no tolerance for coordinate or metric changes.
Container checksums/timestamps/outline compression differ harmlessly across hosts.
The mapping, complete expanded outline with point flags, advance/LSB, names and
layout tables remain bound. No mismatched byte hash is added to an allowlist.
"""
import io
import hashlib
from fontTools.ttLib import TTFont
from .common import digest, canonical, sha

def canonical_contour(points):
    if not points:return []
    m=min(points);positions=[i for i,p in enumerate(points) if p==m]
    # Only rotate contour start; do NOT reverse winding, quantize or approximate.
    return min(tuple(points[i:]+points[:i]) for i in positions)

def fingerprint(data:bytes) -> dict:
    f=TTFont(io.BytesIO(data),recalcTimestamp=False)
    glyphs=hashlib.sha256();names=f.getGlyphOrder();details={}
    for name in sorted(names):
        g=f['glyf'][name];coords,ends,flags=g.getCoordinates(f['glyf']);contours=[];start=0
        for end in ends:
            points=[(int(coords[i][0]),int(coords[i][1]),int(flags[i])) for i in range(start,end+1)]
            contours.append(canonical_contour(points));start=end+1
        instructions=bytes(getattr(getattr(g,'program',None),'bytecode',b'')).hex()
        rec=[name,sorted(contours),list(f['hmtx'][name]),instructions]
        h=sha(canonical(rec));glyphs.update(canonical([name,h]));details[name]=h
    excluded={'GlyphOrder','glyf','loca','head','cmap','hmtx','name','DSIG'}
    tables={tag:sha(f.getTableData(tag)) for tag in sorted(f.keys()) if tag not in excluded}
    name_rows=sorted([[n.nameID,n.platformID,n.platEncID,n.langID,n.toUnicode()] for n in f['name'].names])
    content={'algorithm':'mfai-exact-outline-v1','upm':f['head'].unitsPerEm,
             'head_flags':f['head'].flags,'glyph_count':len(names),'glyph_order':names,
             'cmap':sorted(f.getBestCmap().items()),'glyphs_sha256':glyphs.hexdigest(),
             'names':name_rows,'tables':tables}
    return {'semantic_sha256':digest(content),'raw_sha256':sha(data),
            'glyph_count':len(names),'glyphs_sha256':content['glyphs_sha256'],
            'table_hashes':tables,'per_glyph':details}
