"""Private backup; refuses active research and detects changes during copying."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import urllib.request
import zipfile

SKIP={'__pycache__','.venv','.venv-documents','venv','node_modules'}

def idle(root,url):
    if (root/'.project-intelligence/pipeline.lock').exists():
        raise ValueError('Investigación activa o bloqueo pendiente. No se inició el respaldo.')
    html=urllib.request.urlopen(url,timeout=5).read().decode('utf-8')
    token=re.search(r"const token='([^']+)'",html).group(1)
    request=urllib.request.Request(url+'/api/status',headers={'X-Local-Token':token})
    job=json.load(urllib.request.urlopen(request,timeout=5))['job']
    if job.get('status')=='running':raise ValueError('Trabajo activo. Espera a que termine.')

def inventory(folder):
    result={}
    def visit(path):
        for child in path.iterdir():
            if child.is_symlink():raise ValueError('Enlace simbólico; revisar antes del respaldo: '+str(child))
            if child.is_dir():
                if child.name not in SKIP:visit(child)
            elif child.is_file():
                with child.open('rb') as stream:
                    result[child.relative_to(folder).as_posix()]=hashlib.file_digest(stream,'sha256').hexdigest()
    visit(folder)
    return result

def backup(root,vault,destination,url):
    root=root.resolve();vault=vault.resolve();destination=destination.resolve()
    if not vault.is_dir():raise ValueError('Vault inexistente')
    if destination.is_relative_to(root) or destination.is_relative_to(vault):raise ValueError('Destino debe estar fuera del proyecto y vault')
    idle(root,url)
    before={'project':inventory(root),'vault':inventory(vault)}
    idle(root,url)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    target=destination/stamp;target.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(target/'RESPALDO-PRIVADO.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for label,folder in [('project',root),('vault',vault)]:
            for relative,digest in before[label].items():
                data=(folder/relative).read_bytes()
                if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('Archivo cambió; respaldo parcial sin COMPLETE')
                archive.writestr(label+'/'+relative,data)
    idle(root,url)
    if before!={'project':inventory(root),'vault':inventory(vault)}:raise ValueError('Estado cambió durante respaldo; parcial sin COMPLETE')
    with zipfile.ZipFile(target/'RESPALDO-PRIVADO.zip') as archive:
        if archive.testzip():raise ValueError('Respaldo corrupto')
    (target/'COMPLETE.json').write_text(json.dumps({'created_at_utc':stamp,'files':before,'private_do_not_upload':True},indent=2),encoding='utf-8')
    return target

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent.parent)
    p.add_argument('--vault',type=Path,required=True)
    p.add_argument('--destination',type=Path,required=True)
    p.add_argument('--url',default='http://127.0.0.1:8768')
    args=p.parse_args()
    try:print('Respaldo privado completo: '+str(backup(args.root,args.vault,args.destination,args.url)))
    except Exception as exc:p.exit(1,str(exc)+'\n')
