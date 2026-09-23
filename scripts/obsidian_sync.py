"""Publish documentation to the configured local vault; verify every copied byte."""
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parent.parent


def publish(manifest_path):
    config = json.loads((ROOT / '.project-intelligence/obsidian.json').read_text(encoding='utf-8'))
    vault = Path(config['vault_path']).resolve()
    if not vault.is_dir() or vault == ROOT or vault in ROOT.parents or ROOT in vault.parents:
        raise ValueError('El vault debe existir y estar separado del repositorio.')
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    paths = set(manifest['pending_files'])
    paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT / 'docs').rglob('*.md'))
    paths.update(('.project-intelligence/reports/sources.md', '.project-intelligence/reports/audit-flags.md'))
    base=ROOT/'.project-intelligence/library'
    paths.update(p.relative_to(ROOT).as_posix() for p in base.glob('*.md'))
    paths.update(p.relative_to(ROOT).as_posix() for p in base.glob('*/*.md'))
    paths.update(p.relative_to(ROOT).as_posix() for p in base.glob('*/adjuntos/*') if p.is_file())
    verified = []
    for name in sorted(paths):
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Ruta de publicación inválida: ' + name)
        if relative.parts[0] == 'docs' and relative.suffix == '.md':
            target = vault / relative
        elif name in ('.project-intelligence/reports/sources.md', '.project-intelligence/reports/audit-flags.md'):
            target = vault / 'auditoria' / relative.name
        elif relative.parts[:2] == ('.project-intelligence','library'):
            tail=relative.parts[2:]
            if len(tail)==1 and relative.suffix=='.md':
                target=vault/relative.name
            elif len(tail)==2 and relative.name in ('resumen.md','pregunta.md','resultados.md','fuentes.md','auditoria.md','notas.md','documentos.md','alcance.md','revisiones-humanas.md'):
                target=vault/'Investigaciones'/Path(*tail)
            elif len(tail)==3 and tail[1]=='adjuntos':
                target=vault/'Investigaciones'/Path(*tail)
            else: raise ValueError('Archivo de biblioteca fuera del alcance: '+name)
        else:
            raise ValueError('Archivo fuera del alcance de publicación: ' + name)
        source = (ROOT / relative).resolve()
        if ROOT not in source.parents or vault not in target.resolve().parents:
            raise ValueError('Ruta fuera del proyecto o vault: ' + name)
        data = source.read_bytes()
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.name=='notas.md' and target.exists():
            # Personal notes may have been edited in Obsidian. Never regenerate them.
            continue
        if not target.exists() or target.read_bytes() != data:
            temporary = target.with_name(target.name + '.' + uuid.uuid4().hex + '.tmp')
            try:
                temporary.write_bytes(data)
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
        if target.read_bytes() != data:
            raise ValueError('La copia no coincide: ' + str(target))
        verified.append({'source': name, 'destination': target.relative_to(vault).as_posix(),
                         'sha256': hashlib.sha256(data).hexdigest()})
    receipt = {'transport': 'local-filesystem', 'vault_path': str(vault),
               'manifest_generated_at': manifest['generated_at'], 'verified_files': verified}
    (ROOT / '.project-intelligence/reports/obsidian-receipt.json').write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Vault independiente: ' + str(vault) + '; archivos verificados: ' + str(len(verified)))


if __name__ == '__main__':
    try:
        publish(sys.argv[1])
    except Exception as exc:
        print('ERROR de publicación Obsidian: ' + str(exc), file=sys.stderr)
        sys.exit(1)
