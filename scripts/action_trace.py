"""Observable provider tool events, excluding model reasoning and tool contents."""
import json
import re
from collections import Counter
from pathlib import Path
from functools import lru_cache

VISIBLE_ACTION_LIMIT = 80


def _normalized_target(value):
    """Conservative grouping key; never changes the preserved display value."""
    return re.sub(r'\s+', ' ', (value or '').strip()).casefold()


@lru_cache(maxsize=48)
def _read_trace(path, modified, size):
    if size > 20 * 1024 * 1024:
        return {'actions': [], 'total': 0, 'visible': 0, 'omitted': 0,
                'counts': {}, 'query_groups': [], 'unreadable': 'too_large'}
    actions = {}
    with Path(path).open(encoding='utf-8') as stream:
        for line in stream:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event,dict): continue
            step = event.get('step_update', {})
            if not isinstance(step,dict): continue
            if step.get('step_type') != 'tool':
                continue
            key = (step.get('conversation_id'), step.get('step_index'))
            info = step.get('tool_info') or {}
            params = info.get('parameters') or {}
            row = actions.setdefault(key, {'step': step.get('step_index'), 'tool': '', 'target': '', 'state': ''})
            row['tool'] = step.get('tool_name') or info.get('name') or row['tool']
            row['state'] = step.get('state') or row['state']
            for name in ('Url', 'url', 'query', 'Query', 'AbsolutePath', 'path', 'DirectoryPath', 'SearchPath'):
                if isinstance(params.get(name), str):
                    row['target'] = params[name][:1200]
                    break
            if info.get('error'):
                row['error'] = 'La herramienta registró un error; consulta el registro de ejecución.'
    all_actions = list(actions.values())
    visible = all_actions[-VISIBLE_ACTION_LIMIT:]
    counts = Counter(row.get('tool') or 'unknown' for row in all_actions)
    query_groups = {}
    for index, row in enumerate(all_actions):
        if row.get('tool') != 'search_web' or not row.get('target'):
            continue
        key = _normalized_target(row['target'])
        group = query_groups.setdefault(key, {'query': row['target'], 'occurrences': 0,
                                              'first_action': index + 1})
        group['occurrences'] += 1
    groups = []
    for group in query_groups.values():
        groups.append({**group, 'repeated': max(0, group['occurrences'] - 1)})
    return {'actions': visible, 'all_actions': all_actions, 'total': len(all_actions), 'visible': len(visible),
            'omitted': max(0, len(all_actions) - len(visible)), 'counts': dict(counts),
            'query_groups': groups, 'unreadable': None}


def _read(path, modified, size):
    """Legacy list interface retained for callers that render individual rows."""
    return _read_trace(path, modified, size)['actions']


def for_claim(root, claim):
    result = []
    for event in claim.get('provenance', [])[-1:]:
        ident = event.get('run_id', '')
        if not re.fullmatch(r'[A-Za-z0-9_-]+', ident):
            continue
        for stage in ('pass2', 'pass3'):
            source_run=stage_run(event,stage)
            if not source_run:continue
            path = root / '.project-intelligence/evidence' / (source_run + '_' + stage + '.raw.json')
            if path.is_file():
                stat = path.stat()
                scope=attribution(root,source_run,stage,claim.get('id'))
                label = {'single_claim': 'Ejecución iniciada para esta afirmación',
                         'batch': 'Ejecución iniciada para un lote que incluye esta afirmación',
                         'unknown': 'No se pudo determinar qué afirmaciones iniciaron esta ejecución'}[scope]
                result.extend({**row, 'stage': stage, 'run_id': source_run,'reused':source_run!=ident,
                               'attribution':scope, 'attribution_label': label}
                              for row in _read(str(path), stat.st_mtime_ns, stat.st_size))
    return result


