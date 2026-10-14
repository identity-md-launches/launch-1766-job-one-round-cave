#!/usr/bin/env python3
"""Retain installed-image-tool pigment only; keep ancestor rock and marks intact."""
import hashlib
import json
from pathlib import Path
from image_bytes import read_png, png, jpeg, resize

ANCESTOR='6628b92f3444319f630284208b96c701021dd5cc0e595320612c3ec9885ac955'


def main():
    folder=Path('artifacts/line-4')
    before=(folder/'wall.png').read_bytes()
    assert hashlib.sha256(before).hexdigest()==ANCESTOR, 'requires record 24 ancestor'
    draft=(folder/'wall-v5.png').read_bytes()
    w,h,old=read_png(before)
    gw,gh,generated=read_png(draft)
    assert (w,h)==(1254,1254)
    assert (gw,gh)==(1536,1024)
    final=bytearray(old)
    bounds=[w,h,0,0]; changed=0
    # The motif's two pebbles and curved connecting strokes are on vacant stone
    # below the ancestor branch, right of its surrounding ochre arc.
    for y in range(790,890):
        for x in range(991,1171):
            sx=450+(x-991)*600//180
            sy=345+(y-790)*300//100
            red=((sx-585)/125)**2+((sy-478)/116)**2<1
            yellow=((sx-927)/102)**2+((sy-482)/116)**2<1
            curve=650<sx<950 and 530<sy<620
            if not (red or yellow or curve): continue
            i=(y*w+x)*3; j=(sy*gw+sx)*3
            r,g,b=generated[j:j+3]
            or_,og,ob=old[i:i+3]
            # Deep inherited cracks are retained even within the new area.
            if or_+og+ob<160: continue
            charcoal=r<85 and g<65 and b<55
            ochre_red=red and r>70 and g<r*.5 and b<r*.35
            ochre_yellow=yellow and r>140 and g>80 and b<g*.55
            if not (charcoal or ochre_red or ochre_yellow): continue
            # Blend with original texture instead of importing generated rock.
            opacity=.65 if charcoal else .48
            final[i:i+3]=bytes(round(a*(1-opacity)+v*opacity) for a,v in zip(old[i:i+3],(r,g,b)))
            if final[i:i+3]!=old[i:i+3]:
                changed+=1
                bounds=[min(bounds[0],x),min(bounds[1],y),max(bounds[2],x),max(bounds[3],y)]
    assert changed>1000, 'insufficient pigment'
    output=png(w,h,final)
    (folder/'wall.png').write_bytes(output)
    (folder/'wall-v5.png').write_bytes(output)
    preview=jpeg(512,512,resize(w,h,final),52)
    assert len(preview)<100000
    Path('dist/line-4/25.jpg').write_bytes(preview)
    review={'wall':{'paths':['artifacts/line-4/wall.png','artifacts/line-4/wall-v5.png'],
                   'width':w,'height':h,'format':'PNG','mode':'RGB','sha256':hashlib.sha256(output).hexdigest()},
            'preview':{'path':'dist/line-4/25.jpg','width':512,'height':512,'format':'JPEG','bytes':len(preview)},
            'ancestorSha256':ANCESTOR,'generatedImageSha256':hashlib.sha256(draft).hexdigest(),
            'changedPixels':changed,'unchangedPixels':w*h-changed,'additionBounds':bounds,
            'preservation':'Only selected generated pigment blended on vacant lower-right stone. Every pixel outside the addition remains exactly unchanged, including Pepe and all ancestor marks. Deep cracks inside the addition were protected.',
            'imageTool':'installed mcp image generate_image; one generated motif, extracted pigment',
            'prompt':'Two small worn ochre pebbles with charcoal centers joined by two curved charcoal strokes on rough warm torchlit rock; no writing, hands, people, borders or logos.',
            'visualReview':'Pending inspection','unmetVisualRequirements':[],
            'limitations':['Local visual review, not independent certification.','Small worn pigment is subtler in the JPEG thumbnail.']}
    Path('line-4/wall-review-25.json').write_text(json.dumps(review,indent=2)+'\n')
    print(json.dumps(review,indent=2))


if __name__=='__main__': main()
