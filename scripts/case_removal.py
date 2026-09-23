"""Recoverable, isolated removal of a case; shared evidence is retained."""
import datetime
import shutil
import uuid
from pathlib import Path
import library


def remove(case_id, confirmation):
    root=library.ROOT.resolve();intel=root/'.project-intelligence'
    if root not in intel.resolve().parents or root not in library.BASE.resolve().parents:
        raise ValueError('La biblioteca debe estar dentro del proyecto')
    if (intel/'pipeline.lock').exists():raise ValueError('Espera a que termine la ejecución activa')
    folder=library.case_path(case_id);meta=library.read(folder/'case.json')
    if not meta:raise ValueError('La investigación ya no existe')
    if folder!=library.BASE.resolve()/case_id or meta.get('id')!=case_id:
        raise ValueError('La ruta no corresponde a la investigación seleccionada')
    if confirmation!=meta['title']:raise ValueError('Confirma el nombre de la investigación que quieres eliminar')
    token=uuid.uuid4().hex
    archive=(intel/'deleted-investigations'/token).resolve()
    if intel.resolve() not in archive.parents:raise ValueError('Destino de recuperación fuera del proyecto')
    config=library.read(intel/'obsidian.json',{})
    vault=Path(config['vault_path']).resolve() if config.get('vault_path') else None
    vault_case=vault_archive=None
    if vault:
        vault_case=(vault/'Investigaciones'/case_id).resolve()
        vault_archive=(vault/'.research-trash'/token/case_id).resolve()
        if (vault not in vault_case.parents or vault not in vault_archive.parents or vault_case==folder
                or vault_case!=vault/'Investigaciones'/case_id or vault_archive!=vault/'.research-trash'/token/case_id):
            raise ValueError('La ruta de Obsidian no permite una eliminación aislada')
    registries=[intel/'claims'/f'{group}.json' for group in ('architecture','dependencies','changes')]
    snapshots={p:p.read_bytes() for p in registries if p.exists()}
    state_path=intel/'state.json'
    if state_path.exists():snapshots[state_path]=state_path.read_bytes()
    archive.mkdir(parents=True)
    for path,data in snapshots.items():
        target=archive/'registries'/path.relative_to(intel);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    moved_vault=False;moved_case=False
    try:
        if vault_case and vault_case.exists():
            vault_archive.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(vault_case),str(vault_archive));moved_vault=True
        shutil.move(str(folder),str(archive/'case'));moved_case=True
        for path in registries:
            if path.exists():
                library.save(path,[c for c in library.read(path,[]) if c.get('investigation_id')!=case_id])
        if state_path.exists():
            state=library.read(state_path,{})
            prefix=f'.project-intelligence/library/{case_id}/'
            state.setdefault('obsidian',{})['pending_files']=[p for p in state.get('obsidian',{}).get('pending_files',[]) if not p.replace('\\','/').startswith(prefix)]
            library.save(state_path,state)
        library.refresh()
        receipt={'id':token,'case_id':case_id,'title':meta['title'],
                 'removed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 'case_backup':str(archive/'case'),'vault_backup':str(vault_archive) if moved_vault else None,
                 'shared_documents_retained':True}
        library.save(archive/'removal.json',receipt)
        return receipt
    except Exception:
        for path,data in snapshots.items():path.write_bytes(data)
        if moved_case:shutil.move(str(archive/'case'),str(folder))
        if moved_vault:shutil.move(str(vault_archive),str(vault_case))
        library.refresh()
        raise
