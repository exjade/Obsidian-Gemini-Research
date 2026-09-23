"""Open or start the single authoritative local research desk."""
import json
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
PORT=8770
URL=f'http://127.0.0.1:{PORT}'

def version():
    try:
        with urllib.request.urlopen(URL+'/api/version',timeout=1.5) as response:
            return json.loads(response.read())
    except Exception:
        return None

def main():
    current=version()
    if current:
        webbrowser.open(URL)
        print('Mesa de investigación ya disponible: '+URL)
        return 0
    flags=0x08000000 if sys.platform=='win32' else 0
    subprocess.Popen([sys.executable,str(ROOT/'scripts/frontend.py'),'--port',str(PORT),'--no-browser'],
                     cwd=ROOT,creationflags=flags)
    for _ in range(30):
        if version():
            webbrowser.open(URL);print('Mesa de investigación: '+URL);return 0
        time.sleep(.2)
    print('No se pudo iniciar el servicio local en '+URL)
    return 1

if __name__=='__main__':raise SystemExit(main())
