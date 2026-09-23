import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import research_scope
import pipeline as p
import library as lib
import frontend as front
import obsidian_sync as sync
import json
import tempfile
import threading
import urllib.request
import urllib.error
import copy
import hashlib
import source_check as sc
import source_resolver
from unittest.mock import patch


writer_calls=[]
def fake(self, stage, instructions, data, investigator=False):
    if stage=='pass4':writer_calls.append(data)
    if stage=='scope_review':return [{'id':c['id'],'recommended':True,'reason':'Fixture relevance','answers':'Fixture question'} for c in data['candidates']]
    if stage=='pass1':return [{'claim':data['topic'],'category':'architecture','status':'UNVERIFIED','requires_external':False}]
    if stage=='pass2':return [{**c,'status':'UNVERIFIED','evidence':[{'type':'file','path':'src/proof.txt','lines':'1-1','excerpt':'fixture'}]} for c in data['claims']]
    if stage=='pass3':
        reviewed=[]
        for c in data:
            row=copy.deepcopy(c);row['evidence'][0]['semantic_review']={
                'target_claim_id':c['id'],'decision':'support','basis':'fixture exact passage support',
                'limits':'','reviewer':'pass3'}
            reviewed.append({**row,'status':'VERIFIED','domain':'general','sensible':False,'favorable':False,'skeptic_note':'fixture review','contradiction_search':'fixture searched','primary_sources':[{'evidence_index':0,'independence_group':'fixture','reason':'fixture source'}]})
        return reviewed
    if stage=='pass4':return [{'id':c['id'],'text':'Result: '+c['claim']} for c in data]
    raise AssertionError(stage)


