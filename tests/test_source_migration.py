import copy
import hashlib
import json
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import library
import source_check
import source_identity
import source_migration as migration


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'repo'
        self.intel = self.root / '.project-intelligence'
        self.claims_dir = self.intel / 'claims'
        self.base = self.intel / 'library'
        self.claims_dir.mkdir(parents=True)
        self.base.mkdir(parents=True)
        self.old_root, self.old_base = library.ROOT, library.BASE
        library.ROOT, library.BASE = self.root, self.base
        self.case_id = '2026-09-23-case-1234abcd'
        self.case_folder = self.base / self.case_id
        self.case_folder.mkdir()
        self.case_meta = {'id': self.case_id, 'title': 'Fixture case', 'question': 'Question',
                          'created_at': '2026-09-23T00:00:00Z', 'updated_at': '2026-09-23T00:00:00Z',
                          'status': 'historical', 'tags': [], 'links': '', 'claim_ids': []}
        library.save(self.case_folder / 'case.json', self.case_meta)
        self.claim = {'id': 'c' * 32, 'category': 'architecture', 'investigation_id': self.case_id,
                      'claim': 'Legacy claim text', 'status': 'UNSUPPORTED', 'skeptic_note': 'Preserve this',
                      'primary_sources': [], 'evidence': [{'type': 'external', 'url': 'https://example.org/paper',
                          'title': 'Declared title', 'excerpt': 'A long exact excerpt for the legacy passage.',
                          'relation': 'context', 'source_assessment': {'credibility': {'status': 'unreviewed'}}}]}
        for group in migration.GROUPS:
            library.save(self.claims_dir / (group + '.json'), [self.claim] if group == 'architecture' else [])
        self.intel.joinpath('evidence').mkdir()
        self.intel.joinpath('library').mkdir(exist_ok=True)
        library.save(self.base / 'sources.json', {'policy': source_identity.CATALOG_POLICY,
                      'sources': [], 'legacy_uncatalogued_count': 1})
        library.refresh([self.claim])

    def tearDown(self):
        library.ROOT, library.BASE = self.old_root, self.old_base
        self.temp.cleanup()

    def _persist_and_refresh(self, rows):
        for group in migration.GROUPS:
            library.save(self.claims_dir / (group + '.json'), [c for c in rows if c['category'] == group])
        library.refresh(rows)

    def test_preview_is_read_only_and_apply_adds_only_identity_provenance(self):
        original_path = self.claims_dir / 'architecture.json'
        before = original_path.read_bytes()
        plan = migration.build_plan(self.root)
        self.assertEqual(original_path.read_bytes(), before)
        self.assertEqual(plan['summary']['eligible'], 1)
        self.assertEqual(plan['items'][0]['identity_basis'], 'reference_only')
        manifest, path = migration.write_plan(self.root)
        self.assertEqual(original_path.read_bytes(), before)
        self.assertTrue(path.is_file())

        persisted, refreshed = [], []
        applied = migration.apply_manifest(
            self.root, path,
            lambda rows: (persisted.append(copy.deepcopy(rows)), self._persist_and_refresh(rows)),
            lambda rows: (refreshed.append(copy.deepcopy(rows)), library.refresh(rows)))
        claim = library.read(original_path)[0]
        evidence = claim['evidence'][0]
        expected = source_identity.identify(evidence)
        self.assertEqual(evidence['source_id'], expected['source_id'])
        self.assertEqual(evidence['evidence_id'], expected['evidence_id'])
        self.assertEqual(evidence['source_identity_policy'], source_identity.POLICY)
        self.assertEqual(evidence['source_migration']['policy'], migration.POLICY)
        self.assertEqual(evidence['relation'], 'context')
        self.assertEqual(evidence['excerpt'], 'A long exact excerpt for the legacy passage.')
        self.assertEqual(evidence['source_assessment'], {'credibility': {'status': 'unreviewed'}})
        self.assertEqual(claim['claim'], 'Legacy claim text')
        self.assertEqual(claim['status'], 'UNSUPPORTED')
        self.assertEqual(claim['skeptic_note'], 'Preserve this')
        self.assertEqual(applied['status'], 'applied')
        self.assertEqual(library.read(self.base / 'sources.json')['legacy_uncatalogued_count'], 0)
        before_repeat = original_path.read_bytes()
        repeated = migration.apply_manifest(
            self.root, path, lambda rows: self.fail('successful manifest rewrote evidence'),
            lambda rows: self.fail('successful manifest repeated finalization'))
        self.assertEqual(repeated, applied)
        self.assertEqual(original_path.read_bytes(), before_repeat)
        self.assertEqual(len(persisted), 1)
        self.assertEqual(len(refreshed), 1)

    def test_refresh_failure_after_persist_is_reconciled_without_rewriting_identity(self):
        _, path = migration.write_plan(self.root)
        persist_calls, refresh_calls = [], []

        def persist(rows):
            persist_calls.append(1)
            self._persist_and_refresh(rows)

        def fail_refresh(rows):
            refresh_calls.append(1)
            raise OSError('fixture refresh failure')

        with self.assertRaisesRegex(OSError, 'fixture refresh failure'):
            migration.apply_manifest(self.root, path, persist, fail_refresh)
        self.assertEqual(migration._read(path)['status'], 'apply_error')
        evidence_path = self.claims_dir / 'architecture.json'
        after_persist = library.read(evidence_path)[0]['evidence'][0]
        provenance = copy.deepcopy(after_persist['source_migration'])
        self.assertEqual(len(persist_calls), 1)

        recovered = migration.apply_manifest(self.root, path, persist, lambda rows: refresh_calls.append(1))
        after_recovery = library.read(evidence_path)[0]['evidence'][0]
        self.assertEqual(recovered['status'], 'applied')
        self.assertEqual(after_recovery['source_id'], after_persist['source_id'])
        self.assertEqual(after_recovery['evidence_id'], after_persist['evidence_id'])
        self.assertEqual(after_recovery['source_migration'], provenance)
        self.assertEqual(len(persist_calls), 1)
        self.assertEqual(len(refresh_calls), 2)

    def test_failure_before_persist_can_resume_the_original_manifest(self):
        _, path = migration.write_plan(self.root)

        def fail_persist(rows):
            raise OSError('fixture before persistence')

        with self.assertRaisesRegex(OSError, 'before persistence'):
            migration.apply_manifest(self.root, path, fail_persist, lambda rows: None)
        self.assertEqual(migration._read(path)['status'], 'apply_error')
        self.assertNotIn('source_id', library.read(self.claims_dir / 'architecture.json')[0]['evidence'][0])

        recovered = migration.apply_manifest(self.root, path, self._persist_and_refresh,
                                             lambda rows: library.refresh(rows))
        self.assertEqual(recovered['status'], 'applied')

    def test_partially_or_differently_applied_state_fails_without_silent_repair(self):
        _, path = migration.write_plan(self.root)
        rows = library.read(self.claims_dir / 'architecture.json')
        rows[0]['evidence'][0]['source_id'] = 'f' * 64
        library.save(self.claims_dir / 'architecture.json', rows)
        with self.assertRaisesRegex(ValueError, 'reconciliación manual'):
            migration.apply_manifest(self.root, path, self._persist_and_refresh, lambda rows: None)
        self.assertEqual(library.read(self.claims_dir / 'architecture.json')[0]['evidence'][0]['source_id'],
                         'f' * 64)

    def test_preflight_rejects_stale_evidence_without_partial_mutation(self):
        manifest, path = migration.write_plan(self.root)
        rows = library.read(self.claims_dir / 'architecture.json')
        rows[0]['evidence'][0]['excerpt'] = 'Changed after preview'
        library.save(self.claims_dir / 'architecture.json', rows)
        persisted = []
        with self.assertRaises(ValueError):
            migration.apply_manifest(self.root, path, lambda data: persisted.append(data), lambda data: None)
        self.assertEqual(persisted, [])
        self.assertNotIn('source_id', library.read(self.claims_dir / 'architecture.json')[0]['evidence'][0])

    def test_foreign_or_malformed_identity_is_reported_not_replaced(self):
        rows = library.read(self.claims_dir / 'architecture.json')
        rows[0]['evidence'][0].update(source_id='bad', evidence_id='a' * 64,
                                      source_identity_policy='foreign-v9')
        plan = migration.build_plan(self.root, rows)
        self.assertEqual(plan['items'], [])
        self.assertEqual(plan['skipped'][0]['reason'], 'malformed_or_foreign_identity_fields')

    def test_linked_trusted_receipt_is_used_and_latest_is_never_consulted(self):
        evidence = copy.deepcopy(self.claim['evidence'][0])
        evidence['source_check_id'] = 'd' * 32
        snapshot = b'fixture page bytes'
        excerpt = evidence['excerpt']
        record = {'id': evidence['source_check_id'], 'policy': source_check.POLICY,
                  'original_url': evidence['url'], 'final_url': 'https://publisher.example/paper',
                  'normalized_final_url': 'publisher.example/paper', 'eligible': True,
                  'body_sha256': hashlib.sha256(snapshot).hexdigest(),
                  'snapshot_sha256': hashlib.sha256(snapshot).hexdigest(),
                  'excerpt_sha256': hashlib.sha256(excerpt.encode()).hexdigest(),
                  'checked_at': '2026-09-23T00:00:00Z'}
        directory = self.intel / 'source-checks'
        directory.mkdir()
        (directory / (evidence['source_check_id'] + '.json')).write_text(json.dumps(record), encoding='utf-8')
        (directory / (evidence['source_check_id'] + '.bin')).write_bytes(snapshot)
        (directory / (source_check.key(evidence) + '.latest')).write_text(json.dumps({'id': 'e' * 32}), encoding='utf-8')
        claim = copy.deepcopy(self.claim)
        claim['evidence'] = [evidence]
        with patch.object(source_check, 'latest', side_effect=AssertionError('latest must never be used')):
            candidate, _ = migration._inspect_evidence(self.root, claim, 0, evidence, set())
        expected = source_identity.identify(evidence, record)
        self.assertEqual(candidate['proposed_source_id'], expected['source_id'])
        self.assertEqual(candidate['identity_basis'], 'linked_trusted_source_check')
        self.assertIn('snapshot:' + record['body_sha256'], candidate['identity_signals'])

    def test_document_uses_only_registered_reviewed_identity_when_available(self):
        raw = b'%PDF-fixture original bytes'
        ident = hashlib.sha256(raw).hexdigest()
        folder = self.intel / 'documents' / ident
        folder.mkdir(parents=True)
        (folder / 'original.pdf').write_bytes(raw)
        library.save(folder / 'metadata.json', {'id': ident,
            'imports': [{'case_id': self.case_id}], 'identity_reviews': [{
                'case_id': self.case_id, 'decision': 'confirmed', 'doi': '10.1234/Reviewed'}]})
        meta = library.read(self.case_folder / 'case.json')
        meta['document_ids'] = [ident]
        library.save(self.case_folder / 'case.json', meta)
        evidence = {'type': 'document', 'document_id': ident, 'document_sha256': ident,
                    'excerpt': 'A long document passage associated with a legacy claim.'}
        claim = copy.deepcopy(self.claim)
        claim['evidence'] = [evidence]
        candidate, reason = migration._inspect_evidence(self.root, claim, 0, evidence, set())
        expected = source_identity.identify(evidence, reviewed_key=('doi', '10.1234/reviewed'))
        self.assertIsNone(reason)
        self.assertEqual(candidate['proposed_source_id'], expected['source_id'])
        self.assertEqual(candidate['identity_basis'], 'registered_document_review')


if __name__ == '__main__':
    unittest.main()
