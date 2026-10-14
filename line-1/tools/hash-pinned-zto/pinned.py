#!/usr/bin/env python3
"""Capture a portable ZTO snapshot with EIP-1898 hash-pinned public reads."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import runpy
import sys
import urllib.error
import urllib.request

# Reuse the existing strict JSON envelope and no-follow workspace file boundary.
B = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                       'bounded-rpc-snapshot' / 'snapshot.py'))
SAFE = B['SAFE_FILES']
SOURCE = B['DEFAULT_RPC']
ZTO = B['ZTO']
SCHEMA = 'line1-hash-pinned-zto-v1'
MAX_BYTES = 100000
HASH = re.compile(r'0x[0-9a-fA-F]{64}\Z')
QUANTITY = re.compile(r'0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)\Z')
READ_FIELDS = {'method', 'params', 'content_type', 'response', 'response_sha256'}
SELECTORS = {'0x18160ddd': 'totalSupply', '0x313ce567': 'decimals'}


class PinnedError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise PinnedError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def quantity(value):
    require(isinstance(value, str) and QUANTITY.fullmatch(value),
            'expected canonical hexadecimal quantity')
    return int(value, 16)


def validate_request(method, params):
    """A narrow fixed-purpose public allowlist; no downgrade to number selectors."""
    require(isinstance(params, list), 'parameters must be an array')
    if method == 'eth_chainId':
        require(params == [], 'chain ID takes no parameters')
    elif method == 'eth_getBlockByNumber':
        require(len(params) == 2 and params[1] is False,
                'block read must request transaction hashes only')
        if params[0] != 'finalized':
            quantity(params[0])
    elif method == 'eth_call':
        require(len(params) == 2, 'call requires two parameters')
        call, pin = params
        require(isinstance(call, dict) and set(call) == {'to', 'data'} and
                call['to'] == ZTO and isinstance(call['data'], str) and
                call['data'] in SELECTORS, 'only ZTO supply/decimals calls are allowed')
        require(isinstance(pin, dict) and set(pin) == {'blockHash', 'requireCanonical'} and
                isinstance(pin['blockHash'], str) and HASH.fullmatch(pin['blockHash']) and
                pin['requireCanonical'] is True,
                'state calls require blockHash and requireCanonical=true')
    else:
        raise PinnedError('method is not a permitted public read')


def rpc_read(method, params, timeout):
    validate_request(method, params)
    require(type(timeout) in (int, float) and 0 < timeout <= 60,
            'timeout must be within (0, 60] seconds')
    request = urllib.request.Request(SOURCE, data=canonical({
        'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}),
        method='POST', headers={'User-Agent': 'Pepeolithic-Line1-HashPinned/1.0',
                                'Content-Type': 'application/json',
                                'Accept': 'application/json',
                                'Accept-Encoding': 'identity'})
    # Do not consult environment proxy settings or follow redirects.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), B['NoRedirect']())
    try:
        with opener.open(request, timeout=timeout) as response:
            require(response.status == 200, 'RPC HTTP response was not 200')
            raw = response.read(MAX_BYTES + 1)
            require(len(raw) <= MAX_BYTES, 'RPC response exceeds byte limit')
            content_type = response.headers.get('Content-Type', '')
    except urllib.error.HTTPError as exc:
        raise PinnedError('RPC HTTP error ' + str(exc.code)) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise PinnedError('RPC transport failed') from exc
    answer = B['parse_json'](raw)
    B['validate_response'](answer)
    return {'method': method, 'params': params, 'content_type': content_type,
            'response': answer, 'response_sha256': digest(answer)}


def validate_read(read):
    require(isinstance(read, dict) and set(read) == READ_FIELDS,
            'read fields differ from schema')
    validate_request(read['method'], read['params'])
    require(isinstance(read['content_type'], str) and len(read['content_type']) <= 200,
            'invalid content type')
    response = read['response']
    require(isinstance(response, dict) and set(response) == {'jsonrpc', 'id', 'result'},
            'only exact successful RPC envelopes can be replayed')
    B['validate_response'](response)
    require(isinstance(read['response_sha256'], str) and
            read['response_sha256'] == digest(response), 'response checksum mismatch')
    return response['result']


def block_identity(value):
    require(isinstance(value, dict), 'missing block object')
    number = value.get('number')
    quantity(number)
    block_hash = value.get('hash')
    require(isinstance(block_hash, str) and HASH.fullmatch(block_hash), 'missing block hash')
    return number, block_hash


def validate_bundle(bundle):
    require(isinstance(bundle, dict) and set(bundle) ==
            {'schema', 'rpc_url', 'captured_at_utc', 'reads', 'reads_sha256'},
            'bundle fields differ from schema')
    require(bundle['schema'] == SCHEMA and bundle['rpc_url'] == SOURCE,
            'unexpected schema or public source')
    stamp = bundle['captured_at_utc']
    require(isinstance(stamp, str) and len(stamp) <= 64, 'invalid capture timestamp')
    try:
        moment = datetime.fromisoformat(stamp)
    except ValueError as exc:
        raise PinnedError('invalid capture timestamp') from exc
    require(moment.utcoffset() is not None and moment.utcoffset().total_seconds() == 0,
            'capture timestamp must be UTC')
    reads = bundle['reads']
    require(isinstance(reads, list) and len(reads) == 5, 'expected five ordered reads')
    results = [validate_read(read) for read in reads]
    require(bundle['reads_sha256'] == digest(reads), 'request/response bundle checksum mismatch')
    chain, anchor, supply, decimals, recheck = reads
    require(chain['method'] == 'eth_chainId' and chain['params'] == [] and
            results[0] == '0x1', 'first read must report Ethereum mainnet')
    require(anchor['method'] == 'eth_getBlockByNumber' and
            anchor['params'] == ['finalized', False], 'second read must select finalized block')
    number, block_hash = block_identity(results[1])
    pin = {'blockHash': block_hash, 'requireCanonical': True}
    for read, result, selector in zip((supply, decimals), results[2:4], SELECTORS):
        require(read['method'] == 'eth_call' and
                read['params'] == [{'to': ZTO, 'data': selector}, pin],
                'state read does not match the selected block hash and ZTO selector')
        require(isinstance(result, str) and HASH.fullmatch(result),
                'state result must be one ABI uint256 word')
    raw_supply = int(results[2], 16)
    places = int(results[3], 16)
    require(places <= 255, 'decimals result does not fit uint8')
    require(recheck['method'] == 'eth_getBlockByNumber' and
            recheck['params'] == [number, False], 'last read must recheck anchor height')
    require(block_identity(results[4]) == (number, block_hash), 'anchor changed between reads')
    # Exact decimal rendering: no floating point or invented token precision.
    digits = str(raw_supply).rjust(places + 1, '0')
    human = digits if places == 0 else digits[:-places] + '.' + digits[-places:]
    return {'chain_id': 1, 'block_number': quantity(number), 'block_hash': block_hash,
            'zto_address': ZTO, 'total_supply_raw': str(raw_supply),
            'decimals': places, 'total_supply_tokens': human,
            'state_selector': pin, 'evidence': 'RPC provider observations, not a state proof'}


def capture(timeout=15, read=None):
    """Optional read injection supports tests and explicitly provided transports."""
    require(type(timeout) in (int, float) and 0 < timeout <= 60,
            'timeout must be within (0, 60] seconds')
    read = rpc_read if read is None else read
    chain = read('eth_chainId', [], timeout)
    require(validate_read(chain) == '0x1', 'provider did not report Ethereum mainnet')
    anchor = read('eth_getBlockByNumber', ['finalized', False], timeout)
    number, block_hash = block_identity(validate_read(anchor))
    pin = {'blockHash': block_hash, 'requireCanonical': True}
    reads = [chain, anchor]
    for selector in SELECTORS:
        observation = read('eth_call', [{'to': ZTO, 'data': selector}, dict(pin)], timeout)
        validate_read(observation)
        reads.append(observation)
    reads.append(read('eth_getBlockByNumber', [number, False], timeout))
    bundle = {'schema': SCHEMA, 'rpc_url': SOURCE,
              'captured_at_utc': datetime.now(timezone.utc).isoformat(),
              'reads': reads, 'reads_sha256': digest(reads)}
    return bundle, validate_bundle(bundle)


def verify(path):
    return validate_bundle(B['parse_json'](SAFE['read_bytes'](path, MAX_BYTES)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--verify', help='replay a saved bundle offline')
    action.add_argument('--output', help='capture to a NEW visible workspace path')
    parser.add_argument('--timeout', type=float, default=15)
    args = parser.parse_args(argv)
    try:
        if args.verify:
            info = verify(args.verify)
        else:
            SAFE['parts'](args.output)
            bundle, info = capture(args.timeout)
            raw = (json.dumps(bundle, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
            SAFE['write_bytes'](args.output, raw, MAX_BYTES)
        print(json.dumps(info, indent=2, sort_keys=True))
        return 0
    except (PinnedError, B['SnapshotError'], OSError, ValueError, RecursionError) as exc:
        print('hash-pinned-zto: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
