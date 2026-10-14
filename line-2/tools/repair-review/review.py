#!/usr/bin/env python3
"""Compare structural violations before and after a JSON repair, offline."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import types


def bounded_module():
    # Bootstrap only the fixed, trusted sibling; user inputs use its no-follow reader.
    source = Path(__file__).absolute().parent.parent / 'bounded-contract' / 'check.py'
    relative = source.relative_to(Path.cwd()).as_posix()
    if any(not p or p.startswith('.') for p in relative.split('/')):
        raise ValueError('run inside the workspace containing the sibling tools')
    # Open each component without following links, including the trusted bootstrap.
    import os
    import stat
    directory = os.open('.', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    leaf = None
    try:
        parts = relative.split('/')
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=directory)
            os.close(directory)
            directory = child
        leaf = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                       dir_fd=directory)
        if not stat.S_ISREG(os.fstat(leaf).st_mode):
            raise ValueError('trusted sibling must be a regular file')
        chunks, remaining = [], 1_000_001
        while remaining:
            chunk = os.read(leaf, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        code = b''.join(chunks)
        if len(code) > 1_000_000:
            raise ValueError('trusted sibling exceeds byte limit')
    finally:
        if leaf is not None:
            os.close(leaf)
        os.close(directory)
    module = types.ModuleType('repair_bounded_contract')
    module.__file__ = str(source)
    exec(compile(code, str(source), 'exec'), module.__dict__)
    return module


def identity(error):
    return error['path'], error['rule'], error['message']


def partition(old, new):
    """Multiset comparison, retaining original validator ordering and multiplicity."""
    new_counts = Counter(map(identity, new))
    resolved, persistent = [], []
    for error in old:
        key = identity(error)
        if new_counts[key]:
            persistent.append(error)
            new_counts[key] -= 1
        else:
            resolved.append(error)
    old_counts = Counter(map(identity, old))
    introduced = []
    for error in new:
        key = identity(error)
        if old_counts[key]:
            old_counts[key] -= 1
        else:
            introduced.append(error)
    return resolved, persistent, introduced


def compare(engine, contract, before, after):
    old = engine.validate(before, contract)
    new = engine.validate(after, contract)
    resolved, persistent, introduced = partition(old, new)
    return {'valid': not new, 'before_valid': not old,
            'no_new_violations': not introduced,
            'summary': {'before': len(old), 'after': len(new),
                        'resolved': len(resolved), 'persistent': len(persistent),
                        'introduced': len(introduced)},
            'resolved': resolved, 'persistent': persistent, 'introduced': introduced}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('contract', help='one trusted contract used for both versions')
    parser.add_argument('before', help='relative workspace JSON path')
    parser.add_argument('after', help='relative workspace JSON path')
    parser.add_argument('--require-no-new', action='store_true',
                        help='exit 0 when no violations were introduced, even if some persist')
    args = parser.parse_args(argv)
    try:
        bounded = bounded_module()
        engine = bounded.engine_module()
        contract = engine.prepare(bounded.load(args.contract))
        result = compare(engine, contract, bounded.load(args.before), bounded.load(args.after))
        print(json.dumps(result, indent=2, ensure_ascii=True))
        accepted = result['no_new_violations'] if args.require_no_new else result['valid']
        return 0 if accepted else 1
    except (ValueError, OSError, RecursionError, AttributeError) as exc:
        print(json.dumps({'error': str(exc)}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
