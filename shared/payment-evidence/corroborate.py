#!/usr/bin/env python3
"""Bind two historical payment observations to a complete intended/client request."""
import argparse
import json
import sys

from check import HERE, check, contracts, load, module, policy as validate_policy, typed

# These are ordinary vendored files; neither module's CLI or transport is run.
sys.path.insert(0, str(HERE / 'vendor'))
from request_compare import compare

agreement = module('paired_payment_agreement', 'vendor/provider-agreement/agreement.py')
DOMAIN = {'name': 'Read-only Corroborated Payment Evidence', 'version': '1', 'chainId': 1}
PRIMARY = 'CorroboratedPaymentEvidence'
MAX_OUTPUT_BYTES = 100_000


def request_for_pair(sample, expected):
    """Recompute every read; construct the bridge's fixed read-only commitment.

    No expected request is inferred to be approved. This function also supports
    preparing a request for a caller to review separately before comparison.
    """
    typed.validate_tree(sample)
    typed.validate_tree(expected)
    validate_policy(expected)
    if not isinstance(sample, dict) or not contracts.same(sample.get('policy'), expected):
        raise ValueError('paired /policy differs from the independently supplied policy')
    observations = agreement.replay(sample)
    hashes = []
    # check() adds Line 2's exact transcript contracts, strict read-field checks,
    # separate-policy comparison and Line 4's input bounds to the paired replay.
    for provider in sample['providers']:
        single = {'version': 1, 'policy': expected, 'reads': provider['reads']}
        evidence = check(single, expected)
        hashes.append(evidence['typedData']['message']['transcriptHash'])
    fields = [('transactionHash', 'bytes32'), ('token', 'address'),
              ('recipient', 'address'), ('minimumRaw', 'uint256'),
              ('confirmations', 'uint256'), ('requireFinalized', 'bool'),
              ('firstSource', 'string'), ('firstTranscriptHash', 'bytes32'),
              ('secondSource', 'string'), ('secondTranscriptHash', 'bytes32')]
    request = {
        'types': {
            'EIP712Domain': [{'name': n, 'type': t} for n, t in
                             [('name', 'string'), ('version', 'string'), ('chainId', 'uint256')]],
            PRIMARY: [{'name': n, 'type': t} for n, t in fields]},
        'primaryType': PRIMARY, 'domain': dict(DOMAIN),
        'message': {
            'transactionHash': expected['tx'].lower(),
            'token': agreement.w.TOKENS[expected['token']],
            'recipient': expected['recipient'].lower(),
            'minimumRaw': expected['minimum_raw'],
            'confirmations': expected['confirmations'],
            'requireFinalized': expected['finalized'],
            'firstSource': agreement.PROVIDERS[0], 'firstTranscriptHash': hashes[0],
            'secondSource': agreement.PROVIDERS[1], 'secondTranscriptHash': hashes[1]}}
    return observations, request


def corroborate(sample, expected, intended, client, summary=False):
    """Every acceptance gate is mandatory; saved acceptance flags are never trusted."""
    observations, derived = request_for_pair(sample, expected)
    evidence_binding = compare(derived, intended)
    client_binding = compare(intended, client)
    result = {
        'accepted': observations['accepted'] and evidence_binding['accepted'] and client_binding['accepted'],
        'paymentAccepted': observations['accepted'],
        'evidenceMatchesIntended': evidence_binding['accepted'],
        'clientMatchesIntended': client_binding['accepted'],
        'providerAuthenticated': False,
        'evidenceMode': 'offline historical observations; provider labels are unauthenticated',
        'settlementAndAgreement': observations,
        'evidenceBinding': evidence_binding,
        'clientBinding': client_binding,
        'authorization': 'Read-only content comparison; no signature, permit or sending.'}
    if not summary:
        result['derivedTypedData'] = derived
    # Summary mode still validates and bounds the full diagnostic output.
    if len(json.dumps(result, ensure_ascii=True, indent=2).encode()) > MAX_OUTPUT_BYTES:
        raise ValueError('corroboration exceeds 100000-byte output limit')
    if summary:
        for key in ('evidenceBinding', 'clientBinding'):
            result[key] = {k: v for k, v in result[key].items() if k != 'differences'}
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paired', help='paired historical RPC transcript')
    parser.add_argument('policy', help='independently chosen payment policy')
    parser.add_argument('intended', help='complete independently reviewed typed-data request')
    parser.add_argument('client', help='exact client typed-data request')
    parser.add_argument('--summary', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = corroborate(load(args.paired), load(args.policy), load(args.intended),
                             load(args.client), args.summary)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0 if result['accepted'] else 1
    except (ValueError, OSError, TypeError, KeyError, RecursionError) as exc:
        print(json.dumps({'accepted': False, 'state': 'input_error', 'error': str(exc)}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
