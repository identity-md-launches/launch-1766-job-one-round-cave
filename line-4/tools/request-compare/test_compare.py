"""Commitment comparison and fail-closed CLI regressions."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import request_compare
from request_compare import compare
from typed_digest import TypedDataError, load_workspace_json

HERE = Path(__file__).resolve().parent


def request(kind, value):
    return {'types': {'EIP712Domain': [], 'Data': [{'name': 'value', 'type': kind}]},
            'primaryType': 'Data', 'domain': {}, 'message': {'value': value}}


class CompareTests(unittest.TestCase):
    def setUp(self):
        self.data = load_workspace_json(HERE/'zto-intended.json')

    def paths(self, result):
        return {row['path'] for row in result['differences']}

    def test_historical_zto_matches(self):
        r = compare(self.data, self.data)
        self.assertTrue(r['accepted'])
        self.assertEqual(r['differenceCount'], 0)
        self.assertEqual(r['intended']['digest'],
                         '0xf33e2506e5c103f98dbfe3feb6d4b87d55f1fad4e423dbaa8462465ff4ab9774')

    def test_one_raw_zto_unit_rejected(self):
        r = compare(self.data, load_workspace_json(HERE/'zto-altered.json'))
        self.assertFalse(r['accepted'])
        self.assertFalse(r['digestMatches'])
        self.assertEqual(self.paths(r), {'/message', '/message/minimumRaw'})

    def test_wrong_chain(self):
        x = copy.deepcopy(self.data)
        x['domain']['chainId'] = 2
        r = compare(self.data, x)
        self.assertFalse(r['accepted'])
        self.assertEqual(self.paths(r), {'/domain', '/domain/chainId'})

    def test_equivalent_integer_address_and_object_order(self):
        x = copy.deepcopy(self.data)
        x['message']['minimumRaw'] = hex(int(x['message']['minimumRaw']))
        x['message']['token'] = '0x'+x['message']['token'][2:].upper()
        x['message'] = dict(reversed(list(x['message'].items())))
        self.assertTrue(compare(self.data, x)['accepted'])

    def test_schema_order_diff_even_when_field_values_match(self):
        x = copy.deepcopy(self.data)
        x['types']['PaymentEvidence'].reverse()
        r = compare(self.data, x)
        self.assertFalse(r['accepted'])
        self.assertEqual(self.paths(r), {'/message'})

    def test_same_atomic_word_different_type(self):
        r = compare(request('uint8', 1), request('uint256', 1))
        self.assertFalse(r['accepted'])
        self.assertIn('/message/value', self.paths(r))

    def test_array_reorder_and_added_node(self):
        left = request('uint8[]', [1, 2])
        self.assertFalse(compare(left, request('uint8[]', [2, 1]))['accepted'])
        r = compare(left, request('uint8[]', [1, 2, 3]))
        row = next(x for x in r['differences'] if x['path']=='/message/value/2')
        self.assertIsNone(row['intended'])
        self.assertEqual(row['reason'], 'client encoding node added')
        r = compare(request('uint8[]', [1]), left)
        self.assertIn('/message/value/1', self.paths(r))
        r = compare(left, request('uint8[]', [1]))
        self.assertTrue(any(x['reason']=='intended encoding node missing' for x in r['differences']))

    def test_empty_array_schema_still_bound(self):
        self.assertFalse(compare(request('uint8[]', []), request('uint256[]', []))['accepted'])

    def test_nested_struct_field(self):
        left = {'types': {'EIP712Domain': [],
                         'Data': [{'name':'value','type':'Child'}],
                         'Child': [{'name':'amount','type':'uint256'}]},
                'primaryType':'Data','domain':{},'message':{'value':{'amount':1}}}
        right = copy.deepcopy(left)
        right['message']['value']['amount'] = 2
        self.assertEqual(self.paths(compare(left,right)),
                         {'/message','/message/value','/message/value/amount'})

    def test_unicode_is_exact_not_normalized(self):
        self.assertFalse(compare(request('string','\u00e9'),request('string','e\u0301'))['accepted'])

    def test_unused_declarations_do_not_change_commitment(self):
        x = copy.deepcopy(self.data)
        x['types']['Unused'] = [{'name':'v','type':'bool'}]
        self.assertTrue(compare(self.data,x)['accepted'])

    def test_primary_rename(self):
        x = copy.deepcopy(self.data)
        x['types']['Other'] = x['types'].pop('PaymentEvidence')
        x['primaryType'] = 'Other'
        self.assertIn('/primaryType',self.paths(compare(self.data,x)))

    def test_no_mutation(self):
        before=copy.deepcopy(self.data)
        compare(self.data,self.data)
        self.assertEqual(before,self.data)

    def test_invalid_side_rejected(self):
        for a,b in ((request('uint8',256),self.data),(self.data,request('bool',1))):
            with self.assertRaises(TypedDataError): compare(a,b)

    def test_report_limit_refuses_without_truncation(self):
        with patch.object(request_compare,'MAX_REPORT_BYTES',100):
            with self.assertRaisesRegex(TypedDataError,'report limit'):
                compare(self.data,self.data)


class CliTests(unittest.TestCase):
    def run_cli(self,*args):
        return subprocess.run([sys.executable,'-B',str(HERE/'request_compare.py'),*map(str,args)],
                              capture_output=True,text=True,timeout=15)

    def test_match_and_mismatch_exit_codes_full_and_summary(self):
        for flags in ([],['--summary']):
            for name,code in (('zto-intended.json',0),('zto-altered.json',1)):
                p=self.run_cli(HERE/'zto-intended.json',HERE/name,*flags)
                self.assertEqual(p.returncode,code,p.stderr)
                r=json.loads(p.stdout)
                self.assertEqual(r['accepted'],code==0)
                self.assertEqual('differences' in r,not bool(flags))

    def test_bad_paths_each_side(self):
        for path in ('../outside.json','.hidden.json'):
            for a,b in ((path,HERE/'zto-intended.json'),(HERE/'zto-intended.json',path)):
                p=self.run_cli(a,b)
                self.assertEqual(p.returncode,2)
                self.assertEqual(p.stdout,'')
                self.assertNotIn('Traceback',p.stderr)

    def test_malformed_duplicate_oversized_symlink(self):
        scratch=Path('test/scratch');scratch.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch,prefix='compare-') as folder:
            f=Path(folder)/'bad.json'
            for raw in (b'{',b'{"a":1,"a":2}',b' '*65537):
                f.write_bytes(raw)
                p=self.run_cli(HERE/'zto-intended.json',f)
                self.assertEqual(p.returncode,2)
                self.assertEqual(p.stdout,'')
            link=Path(folder)/'link.json'
            link.symlink_to(f.name)
            self.assertEqual(self.run_cli(link,HERE/'zto-intended.json').returncode,2)


if __name__=='__main__': unittest.main()
