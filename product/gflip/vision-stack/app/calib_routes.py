import os, pathlib, json
from fastapi import Response, Request
from fastapi.responses import HTMLResponse, JSONResponse

CALIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'calibration', 'boards')
SIZES = [30,60,90,120,150,180,210,240,270,300,330,360,390,420,450,470,510,570,630,690,780,870,960,1050]

def register(app):
    @app.get('/calib/board/{profile}/{size}mm.png')
    def calib_board(profile: str, size: int):
        p = pathlib.Path(CALIB_DIR) / profile / f'{size}mm.png'
        if not p.exists():
            return Response(b'not found', status_code=404)
        return Response(p.read_bytes(), media_type='image/png')


    @app.get('/calib/board/{profile}/{size}mm.jpg')
    def calib_board_jpg(profile: str, size: int):
        p = pathlib.Path(CALIB_DIR) / profile / f'{size}mm.png'
        if not p.exists():
            return Response(b'not found', status_code=404)
        import cv2 as _cv2
        img = _cv2.imread(str(p), _cv2.IMREAD_GRAYSCALE)
        ok, buf = _cv2.imencode('.jpg', img, [_cv2.IMWRITE_JPEG_QUALITY, 95])
        return Response(buf.tobytes(), media_type='image/jpeg')


    @app.get('/calib/print/{name}')
    def calib_print(name: str):
        import pathlib as _pl
        base = pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / 'calibration' / 'print'
        p = base / name
        if not p.exists() or not p.is_file():
            return Response(b'not found', status_code=404)
        mt = 'application/pdf' if name.endswith('.pdf') else 'image/png'
        return Response(p.read_bytes(), media_type=mt)


    @app.post('/calib/upload')
    async def calib_upload(request: Request):
        import pathlib as _pl
        from fastapi import UploadFile, File
        form = await request.form()
        up = form.get('file')
        if up is None:
            return Response(b'no file', status_code=400)
        dest_dir = _pl.Path('/home/taza/vision-stack/world/cad')
        dest_dir.mkdir(parents=True, exist_ok=True)
        data = await up.read()
        dest = dest_dir / up.filename
        dest.write_bytes(data)
        return JSONResponse({'saved': str(dest), 'bytes': len(data)})

    @app.get('/calib/viewer', response_class=HTMLResponse)
    def calib_viewer(profile: str = 'mt15', size: int = 30):
        html = """<!DOCTYPE html><html><head><title>Calib Board</title>
<style>body{margin:0;background:#000}img{width:100vw;height:100vh;object-fit:fill}</style></head>
<body><img id="b" src="/calib/board/PROFILE/SIZEmm.png">
<script>
var sizes=SIZES;
var i=sizes.indexOf(SIZE);
var profile='PROFILE';
function set(){document.getElementById('b').src='/calib/board/'+profile+'/'+sizes[i]+'mm.png';}
document.body.onclick=function(){i=(i+1)%sizes.length; set();};
window.addEventListener('keydown',function(e){if(e.key==='ArrowRight'){i=(i+1)%sizes.length;} if(e.key==='ArrowLeft'){i=(i-1+sizes.length)%sizes.length;} set();});
</script></body></html>"""
        html = html.replace('PROFILE', profile).replace('SIZES', json.dumps(SIZES)).replace('SIZE', str(size))
        return HTMLResponse(html)
