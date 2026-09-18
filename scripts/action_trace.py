"""Observable provider tool events, excluding model reasoning and tool contents."""
import json
import re
from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=48)
def _read(path, modified, size):
    if size > 20 * 1024 * 1024:
        return []
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
    return list(actions.values())[-80:]


def for_claim(root, claim):
    result = []
    for event in claim.get('provenance', [])[-1:]:
        ident = event.get('run_id', '')
        if not re.fullmatch(r'[A-Za-z0-9_-]+', ident):
            continue
        for stage in ('pass2', 'pass3'):
            path = root / '.project-intelligence/evidence' / (ident + '_' + stage + '.raw.json')
            if path.is_file():
                stat = path.stat()
                result.extend({**row, 'stage': stage, 'run_id': ident} for row in _read(str(path), stat.st_mtime_ns, stat.st_size))
    return result