with tempfile.TemporaryDirectory() as td:
    root=Path(td)/'repo';root.mkdir();intel=root/'.project-intelligence';(intel/'claims').mkdir(parents=True);(intel/'reports').mkdir();(intel/'evidence').mkdir();(root/'src').mkdir();(root/'src/proof.txt').write_text('fixture\n');(root/'docs').mkdir();(root/'docs/research.md').write_text('GLOBAL UNCHANGED');(root/'GEMINI.md').write_text('fixture contract')
    (root/'scripts').mkdir()
    (root/'scripts/frontend.html').write_bytes((Path(__file__).resolve().parents[1]/'scripts/frontend.html').read_bytes())
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
    first_meta=lib.read(lib.case_path(first)/'case.json');first_meta['tags']=['tema/first'];lib.save(lib.case_path(first)/'case.json',first_meta)
    second_meta=lib.read(lib.case_path(second)/'case.json');second_meta['tags']=['tema/second'];lib.save(lib.case_path(second)/'case.json',second_meta)
    rows=p.all_claims();first_claim=next(c for c in rows if c.get('investigation_id')==first)
    second_claim=next(c for c in rows if c.get('investigation_id')==second)
    original_first=copy.deepcopy(first_claim['evidence']);original_second=copy.deepcopy(second_claim['evidence'])
    first_claim['evidence']=[{'type':'external','url':'https://example.org/paper','title':'Fixture paper','excerpt':'shared passage',
        'doi':'10.1234/declared-one','source_id':'a'*64,'evidence_id':'b'*64,'source_identity_policy':'source-identity-v1','relation':'support'}]
    second_claim['evidence']=[{**first_claim['evidence'][0],'url':'https://publisher.example/paper.pdf','title':'Publisher alias','doi':'10.1234/declared-two','source_check_id':'','relation':'contradiction'}]
    first_e=first_claim['evidence'][0];second_e=second_claim['evidence'][0]
    first_e['source_check_id']='c'*32
    check_dir=intel/'source-checks';check_dir.mkdir(parents=True)
    snapshot=b'trusted saved page';excerpt_hash=hashlib.sha256(first_e['excerpt'].encode()).hexdigest()
    record={'id':first_e['source_check_id'],'policy':sc.POLICY,'original_url':first_e['url'],'excerpt_sha256':excerpt_hash,
        'snapshot_sha256':hashlib.sha256(snapshot).hexdigest(),'final_url':'https://publisher.example/paper.pdf',
        'normalized_final_url':'publisher.example/paper.pdf','page_title':'Observed publisher title','content_type':'text/html',
        'body_sha256':hashlib.sha256(snapshot).hexdigest(),'checked_at':'2026-09-20T00:00:00Z','persistent_identifiers':['doi:10.1234/from-url']}
    (check_dir/(first_e['source_check_id']+'.bin')).write_bytes(snapshot)
    (check_dir/(first_e['source_check_id']+'.json')).write_text(json.dumps(record),encoding='utf-8')
    resolver_payload={'message':{'DOI':'10.1234/declared-one','title':['Resolved fixture title']}}
    resolver_receipt=source_resolver.resolve('doi','10.1234/declared-one',
        lambda url:{'status':200,'url':url,'body':json.dumps(resolver_payload).encode('utf-8')})
    source_resolver.save_receipt(root,first_e['source_id'],resolver_receipt)
    p.persist(rows);lib.refresh(rows);catalog=lib.read(lib.BASE/'sources.json')
    assert catalog['policy']=='source-catalog-v1' and catalog['sources']
    assert first_e['source_id']==second_e['source_id'] and first_e['evidence_id']==second_e['evidence_id']
    catalog=lib.read(lib.BASE/'sources.json');source=next(s for s in catalog['sources'] if s['source_id']==first_e['source_id'])
    metadata=source['metadata']
    assert metadata['policy']=='source-metadata-v1'
    assert source['metadata_resolutions'][0]['outcome']=='resolved'
    assert any(a['provenance']=='resolver.crossref.doi' and a['value']=='10.1234/declared-one'
               for a in metadata['fields']['doi']['assertions'])
    assert metadata['fields']['doi']['value'] is None
    assert len(metadata['conflicts'])>=2
    assert any(a['provenance']=='source_check.page_title' and a['value']=='Observed publisher title'
               for a in metadata['fields']['title']['assertions'])
    assert all(a.get('reference')==first_e['source_check_id'] for a in metadata['fields']['title']['assertions']
               if a['provenance']=='source_check.page_title')
    passage=next(x for x in source['passages'] if x['evidence_id']==first_e['evidence_id'])
    assert {r['role'] for r in passage['relationships']}=={'support','contradiction'}
    assert len(source['references'])==2 and {r['url'] for r in source['references']}=={'https://example.org/paper','https://publisher.example/paper.pdf'}
    assert [x['id'] for x in lib.related_cases(lib.all_cases(),lib.read(lib.case_path(first)/'case.json'))]==[second]
    before=(lib.BASE/'sources.json').read_bytes()
    with patch.object(source_resolver,'fetch',side_effect=AssertionError('catalogue refresh must stay offline')):
        lib.refresh(p.all_claims())
    assert (lib.BASE/'sources.json').read_bytes()==before
    # source-only relation works across disjoint tags; identical legacy URLs do not.
    unrelated=[{'id':'a','tags':['tema/a'],'source_ids':['stable']},{'id':'b','tags':['tema/b'],'source_ids':['stable']}]
    assert [x['id'] for x in lib.related_cases(unrelated,unrelated[0])]==['b']
    legacy_related=[{'id':'x','tags':['tema/x'],'source_urls':['https://same.example'],'source_ids':[]},
                    {'id':'y','tags':['tema/y'],'source_urls':['https://same.example'],'source_ids':[]}]
    assert lib.related_cases(legacy_related,legacy_related[0])==[]
    # Apparent IDs without an explicit matching policy, malformed IDs, and foreign policies are never canonicalized.
    invalid_policy=copy.deepcopy(first_claim);invalid_policy['id']='d'*32;invalid_policy['claim']='Policy-less IDs'
    invalid_policy['evidence']=[{**first_e,'source_id':'9'*64,'evidence_id':'8'*64}]
    invalid_policy['evidence'][0].pop('source_identity_policy',None)
    foreign=copy.deepcopy(invalid_policy);foreign['id']='c'*32;foreign['claim']='Foreign policy IDs'
    foreign['evidence'][0]['source_identity_policy']='source-identity-v999'
    malformed=copy.deepcopy(invalid_policy);malformed['id']='b'*32;malformed['claim']='Malformed IDs'
    malformed['evidence'][0].update(source_identity_policy='source-identity-v1',source_id='not-a-digest')
    legacy_rows=p.all_claims()+[invalid_policy,foreign,malformed];lib.refresh(legacy_rows);catalog=lib.read(lib.BASE/'sources.json')
    assert all(s['source_id'] not in {'9'*64,'not-a-digest'} for s in catalog['sources'])
    assert catalog['legacy_uncatalogued_count']>=3
    legacy=copy.deepcopy(first_claim);legacy['id']='e'*32;legacy['claim']='Legacy source fixture';legacy['evidence']=[{'type':'external','url':'https://example.org/legacy','excerpt':'old'}]
    rows=p.all_claims();rows.append(legacy);lib.refresh(rows);catalog=lib.read(lib.BASE/'sources.json')
    assert catalog['legacy_uncatalogued_count']>=1 and all(s['url']!='https://example.org/legacy' for s in catalog['sources'])
    rows=p.all_claims();next(c for c in rows if c.get('investigation_id')==first)['evidence']=original_first
    next(c for c in rows if c.get('investigation_id')==second)['evidence']=original_second
    p.persist(rows);lib.refresh(rows)
    research_scope.approve(first,[lib.read(lib.case_path(first)/'claims.json')[0]['id']])
    research_scope.approve(second,[lib.read(lib.case_path(second)/'claims.json')[0]['id']])
    run('document','--case',first)
    first_result=(lib.case_path(first)/'resultados.md').read_text();assert 'FIRST TOPIC' in first_result and 'SECOND TOPIC' not in first_result
    assert (root/'docs/research.md').read_text()=='GLOBAL UNCHANGED'
    assert lib.read(lib.case_path(second)/'claims.json')[0]['status']=='UNVERIFIED'
    run('document','--case',second)
    assert (lib.case_path(first)/'resultados.md').read_text()==first_result
    assert 'FIRST TOPIC' not in (lib.case_path(second)/'fuentes.md').read_text()
    assert lib.read(lib.case_path(first)/'claims.json')[0]['writing_history'][0]['docs']==[f'.project-intelligence/library/{first}/resultados.md']
    # A supported subset must not reach Writer while another admitted hypothesis remains unsupported.
    rows=p.all_claims() if hasattr(p,'all_claims') else sum([lib.read(intel/'claims'/f'{g}.json',[]) for g in p.GROUPS],[])
    first_claim=next(c for c in rows if c.get('investigation_id')==first)
    unresolved=copy.deepcopy(first_claim);unresolved.update(id='f'*32,claim='Unresolved hypothesis',status='UNSUPPORTED',evidence=[],primary_sources=[])
    unresolved.pop('writing_history',None);rows.append(unresolved);p.persist(rows);lib.refresh(rows)
    meta=lib.read(lib.case_path(first)/'case.json');meta['scope']['selected_ids'].append(unresolved['id'])
    meta['scope']['candidates'].append({'id':unresolved['id'],'claim':unresolved['claim']});lib.save(lib.case_path(first)/'case.json',meta)
    before=len(writer_calls);run('document','--case',first)
    assert len(writer_calls)==before, 'Writer ran despite unresolved approved hypothesis'
    assert 'Informe provisional' in (lib.case_path(first)/'resultados.md').read_text()
    assert not lib.read(lib.case_path(first)/'case.json')['publication']['consolidated']
    assert any(p.read_text()==first_result for p in (lib.case_path(first)/'resultados-anteriores').glob('*.md'))
    vault=Path(td)/'vault';vault.mkdir();lib.save(intel/'obsidian.json',{'vault_path':str(vault)})
    lib.write(intel/'reports/sources.md','all');lib.write(intel/'reports/audit-flags.md','all')
    manifest=intel/'reports/obsidian-sync.json';lib.save(manifest,{'pending_files':[],'generated_at':'test'})
    sync.publish(manifest);note=vault/'Investigaciones'/first/'notas.md';note.write_text('PERSONAL IN OBSIDIAN');sync.publish(manifest);assert note.read_text()=='PERSONAL IN OBSIDIAN'
    for i in range(100):lib.create('Case '+str(i),'searchable-'+str(i),'','tema/scale',brief,[])
    server=front.ThreadingHTTPServer(('127.0.0.1',0),front.Handler);threading.Thread(target=server.serve_forever,daemon=True).start();base='http://127.0.0.1:'+str(server.server_port)
    def get(path):return json.load(urllib.request.urlopen(urllib.request.Request(base+path,headers={'X-Local-Token':front.TOKEN})))
    try:
        html=urllib.request.urlopen(base+'/?investigacion='+first+'&vista=fuentes').read().decode('utf-8')
        assert 'Mesa de investigación' in html and '__TOKEN__' not in html
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

