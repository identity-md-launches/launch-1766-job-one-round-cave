"""Offline rejection/integration checks using the saved real ZTO observations."""
import copy
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import unittest
from unittest.mock import patch

P = runpy.run_path('line-1/tools/hash-pinned-zto/pinned.py')
LIVE = json.loads(P['SAFE']['read_bytes']('line-1/tools/hash-pinned-zto/live-zto.json', 100000))


class PinnedTests(unittest.TestCase):
    def setUp(self):
        self.bundle = copy.deepcopy(LIVE)

    def reseal(self):
        for read in self.bundle['reads']:
            read['response_sha256'] = P['digest'](read['response'])
        self.bundle['reads_sha256'] = P['digest'](self.bundle['reads'])

    def reject(self, reseal=True):
        if reseal:
            self.reseal()
        with self.assertRaises((P['PinnedError'], P['B']['SnapshotError'])):
            P['validate_bundle'](self.bundle)

    def test_real_offline_replay(self):
        result = P['verify']('line-1/tools/hash-pinned-zto/live-zto.json')
        self.assertEqual(result['total_supply_raw'], str(10**27))
        self.assertEqual(result['decimals'], 18)
        self.assertEqual(result['total_supply_tokens'], '1000000000.000000000000000000')

    def test_capture_requests_exact_hash(self):
        observations = iter(copy.deepcopy(LIVE['reads']))
        seen = []
        def read(method, params, timeout):
            record = next(observations)
            self.assertEqual((method, params), (record['method'], record['params']))
            seen.append(method)
            return record
        bundle, info = P['capture'](read=read)
        self.assertEqual(len(seen), 5)
        self.assertEqual(info['block_hash'], LIVE['reads'][1]['response']['result']['hash'])
        self.assertEqual(P['validate_bundle'](bundle), info)

    def test_no_number_downgrade(self):
        self.bundle['reads'][2]['params'][1] = LIVE['reads'][1]['response']['result']['number']
        self.reject()

    def test_no_latest_downgrade(self):
        self.bundle['reads'][3]['params'][1] = 'latest'
        self.reject()

    def test_wrong_real_hash_rejected_even_resealed(self):
        self.bundle['reads'][2]['params'][1]['blockHash'] = LIVE['reads'][1]['response']['result']['parentHash']
        self.reject()

    def test_require_canonical_exact_boolean(self):
        for value in [False, 1, 'true', None]:
            with self.subTest(value=value):
                self.bundle = copy.deepcopy(LIVE)
                self.bundle['reads'][2]['params'][1]['requireCanonical'] = value
                self.reject()

    def test_require_canonical_mandatory(self):
        del self.bundle['reads'][2]['params'][1]['requireCanonical']
        self.reject()

    def test_mixed_hash_and_number_refused(self):
        self.bundle['reads'][2]['params'][1]['blockNumber'] = LIVE['reads'][1]['response']['result']['number']
        self.reject()

    def test_wrong_token_rejected(self):
        self.bundle['reads'][2]['params'][0]['to'] = '0xd34a99bc0f67ae1bbd63c660e6d0b0dd03e263b7'
        self.reject()

    def test_wrong_selector_and_call_fields(self):
        for update in [{'data': '0x70a08231'}, {'from': P['ZTO']}, {'value': '0x1'}]:
            self.bundle = copy.deepcopy(LIVE)
            self.bundle['reads'][2]['params'][0].update(update)
            self.reject()

    def test_wrong_chain(self):
        self.bundle['reads'][0]['response']['result'] = '0xa'
        self.reject()

    def test_non_finalized_anchor(self):
        self.bundle['reads'][1]['params'][0] = LIVE['reads'][1]['response']['result']['number']
        self.reject()

    def test_changed_rechecked_hash(self):
        block = self.bundle['reads'][4]['response']['result']
        block['hash'] = block['parentHash']
        self.reject()

    def test_wrong_recheck_height(self):
        self.bundle['reads'][4]['params'][0] = hex(int(self.bundle['reads'][4]['params'][0], 16) - 1)
        self.reject()

    def test_read_order_and_missing_read(self):
        self.bundle['reads'][2:4] = reversed(self.bundle['reads'][2:4])
        self.reject()
        self.bundle = copy.deepcopy(LIVE)
        self.bundle['reads'].pop()
        self.reject()

    def test_bad_supply_and_decimals(self):
        for index, value in [(2, '0x'), (2, '0x1'), (2, None), (3, '0x' + format(256, '064x'))]:
            self.bundle = copy.deepcopy(LIVE)
            self.bundle['reads'][index]['response']['result'] = value
            self.reject()

    def test_uint8_precision_rendering_without_float(self):
        for places in [0, 6, 255]:
            self.bundle = copy.deepcopy(LIVE)
            self.bundle['reads'][3]['response']['result'] = '0x' + format(places, '064x')
            self.reseal()
            info = P['validate_bundle'](self.bundle)
            self.assertEqual(info['decimals'], places)
            self.assertEqual(info['total_supply_tokens'].replace('.', '').lstrip('0'), str(10**27))

    def test_both_checksum_layers(self):
        self.bundle['reads'][2]['response']['result'] = self.bundle['reads'][3]['response']['result']
        self.reject(reseal=False)
        self.bundle = copy.deepcopy(LIVE)
        self.bundle['reads'][2]['content_type'] = 'altered'
        self.reject(reseal=False)

    def test_error_envelope_and_bool_id(self):
        for response in [{'jsonrpc': '2.0', 'id': 1, 'error': {'code': -32000, 'message': 'not canonical'}},
                         {'jsonrpc': '2.0', 'id': True, 'result': '0x1'}]:
            self.bundle = copy.deepcopy(LIVE)
            self.bundle['reads'][0]['response'] = response
            self.reject()

    def test_unknown_fields_source_and_timestamp(self):
        for key, value in [('extra', True), ('rpc_url', 'https://eth.drpc.org'),
                           ('captured_at_utc', '2026-10-14T01:00:00'),
                           ('captured_at_utc', '2026-10-14T01:00:00+02:00')]:
            self.bundle = copy.deepcopy(LIVE)
            self.bundle[key] = value
            self.reject()

    def test_send_sign_and_other_methods_refused(self):
        for method in ['eth_sendRawTransaction', 'eth_sendTransaction', 'eth_sign',
                       'personal_sign', 'eth_getBalance', 'eth_getStorageAt']:
            with self.subTest(method=method), self.assertRaises(P['PinnedError']):
                P['validate_request'](method, [])

    def test_invalid_hash_and_block_quantity(self):
        for value in ['0x1', None, 123, '0x' + 'g'*64]:
            self.bundle = copy.deepcopy(LIVE)
            self.bundle['reads'][2]['params'][1]['blockHash'] = value
            self.reject()
        for value in ['0x00', True, {}, None]:
            with self.assertRaises(P['PinnedError']):
                P['validate_request']('eth_getBlockByNumber', [value, False])

    def test_invalid_timeout(self):
        for timeout in [0, -1, 61, float('nan'), float('inf'), True]:
            with self.subTest(timeout=timeout), self.assertRaises(P['PinnedError']):
                P['capture'](timeout=timeout)

    def test_rpc_failure_never_downgrades(self):
        calls = []
        def fail(method, params, timeout):
            calls.append((method, params))
            if len(calls) < 3:
                return copy.deepcopy(LIVE['reads'][len(calls)-1])
            raise P['PinnedError']('provider does not support blockHash')
        with self.assertRaises(P['PinnedError']):
            P['capture'](read=fail)
        self.assertEqual(len(calls), 3)
        self.assertIs(calls[-1][1][1]['requireCanonical'], True)

    def test_transport_bounds_and_headers(self):
        class Response(io.BytesIO):
            status = 200
            headers = {'Content-Type': 'application/json'}
        good = Response(json.dumps(LIVE['reads'][0]['response']).encode())
        opener = unittest.mock.Mock()
        opener.open.return_value = good
        with patch.object(P['urllib'].request, 'build_opener', return_value=opener):
            self.assertEqual(P['rpc_read']('eth_chainId', [], 15)['response']['result'], '0x1')
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, P['SOURCE'])
        self.assertIn('HashPinned', request.get_header('User-agent'))
        opener.open.return_value = Response(b'x' * (P['MAX_BYTES']+1))
        with patch.object(P['urllib'].request, 'build_opener', return_value=opener), self.assertRaises(P['PinnedError']):
            P['rpc_read']('eth_chainId', [], 15)

    def test_parser_rejects_duplicate_keys_and_nonfinite(self):
        for raw in [b'{"x":1,"x":2}', b'{"x":NaN}']:
            with self.assertRaises(P['B']['SnapshotError']):
                P['B']['parse_json'](raw)

    def test_file_and_cli_integration(self):
        area = Path('test/scratch/hash-pinned-' + str(os.getpid()))
        area.mkdir(parents=True)
        try:
            valid = area/'valid.json'
            raw = (json.dumps(LIVE) + '\n').encode()
            P['SAFE']['write_bytes'](valid, raw, P['MAX_BYTES'])
            with patch.object(P['sys'], 'stdout', io.StringIO()):
                self.assertEqual(P['main'](['--verify', str(valid)]), 0)
            with self.assertRaises(FileExistsError):
                P['SAFE']['write_bytes'](valid, raw, P['MAX_BYTES'])
            (area/'alias').symlink_to('valid.json')
            with self.assertRaises(OSError):
                P['verify'](area/'alias')
            for path in ['../input', '.secret', '/tmp/input']:
                with self.assertRaises(ValueError):
                    P['verify'](path)
            (area/'large').write_bytes(b'x' * (P['MAX_BYTES']+1))
            with self.assertRaises(ValueError):
                P['verify'](area/'large')
        finally:
            shutil.rmtree(area)


if __name__ == '__main__':
    unittest.main(verbosity=2)
