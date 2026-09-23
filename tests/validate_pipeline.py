import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE / 'scripts'))
spec = importlib.util.spec_from_file_location('pipeline', SOURCE / 'scripts/pipeline.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
calls = []
fail_writer = False


def fake(self, stage, instructions, data, investigator=False):
    calls.append(stage)
    if stage == 'pass1':
        group = 'changes' if 'category debe ser "changes"' in instructions else 'architecture'
        return [{'claim': name, 'category': group, 'status': 'UNVERIFIED',
                 'requires_external': False, 'hypothesis_source': 'DO_NOT_SEND_TO_SKEPTIC'}
                for name in ('supported', 'partial', 'unsupported', 'contradicted')]
    if stage == 'pass2':
        return [{'id': c['id'], 'claim': c['claim'], 'status': 'UNVERIFIED',
                 'evidence': [] if c['claim'] == 'unsupported' else
                 [{'type': 'file', 'path': 'src/app.txt', 'lines': '1-1',
                   'excerpt': (p.ROOT / 'src/app.txt').read_text().splitlines()[0]}]}
                for c in data['claims']]
    if stage == 'pass3':
        assert isinstance(data, list)
        assert all(set(c) == {'id', 'claim', 'evidence'} for c in data)
        assert 'DO_NOT_SEND_TO_SKEPTIC' not in json.dumps(data)
        statuses = dict(zip(('supported', 'partial', 'unsupported', 'contradicted'), p.FINAL))
        return [{**c, 'evidence': [{**e, 'relation': 'contradiction' if c['claim']=='contradicted' else 'support',
                 'semantic_review':{'target_claim_id':c['id'],'decision':'contradiction' if c['claim']=='contradicted' else 'support',
                 'basis':'fixture exact passage review','limits':'','reviewer':'pass3'}} for e in c['evidence']], 'status': statuses[c['claim']], 'skeptic_note': 'reviewed',
                 'domain': 'general', 'sensible': False, 'favorable': False,
                 'primary_sources': [{'evidence_index': 0, 'independence_group': 'fixture', 'reason': 'source'}] if c['evidence'] else [],
                 'contradiction_search': 'checked source and counterexamples'} for c in data]
    if stage == 'pass4':
        assert all(c['status'] == 'VERIFIED' for c in data)
        if fail_writer:
            raise ValueError('simulated Writer failure')
        return [{'id': c['id'], 'text': 'verified publication ' + c['claim']} for c in data]
    raise AssertionError(stage)


def run(*args):
    with patch.object(sys, 'argv', ['pipeline.py', *args]), patch.object(p.shutil, 'which', return_value='gemini'), patch.object(p.Runner, 'call', fake):
        p.main()


Path('work').mkdir(exist_ok=True)

with tempfile.TemporaryDirectory(prefix='gemini_pipeline_', dir=Path('work').resolve()) as tmp:
    root = Path(tmp)
    shutil.copy2(SOURCE / 'GEMINI.md', root / 'GEMINI.md')
    # Synthetic fixtures must not copy private cases or depend on their path lengths.
    p.initialize(root)
    (root / '.project-intelligence/pipeline.lock').unlink(missing_ok=True)
    (root / '.project-intelligence/obsidian.json').unlink(missing_ok=True)
    for name in p.GROUPS:
        (root / '.project-intelligence/claims' / (name + '.json')).write_text('[]\n')
    (root / '.project-intelligence/state.json').write_text(json.dumps({'last_run': None, 'last_commit': None, 'claims': {s: 0 for s in p.FINAL}, 'unverified': 0, 'obsidian': {'status': 'NOT_CONFIGURED', 'pending_files': []}}))
    (root / 'src/app.txt').write_text('hello\n')
    p.ROOT, p.INTEL = root, root / '.project-intelligence'
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    p.git('config', 'user.email', 'test@example.invalid')
    p.git('config', 'user.name', 'Temporary Validation')
    p.git('add', '.')
    p.git('commit', '-qm', 'Initial fixture')
    run('research', 'fixture')
    assert len(p.all_claims()) == 4
    original_doc = (root / 'docs/architecture.md').read_text()
    fail_writer = True
    try:
        run('document')
        raise AssertionError('Writer failure did not stop publication')
    except ValueError as exc:
        assert 'simulated' in str(exc)
    assert (root / 'docs/architecture.md').read_text() == original_doc
    assert p.load(p.INTEL / 'state.json')['claims'] == {s: 1 for s in p.FINAL}
    assert not (p.INTEL / 'pipeline.lock').exists()
    fail_writer = False
    before = len(calls)
    run('document')
    assert calls[before:] == ['pass4']
    publication = (root / 'docs/architecture.md').read_text()
    assert 'verified publication supported' in publication
    reviewed = p.all_claims()[0]
    assert reviewed['provenance'][-1]['collector_result'].endswith('_pass2.json')
    assert reviewed['writing_history'][-1]['writer_result'].endswith('_pass4.json')
    sources = (p.INTEL / 'reports/sources.md').read_text(encoding='utf-8')
    assert 'SHA-256 del extracto' in sources and 'Writer' in sources
    assert not any(word in publication for word in ('partial', 'unsupported', 'contradicted'))
    run('document')
    assert p.load(p.INTEL / 'state.json')['claims'] == {s: 1 for s in p.FINAL}
    before = len(calls)
    fail_writer = True
    try:
        run('changelog')
        raise AssertionError('Writer failure did not stop changelog')
    except ValueError as exc:
        assert 'simulated' in str(exc)
    assert p.load(p.INTEL / 'state.json')['last_commit'] is None
    assert len(p.all_claims()) == 8
    fail_writer = False
    before = len(calls)
    run('changelog')
    assert calls[before:] == ['pass4']
    assert len(p.all_claims()) == 8
    assert p.load(p.INTEL / 'state.json')['last_commit'] == p.git('rev-parse', 'HEAD').strip()
    assert len(list((root / 'docs/changelog').glob('*.md'))) == 1
    before = len(calls)
    run('changelog')
    assert len(calls) == before
    (root / 'src/app.txt').write_text('world\n')
    p.git('add', 'src/app.txt')
    p.git('commit', '-qm', 'Second fixture change')
    run('changelog')
    assert len(list((root / 'docs/changelog').glob('*.md'))) == 2
    assert p.load(p.INTEL / 'state.json')['claims'] == {s: 3 for s in p.FINAL}
    # Embedded errors and malformed responses must preserve raw output and fail.
    with patch.object(p.shutil, 'which', return_value='gemini'):
        runner = p.Runner()
    # This fixture validates parsing and raw-output preservation without
    # launching a real provider process.  Runner defaults to incremental
    # Popen in production, while the deterministic test stubs subprocess.run.
    runner.incremental = False
    for output in ('{"error":{"message":"failed"}}', '{"response":"not JSON"}'):
        proc = subprocess.CompletedProcess([], 0, stdout=output.encode(), stderr=b'fixture log')
        with patch.object(p.subprocess, 'run', return_value=proc):
            try:
                runner.call('invalid', '', [])
                raise AssertionError('Invalid response accepted')
            except ValueError:
                pass
        assert (p.INTEL / 'evidence' / (runner.run_id + '_invalid.raw.json')).read_text() == output
    try:
        p.matched([], [{'id': 'missing', 'claim': 'x'}])
        raise AssertionError('Dropped claim accepted')
    except ValueError:
        pass
    try:
        p.check_evidence([{'type': 'file', 'path': 'src/app.txt', 'lines': '1-999', 'excerpt': 'world'}])
        raise AssertionError('Invalid line range accepted')
    except ValueError:
        pass
    try:
        p.check_evidence([{'type': 'external', 'url': 'https://example.invalid', 'excerpt': 'x'}])
        raise AssertionError('Unfetched external source accepted')
    except ValueError:
        pass
    with patch.dict(p.os.environ, {'OBSIDIAN_SYNC_HOOK': 'fixture-hook'}), patch.object(p.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)):
        try:
            p.sync_docs([])
            raise AssertionError('Sync failure hidden')
        except ValueError:
            pass
    assert p.load(p.INTEL / 'state.json')['obsidian']['status'] == 'FAILED'
    assert p.load(p.INTEL / 'state.json')['obsidian']['pending_files']
    with patch.dict(p.os.environ, {'OBSIDIAN_SYNC_HOOK': 'fixture-hook'}), patch.object(p.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)):
        p.sync_docs([])
    assert p.load(p.INTEL / 'state.json')['obsidian'] == {'status': 'SYNCED', 'pending_files': []}
print('PASS: isolated four-pass flow, strict VERIFIED gate, retry without duplicate counts, incremental commits, raw error preservation, claim IDs, evidence validation and sync retry.')
