"""Read-only verification of a handoff baseline and optional text patch."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess

PRIVATE={'.git','.gemini','.project-intelligence','.obsidian','pdfs','.venv','.venv-documents','work','outputs','__pycache__'}

def safe_path(root,relative):
    p=PurePosixPath(relative.replace('\\','/'))
    if p.is_absolute() or '..' in p.parts or ':' in relative or not p.parts:
        raise ValueError('Ruta no permitida: '+relative)
    if any(x in PRIVATE or x.startswith('.env') and x!='.env.example' for x in p.parts):
        raise ValueError('Ruta privada: '+relative)
    target=root.joinpath(*p.parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError('Ruta fuera de la copia: '+relative)
    return target

def verify(root,manifest,patch=None):
    entries=json.loads(manifest.read_text(encoding='utf-8'))['files']
    if not entries:raise ValueError('Manifiesto vacío')
    for entry in entries:
        path=safe_path(root,entry['path'])
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
            raise ValueError('La base cambió o falta: '+entry['path'])
    if patch:
        content=patch.read_text(encoding='utf-8')
        if any(x in content for x in ('GIT binary patch','Binary files ','rename from ','copy from ')):
            raise ValueError('Entrega v1 admite sólo cambios de texto sin renombrados/copias')
        stat=subprocess.run(['git','apply','--numstat','-z',str(patch.resolve())],cwd=root,capture_output=True,check=True).stdout
        paths=[x.split(b'\t',2)[2].decode('utf-8') for x in stat.split(b'\0') if x]
        if not paths:raise ValueError('Parche sin cambios')
        for path in paths:safe_path(root,path)
        subprocess.run(['git','apply','--check',str(patch.resolve())],cwd=root,check=True)
    return len(entries)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent.parent)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--patch',type=Path)
    args=p.parse_args()
    try:print(f'Base comprobada: {verify(args.root,args.manifest,args.patch)} archivos. No se modificó ningún archivo.')
    except (ValueError,OSError,subprocess.CalledProcessError) as exc:p.exit(1,str(exc)+'\n')
