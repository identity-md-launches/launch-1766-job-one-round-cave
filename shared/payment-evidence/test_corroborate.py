"""Acceptance gates using real saved ZTO evidence; edits are rejection fixtures."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import corroborate as c

HERE = Path(__file__).resolve().parent


class CorroborationTests(unittest.TestCase):
    def setUp(self):
        self.sample = c.load(HERE / 'example.paired.json')
        self.policy = copy.deepcopy(self.sample['policy'])
        _, self.intended = c.request_for_pair(self.sample, self.policy)
        self.client = copy.deepcopy(self.intended)

    def result(self, summary=True):
        return c.corroborate(self.sample, self.policy, self.intended, self.client, summary)

    def test_actual_paired_zto_observations(self):
        result = self.result()
        self.assertTrue(result['accepted'])
        self.assertFalse(result['providerAuthenticated'])
        self.assertEqual(result['settlementAndAgreement']['state'], 'corroborated')
        self.assertEqual(self.intended['message']['token'], c.agreement.w.TOKENS['ZTO'])
        for field in ('firstTranscriptHash', 'secondTranscriptHash'):
            self.assertEqual(len(self.intended['message'][field]), 66)

    def test_policy_cannot_be_lowered_in_paired_file(self):
        self.sample['policy']['minimum_raw'] = '1'
        with self.assertRaisesRegex(ValueError, 'independently supplied policy'):
            self.result()

    def test_matching_requests_cannot_bypass_payment_shortfall(self):
        self.policy['minimum_raw'] = str(int(self.policy['minimum_raw']) + 1)
        self.sample['policy'] = copy.deepcopy(self.policy)
        _, self.intended = c.request_for_pair(self.sample, self.policy)
        self.client = copy.deepcopy(self.intended)
        result = self.result()
        self.assertFalse(result['accepted'])
        self.assertFalse(result['paymentAccepted'])
        self.assertTrue(result['evidenceMatchesIntended'])
        self.assertTrue(result['clientMatchesIntended'])

    def test_agreed_amount_cannot_hide_different_events(self):
        for read in self.sample['providers'][1]['reads']:
            if read['method'] == 'eth_getTransactionReceipt':
                event = next(log for log in read['result']['logs']
                             if log['address'].lower() == c.agreement.w.TOKENS['ZTO'])
                # Real observed recipient substituted as sender in a rejection fixture.
                event['topics'][1] = '0x' + '0' * 24 + self.policy['recipient'][2:]
        result = self.result()
        self.assertFalse(result['accepted'])
        self.assertEqual(result['settlementAndAgreement']['state'], 'evidence_disagreement')

    def test_client_amount_change_rejected(self):
        self.client['message']['minimumRaw'] = str(int(self.policy['minimum_raw']) + 1)
        result = self.result(summary=False)
        self.assertTrue(result['paymentAccepted'])
        self.assertTrue(result['evidenceMatchesIntended'])
        self.assertFalse(result['clientMatchesIntended'])
        self.assertFalse(result['accepted'])
        self.assertIn('/message/minimumRaw',
                      {row['path'] for row in result['clientBinding']['differences']})

    def test_intended_and_client_match_cannot_override_evidence(self):
        self.intended['message']['minimumRaw'] = str(int(self.policy['minimum_raw']) + 1)
        self.client = copy.deepcopy(self.intended)
        result = self.result()
        self.assertFalse(result['accepted'])
        self.assertTrue(result['clientMatchesIntended'])
        self.assertFalse(result['evidenceMatchesIntended'])

    def test_complete_domain_is_bound(self):
        self.intended['domain']['chainId'] = 2
        self.client = copy.deepcopy(self.intended)
        result = self.result()
        self.assertTrue(result['clientMatchesIntended'])
        self.assertFalse(result['evidenceMatchesIntended'])
        self.assertFalse(result['accepted'])

    def test_schema_order_and_source_swaps_rejected(self):
        for kind in ('schema', 'sources'):
            client = copy.deepcopy(self.intended)
            if kind == 'schema':
                client['types'][c.PRIMARY].reverse()
            else:
                a, b = ('firstSource', 'secondSource') if kind == 'sources' else (
                    'firstTranscriptHash', 'secondTranscriptHash')
                client['message'][a], client['message'][b] = client['message'][b], client['message'][a]
            with self.subTest(kind=kind):
                self.assertFalse(c.corroborate(self.sample, self.policy, self.intended, client)['accepted'])

    def test_distinct_transcript_hash_swap_rejected(self):
        # Actual saved provider reads can be byte-identical. Add explicit test
        # metadata to distinguish the second fixture without changing payment.
        for read in self.sample['providers'][1]['reads']:
            if read['method'] == 'eth_getTransactionReceipt':
                read['result']['gatheringTestMetadata'] = 'rejection fixture'
        _, self.intended = c.request_for_pair(self.sample, self.policy)
        self.client = copy.deepcopy(self.intended)
        m = self.client['message']
        m['firstTranscriptHash'], m['secondTranscriptHash'] = m['secondTranscriptHash'], m['firstTranscriptHash']
        result = self.result()
        self.assertTrue(result['evidenceMatchesIntended'])
        self.assertFalse(result['clientMatchesIntended'])
        self.assertFalse(result['accepted'])

    def test_all_transcript_bytes_bound_even_when_payment_unchanged(self):
        # eth_getTransactionReceipt is observed twice; extra innocuous receipt
        # metadata changes content while policy-relevant facts stay the same.
        for read in self.sample['providers'][1]['reads']:
            if read['method'] == 'eth_getTransactionReceipt':
                read['result']['gatheringTestMetadata'] = 'rejection fixture'
        result = self.result()
        self.assertTrue(result['paymentAccepted'])
        self.assertFalse(result['evidenceMatchesIntended'])
        self.assertFalse(result['accepted'])

    def test_missing_duplicate_swapped_and_extra_evidence_refused(self):
        for kind in ('missing', 'duplicate', 'swapped', 'extra_read', 'extra_field', 'bool_version'):
            sample = copy.deepcopy(self.sample)
            if kind == 'missing': sample['providers'].pop()
            if kind == 'duplicate': sample['providers'][1]['source'] = sample['providers'][0]['source']
            if kind == 'swapped': sample['providers'].reverse()
            if kind == 'extra_read': sample['providers'][1]['reads'].append(sample['providers'][1]['reads'][-1])
            if kind == 'extra_field': sample['providers'][1]['reads'][0]['accepted'] = True
            if kind == 'bool_version': sample['version'] = True
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                c.corroborate(sample, self.policy, self.intended, self.client)

    def test_equivalent_client_representation_matches(self):
        self.client['message']['minimumRaw'] = hex(int(self.policy['minimum_raw']))
        self.client['message']['token'] = '0x' + self.client['message']['token'][2:].upper()
        self.client['message'] = dict(reversed(list(self.client['message'].items())))
        self.assertTrue(self.result()['accepted'])

    def test_full_and_summary_decisions_and_no_mutation(self):
        before = copy.deepcopy((self.sample, self.policy, self.intended, self.client))
        full, short = self.result(False), self.result(True)
        self.assertEqual(full['accepted'], short['accepted'])
        self.assertEqual(full['clientBinding']['intended'], short['clientBinding']['intended'])
        self.assertIn('differences', full['clientBinding'])
        self.assertNotIn('differences', short['clientBinding'])
        self.assertEqual((self.sample, self.policy, self.intended, self.client), before)

    def test_summary_cannot_bypass_report_limit(self):
        with patch.object(c, 'MAX_OUTPUT_BYTES', 100):
            with self.assertRaisesRegex(ValueError, 'output limit'):
                self.result(summary=True)

    def test_cli_accept_reject_and_input_error(self):
        args = [str(HERE / n) for n in ('example.paired.json', 'example.paired-policy.json',
                                      'example.paired-intended.json', 'example.paired-intended.json')]
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(c.main([*args, '--summary']), 0)
        self.assertTrue(json.loads(out.getvalue())['accepted'])
        Path('test/scratch').mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir='test/scratch') as area:
            bad = Path(area) / 'changed.json'
            self.client['domain']['chainId'] = 2
            bad.write_text(json.dumps(self.client))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(c.main([*args[:3], str(bad)]), 1)
                self.assertEqual(c.main(['../outside.json', *args[1:]]), 2)
            bad.write_text('{"a":1,"a":2}')
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(c.main([*args[:3], str(bad)]), 2)

    def test_bridge_never_constructs_transport(self):
        with patch.object(c.agreement.s, 'RPC', side_effect=AssertionError('no network')):
            self.assertTrue(self.result()['accepted'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
