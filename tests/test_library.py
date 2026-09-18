import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import pipeline as p
import library as lib
import frontend as front
import obsidian_sync as sync
import json
import tempfile
import threading
import urllib.request
import urllib.error
from unittest.mock import patch


def fake(self, stage, instructions, data, investigator=False):
    if stage=='pass1':return [{'claim':data['topic'],'category':'architecture','status':'UNVERIFIED','requires_external':False}]
    if stage=='pass2':return [{**c,'status':'UNVERIFIED','evidence':[{'type':'file','path':'src/proof.txt','lines':'1-1','excerpt':'fixture'}]} for c in data['claims']]
    if stage=='pass3':return [{**c,'status':'VERIFIED','domain':'general','sensible':False,'favorable':False,'skeptic_note':'fixture review','contradiction_search':'fixture searched','primary_sources':[{'evidence_index':0,'independence_group':'fixture','reason':'fixture source'}]} for c in data]
    if stage=='pass4':return [{'id':c['id'],'text':'Result: '+c['claim']} for c in data]
    raise AssertionError(stage)


with tempfile.TemporaryDirectory() as td:
    root=Path(td)/'repo';root.mkdir();intel=root/'.project-intelligence';(intel/'claims').mkdir(parents=True);(intel/'reports').mkdir();(intel/'evidence').mkdir();(root/'src').mkdir();(root/'src/proof.txt').write_text('fixture\n');(root/'docs').mkdir();(root/'docs/research.md').write_text('GLOBAL UNCHANGED');(root/'GEMINI.md').write_text('fixture contract')
    p.ROOT=root;p.INTEL=intel;lib.ROOT=root;lib.BASE=intel/'library';front.ROOT=root;front.INTEL=intel;sync.ROOT=root
    for group in p.GROUPS:lib.save(intel/'claims'/f'{group}.json',[])
    lib.save(intel/'state.json',{'obsidian':{'status':'NOT_CONFIGURED','pending_files':[]},'claims':{},'last_commit':None})
    brief=root/'brief.md';brief.write_text('FIRST TOPIC')
    first=lib.create('First','FIRST TOPIC','https://example.org','tema/test',brief,[])
    brief2=root/'second.md';brief2.write_text('SECOND TOPIC')
    second=lib.create('Second','SECOND TOPIC','','tema/test',brief2,[])
    def run(*args):
        with patch.object(sys,'argv',['pipeline.py',*args]),patch.object(p.Runner,'call',fake),patch.object(p.shutil,'which',return_value='agy'),patch.object(p,'sync_docs'):
            p.main()
    run('research','--brief',str(brief),'--case',first)
    run('research','--brief',str(brief2),'--case',second)
    run('document','--case',first)
    first_result=(lib.case_path(first)/'resultados.md').read_text();assert 'FIRST TOPIC' in first_result and 'SECOND TOPIC' not in first_result
    assert (root/'docs/research.md').read_text()=='GLOBAL UNCHANGED'
    assert lib.read(lib.case_path(second)/'claims.json')[0]['status']=='UNVERIFIED'
    run('document','--case',second)
    assert (lib.case_path(first)/'resultados.md').read_text()==first_result
    assert 'FIRST TOPIC' not in (lib.case_path(second)/'fuentes.md').read_text()
    assert lib.read(lib.case_path(first)/'claims.json')[0]['writing_history'][0]['docs']==[f'.project-intelligence/library/{first}/resultados.md']
    vault=Path(td)/'vault';vault.mkdir();lib.save(intel/'obsidian.json',{'vault_path':str(vault)})
    lib.write(intel/'reports/sources.md','all');lib.write(intel/'reports/audit-flags.md','all')
    manifest=intel/'reports/obsidian-sync.json';lib.save(manifest,{'pending_files':[],'generated_at':'test'})
    sync.publish(manifest);note=vault/'Investigaciones'/first/'notas.md';note.write_text('PERSONAL IN OBSIDIAN');sync.publish(manifest);assert note.read_text()=='PERSONAL IN OBSIDIAN'
    for i in range(100):lib.create('Case '+str(i),'searchable-'+str(i),'','tema/scale',brief,[])
    server=front.ThreadingHTTPServer(('127.0.0.1',0),front.Handler);threading.Thread(target=server.serve_forever,daemon=True).start();base='http://127.0.0.1:'+str(server.server_port)
    def get(path):return json.load(urllib.request.urlopen(urllib.request.Request(base+path,headers={'X-Local-Token':front.TOKEN})))
    try:
        page=get('/api/library?tag=tema%2Fscale&page=2');assert page['total']==100 and len(page['cases'])==12
        assert get('/api/library?q=searchable-99')['total']==1
        case=get('/api/case?id='+first);assert case['notes']=='PERSONAL IN OBSIDIAN' and len(case['related'])==1
        try:get('/api/case?id=..%2Foutside')
        except urllib.error.HTTPError as e:assert e.code==404
        else:raise AssertionError('Traversal accepted')
        body=json.dumps({'id':first,'tags':'tema/updated','notes':'EDITED IN FRONTEND'}).encode()
        req=urllib.request.Request(base+'/api/case',data=body,headers={'X-Local-Token':front.TOKEN,'Content-Type':'application/json'})
        assert json.load(urllib.request.urlopen(req))['ok'];assert note.read_text()=='EDITED IN FRONTEND'
        sync.publish(manifest);assert note.read_text()=='EDITED IN FRONTEND'
    finally:server.shutdown();server.server_close()
print('PASS: isolated two-case pipeline, provenance, unchanged global docs, protected personal notes, shared topics, 100-case search/pagination, metadata edit and traversal rejection')

