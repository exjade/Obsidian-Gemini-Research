"""Create missing runtime data; never reset an existing investigation."""
import argparse
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent


def initialize(root=ROOT):
    intel=root/'.project-intelligence'
    for folder in ('claims','evidence','reports','library','inputs'):
        (intel/folder).mkdir(parents=True,exist_ok=True)
    for folder in ('docs/decisions','docs/changelog','src'):
        (root/folder).mkdir(parents=True,exist_ok=True)
    state={'last_run':None,'last_commit':None,'claims':{s:0 for s in ('VERIFIED','PARTIAL','UNSUPPORTED','CONTRADICTED')},'unverified':0,'obsidian':{'status':'NOT_CONFIGURED','pending_files':[]}}
    missing={intel/'state.json':json.dumps(state,indent=2)+'\n'}
    missing[intel/'library/Guia.md']='# Cerebro de investigación\n\n[[Biblioteca]] · [[Temas]] · [[Fuentes]]\n\nCrea expedientes desde la interfaz local. Usa tema/... y proyecto/... para organizar. Los estados de ejecución no equivalen a veredictos de verdad. Mis notas no se regenera; resultados, fuentes e índices sí. Las relacionadas comparten etiquetas o URLs y no demuestran corroboración.\n\nGuía del programa: guides/GUIA-COMPLETA.md dentro del repositorio.\n'
    for group in ('architecture','dependencies','changes'):missing[intel/'claims'/f'{group}.json']='[]\n'
    for group in ('git','source','web'):missing[intel/'evidence'/f'{group}.json']='[]\n'
    for name in ('architecture','research','changelog','sources','audit-flags'):missing[intel/'reports'/f'{name}.md']='# '+name+'\n\nSin resultados registrados todavía.\n'
    for name in ('architecture','research'):missing[root/'docs'/f'{name}.md']='# '+name+'\n\nSin claims VERIFIED publicados todavía.\n'
    for path,text in missing.items():
        try:
            with path.open('x',encoding='utf-8') as handle:handle.write(text)
        except FileExistsError:pass


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Inicializa datos locales sin reemplazar los existentes')
    parser.add_argument('--vault',help='Ruta de un vault independiente para publicar resultados')
    args=parser.parse_args();initialize()
    if args.vault:
        vault=Path(args.vault).resolve()
        if vault==ROOT or vault in ROOT.parents or ROOT in vault.parents:
            parser.error('Usa un vault separado del repositorio')
        vault.mkdir(parents=True,exist_ok=True);(vault/'.obsidian').mkdir(exist_ok=True)
        path=ROOT/'.project-intelligence/obsidian.json'
        temp=path.with_suffix('.tmp')
        temp.write_text(json.dumps({'vault_path':str(vault),'transport':'local-filesystem'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(temp,path)
        print('Destino local configurado: '+str(vault))
    print('Datos locales listos. No se reemplazaron investigaciones existentes.')
