import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_handoff as verifier
import continuity_backup as backup

class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.base=Path(self.temp.name)
        self.root=self.base/'code';self.root.mkdir()
        (self.root/'a.txt').write_bytes(b'old\n')
        self.manifest=self.base/'manifest.json'
        self.manifest.write_text(json.dumps({'files':[{'path':'a.txt','sha256':hashlib.sha256(b'old\n').hexdigest()}]}))
    def tearDown(self):self.temp.cleanup()
    def test_exact_base_and_tamper(self):
        self.assertEqual(verifier.verify(self.root,self.manifest),1)
        (self.root/'a.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError,'base cambió'):verifier.verify(self.root,self.manifest)
    def test_text_patch_check_does_not_apply(self):
        p=self.base/'change.patch'
        p.write_bytes(b'diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n')
        verifier.verify(self.root,self.manifest,p)
        self.assertEqual((self.root/'a.txt').read_text(),'old\n')
    def test_private_and_escape_routes(self):
        for relative in ['../outside','C:/secret','.project-intelligence/state.json','.env','.git/config','pdfs/book.pdf']:
            with self.subTest(relative=relative),self.assertRaises(ValueError):verifier.safe_path(self.root,relative)
    def test_patch_cannot_add_runtime_data(self):
        p=self.base/'bad.patch'
        p.write_bytes(b'diff --git a/.project-intelligence/x b/.project-intelligence/x\nnew file mode 100644\n--- /dev/null\n+++ b/.project-intelligence/x\n@@ -0,0 +1 @@\n+bad\n')
        with self.assertRaisesRegex(ValueError,'privada'):verifier.verify(self.root,self.manifest,p)
    def test_active_lock_blocks_before_copy(self):
        (self.root/'.project-intelligence').mkdir()
        (self.root/'.project-intelligence/pipeline.lock').write_text('123')
        vault=self.base/'vault';vault.mkdir()
        with self.assertRaisesRegex(ValueError,'activa'):backup.backup(self.root,vault,self.base/'backups','http://127.0.0.1:1')
        self.assertFalse((self.base/'backups').exists())
    def test_private_backup_complete_and_preserves_sources(self):
        vault=self.base/'vault';vault.mkdir();(vault/'notes.md').write_text('personal')
        with patch.object(backup,'idle'):
            target=backup.backup(self.root,vault,self.base/'backups','unused')
        self.assertTrue((target/'COMPLETE.json').exists())
        with zipfile.ZipFile(target/'RESPALDO-PRIVADO.zip') as archive:
            self.assertEqual(archive.read('vault/notes.md'),b'personal')
            self.assertEqual(archive.read('project/a.txt'),b'old\n')
        self.assertEqual((vault/'notes.md').read_text(),'personal')
    def test_changed_backup_never_marked_complete(self):
        vault=self.base/'vault';vault.mkdir()
        real=backup.inventory;count=0
        def mutate_inventory(folder):
            nonlocal count
            count+=1
            if count==3:(self.root/'a.txt').write_text('concurrent change')
            return real(folder)
        with patch.object(backup,'idle'),patch.object(backup,'inventory',side_effect=mutate_inventory):
            with self.assertRaisesRegex(ValueError,'Estado cambió'):backup.backup(self.root,vault,self.base/'backups','unused')
        self.assertFalse(list((self.base/'backups').rglob('COMPLETE.json')))

if __name__=='__main__':unittest.main()
