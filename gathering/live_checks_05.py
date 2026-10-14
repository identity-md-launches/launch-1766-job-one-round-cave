#!/usr/bin/env python3
"""One-shot public Ethereum trials; no wallets, environment or line writes."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    if Path.cwd() != ROOT:
        raise SystemExit('Run from repository root')
    sys.path.insert(0, str(ROOT / 'shared/payment-evidence'))
    import corroborate
    agreement = module('live_agreement05', 'line-3/tools/provider-agreement/agreement.py')
    diagnostic = module('live_diagnostic05', 'line-3/tools/discovery-diagnostic/diagnose.py')
    pinned = module('live_pinned05', 'line-1/tools/hash-pinned-zto/pinned.py')
    rows = []
    # If a prior successful trial exists, replay it without clobbering evidence.
    path = ROOT / 'gathering/hash-pinned-round05.json'
    arguments = ['--verify', str(path.relative_to(ROOT))] if path.exists() else [
        '--output', str(path.relative_to(ROOT)), '--timeout', '6']
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = pinned.main(arguments)
    rows.append({'trial': 'ZTO hash-pinned capture/replay', 'exitCode': code,
                 'stdout': out.getvalue(), 'stderr': err.getvalue(),
                 'source': 'https://ethereum-rpc.publicnode.com'})
    print('ZTO hash-pinned capture/replay', code, flush=True)
    policy = corroborate.load('shared/payment-evidence/example.paired-policy.json')
    result = agreement.collect(policy)
    code = agreement.exit_code(result)
    if 'sample' in result:
        sample = result.pop('sample')
        _, intended = corroborate.request_for_pair(sample, policy)
        combined = corroborate.corroborate(sample, policy, intended, intended, summary=True)
        base = ROOT / 'shared/payment-evidence'
        for suffix, data in [('paired', sample), ('policy', policy),
                             ('intended', intended), ('corroboration', combined)]:
            raw = json.dumps(data, indent=2)+'\n'
            if len(raw.encode()) > 100000:
                raise ValueError('live evidence file exceeds deliverable byte limit')
            (base / f'round05.{suffix}.json').write_text(raw)
    rows.append({'trial': 'fresh two-provider ZTO payment', 'exitCode': code, 'result': result})
    print('fresh two-provider ZTO payment', code, flush=True)
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = diagnostic.main(['--discover', '--lookback', '512'])
    rows.append({'trial': 'bounded ZTO discovery', 'exitCode': code,
                 'stdout': out.getvalue(), 'stderr': err.getvalue(),
                 'source': 'https://ethereum-rpc.publicnode.com'})
    print('bounded ZTO discovery', code, flush=True)
    (ROOT / 'gathering/live-check-results-05.json').write_text(json.dumps(rows, indent=2)+'\n')
    return 0 if all(row['exitCode'] == 0 for row in rows) else 1


if __name__ == '__main__':
    sys.exit(main())