def summary_for_claim(root, claim):
    """Return pre-truncation totals without exposing model reasoning or tool contents."""
    stages = []
    total_counts = Counter()
    total = visible = omitted = 0
    query_groups = {}
    for event in claim.get('provenance', [])[-1:]:
        current_run = event.get('run_id', '')
        for stage in ('pass2', 'pass3'):
            source_run = stage_run(event, stage)
            if not source_run:
                continue
            path = root / '.project-intelligence/evidence' / (source_run + '_' + stage + '.raw.json')
            if not path.is_file():
                continue
            stat = path.stat()
            trace = _read_trace(str(path), stat.st_mtime_ns, stat.st_size)
            reused = source_run != current_run
            stages.append({'stage': stage, 'run_id': source_run, 'reused': reused,
                           'total': trace['total'], 'visible': trace['visible'],
                           'omitted': trace['omitted'], 'counts': trace['counts']})
            total += trace['total']; visible += trace['visible']; omitted += trace['omitted']
            total_counts.update(trace['counts'])
            for group in trace['query_groups']:
                key = _normalized_target(group['query'])
                merged = query_groups.setdefault(key, {'query': group['query'], 'occurrences': 0,
                                                        'reused_occurrences': 0})
                merged['occurrences'] += group['occurrences']
                if reused:
                    merged['reused_occurrences'] += group['occurrences']
    groups = []
    for group in query_groups.values():
        groups.append({**group, 'repeated': max(0, group['occurrences'] - 1)})
    return {'total': total, 'visible': visible, 'omitted': omitted,
            'counts': dict(total_counts), 'query_groups': groups, 'stages': stages}


def export_for_claim(root, claim):
    """Complete observable tool list for explicit professional download."""
    actions=[]
    for event in claim.get('provenance', [])[-1:]:
        current=event.get('run_id','')
        for stage in ('pass2','pass3'):
            ident=stage_run(event,stage)
            if not ident:continue
            path=root/'.project-intelligence/evidence'/f'{ident}_{stage}.raw.json'
            if not path.is_file():continue
            stat=path.stat();scope=attribution(root,ident,stage,claim.get('id'))
            actions.extend({**row,'stage':stage,'run_id':ident,'reused':ident!=current,
                            'attribution':scope} for row in _read_trace(str(path),stat.st_mtime_ns,stat.st_size).get('all_actions',[]))
    return {'claim_id':claim.get('id'),'summary':summary_for_claim(root,claim),'actions':actions}


def stage_run(event,stage):
    key='collector_result' if stage=='pass2' else 'skeptic_result'
    reference=event.get(key)
    if reference:
        match=re.fullmatch(r'evidence/([A-Za-z0-9_-]+)_'+stage+r'\.json',reference)
        return match[1] if match else None
    ident=event.get('run_id','')
    return ident if re.fullmatch(r'[A-Za-z0-9_-]+',ident) else None


def attribution(root,run_id,stage,claim_id):
    manifest=root/'.project-intelligence/evidence'/f'{run_id}_{stage}.manifest.json'
    try:
        value=json.loads(manifest.read_text(encoding='utf-8'))
        if value.get('run_id')==run_id and value.get('stage')==stage:
            ids=value.get('claim_ids')
            if ids==[claim_id]:return 'single_claim'
            if isinstance(ids,list) and claim_id in ids:return 'batch'
    except (OSError,ValueError,TypeError):pass
    path=root/'.project-intelligence/evidence'/f'{run_id}_{stage}.input.json'
    try:
        if path.stat().st_size>2*1024*1024:return 'unknown'
        message=json.loads(path.read_text(encoding='utf-8'))
        data=json.loads(message['message']['content'].rsplit('\n\nDATOS:\n',1)[1])
        rows=data.get('claims',[]) if isinstance(data,dict) else data
        ids=[c['id'] for c in rows]
        if ids==[claim_id]:return 'single_claim'
        if claim_id in ids:return 'batch'
    except (OSError,ValueError,KeyError,TypeError,IndexError):pass
    return 'unknown'


def receipts_for_claim(root,claim):
    result=[]
    for event in claim.get('provenance',[])[-1:]:
        for stage in ('pass2','pass3'):
            ident=stage_run(event,stage)
            if not ident:continue
            path=root/'.project-intelligence/execution-receipts'/f'{ident}_{stage}.json'
            try:
                receipt=json.loads(path.read_text(encoding='utf-8'))
                if receipt['run_id']!=ident or receipt['stage']!=stage:continue
                result.append({**receipt,'reused':ident!=event.get('run_id')})
            except (OSError,ValueError,KeyError,TypeError):continue
    return result
