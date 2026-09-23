import sys
import tempfile
import threading
import json
import urllib.request
import urllib.error
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import library as lib
import case_removal
import frontend
import pipeline


class RemovalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'repo';self.root.mkdir();self.intel=self.root/'.project-intelligence'
        self.vault=Path(self.temp.name)/'vault';self.vault.mkdir()
        for module,attr,value in [(lib,'ROOT',self.root),(lib,'BASE',self.intel/'library'),
                                  (frontend,'ROOT',self.root),(frontend,'INTEL',self.intel),
                                  (pipeline,'ROOT',self.root),(pipeline,'INTEL',self.intel)]:
            p=patch.object(module,attr,value);p.start();self.addCleanup(p.stop)
        lib.save(self.intel/'obsidian.json',{'vault_path':str(self.vault)})
        lib.save(self.intel/'state.json',{'obsidian':{'pending_files':['.project-intelligence/library/first/resultados.md']},'claims':{},'last_commit':None})
        self.rows=[{'id':cid+'-claim','claim':'Claim '+cid,'status':'UNSUPPORTED','category':'dependencies',
                    'investigation_id':cid,'evidence':[]} for cid in ('first','second')]
        for group in ('architecture','dependencies','changes'):lib.save(self.intel/'claims'/f'{group}.json',self.rows if group=='dependencies' else [])
        for cid in ('first','second'):
            lib.save(lib.case_path(cid)/'case.json',{'id':cid,'title':cid,'question':'Question','status':'completed','tags':[],
                     'created_at':'2026-01-01','claim_ids':[cid+'-claim']})
            lib.write(lib.case_path(cid)/'notas.md','Repository notes '+cid)
            lib.write(self.vault/'Investigaciones'/cid/'notas.md','Obsidian personal notes '+cid)
        lib.write(self.intel/'documents/shared/original.pdf','Shared PDF')
        lib.refresh()

    def test_removal_is_isolated_recoverable_and_keeps_shared_documents(self):
        receipt=case_removal.remove('first','first')
        self.assertFalse(lib.case_path('first').exists());self.assertFalse((self.vault/'Investigaciones/first').exists())
        self.assertEqual((Path(receipt['case_backup'])/'notas.md').read_text(),'Repository notes first')
        self.assertEqual((Path(receipt['vault_backup'])/'notas.md').read_text(),'Obsidian personal notes first')
        self.assertEqual(lib.read(self.intel/'claims/dependencies.json'),[self.rows[1]])
        self.assertEqual((self.vault/'Investigaciones/second/notas.md').read_text(),'Obsidian personal notes second')
        self.assertTrue((self.intel/'documents/shared/original.pdf').exists())
        self.assertNotIn('first', (lib.BASE/'Biblioteca.md').read_text())
        self.assertEqual(lib.read(self.intel/'state.json')['obsidian']['pending_files'],[])

    def test_confirmation_traversal_and_active_pipeline_are_rejected(self):
        with self.assertRaises(ValueError):case_removal.remove('first','wrong')
        with self.assertRaises(ValueError):case_removal.remove('../outside','first')
        (self.intel/'pipeline.lock').write_text('Active')
        with self.assertRaisesRegex(ValueError,'ejecución activa'):case_removal.remove('first','first')
        self.assertTrue(lib.case_path('first').exists())

    def test_local_failure_rolls_back_case_vault_and_registry(self):
        original=(self.intel/'claims/dependencies.json').read_bytes()
        with patch.object(lib,'refresh',side_effect=[OSError('fixture failure'),None]):
            with self.assertRaises(OSError):case_removal.remove('first','first')
        self.assertEqual((self.intel/'claims/dependencies.json').read_bytes(),original)
        self.assertTrue(lib.case_path('first').exists())
        self.assertEqual((self.vault/'Investigaciones/first/notas.md').read_text(),'Obsidian personal notes first')

    def test_http_delete_blocks_running_job_and_accepts_confirmed_idle_request(self):
        server=frontend.ThreadingHTTPServer(('127.0.0.1',0),frontend.Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            request=urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+'/api/delete-case',
                    data=json.dumps({'case_id':'first','confirmation':'first'}).encode(),
                    headers={'X-Local-Token':frontend.TOKEN,'Content-Type':'application/json'})
            with patch.dict(frontend.JOB,{'status':'running'}):
                with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(request)
                self.assertEqual(caught.exception.code,409)
            with patch.dict(frontend.JOB,{'status':'idle'}),patch.object(pipeline,'sync_docs'),patch.object(pipeline,'sources_report'),patch.object(pipeline,'audit_flags'):
                result=json.load(urllib.request.urlopen(request));self.assertTrue(result['ok']);self.assertTrue(result['recoverable'])
        finally:server.shutdown();server.server_close()


if __name__=='__main__':unittest.main()
