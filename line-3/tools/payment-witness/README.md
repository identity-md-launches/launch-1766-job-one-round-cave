# Payment witness

Verify that an Ethereum-mainnet transaction both meets a settlement policy and
records enough **net ZTO transferred to a specified recipient**. IMD is also
supported. Python 3.9+ and the standard library are sufficient; no install,
wallet, key, configuration, signing, sending, or timer is involved. JSON goes
to stdout. This piece imports the unchanged sibling `settlement-check/settlement.py`;
copy both folders when taking it elsewhere.

One command from the repository root shows it working **without network** on
saved observations of a real ZTO transfer:

```sh
python3 -B line-3/tools/payment-witness/witness.py --replay line-3/tools/payment-witness/live-evidence.json
```

It recomputes the settlement and amount checks by replaying the recorded RPC
reads in order. It does not trust a saved `accepted` flag. The transcript includes
the actual receipt and the canonical block anchors; block transaction lists are
omitted because the policy does not use them. Replay checks historical observations,
not today's chain, and cannot authenticate the provider or the file's provenance.
Input files are bounded to 90 KB and must use visible relative paths inside the current workspace; symlinks and nonregular files are refused.

For current read-only evidence:

```sh
python3 -B line-3/tools/payment-witness/witness.py --demo
```

This checks transaction
`0xc4ca304c305cae326cab066639ab2156412eee7f5f774b41a2a136369f817ef7`,
discovered using real ZTO Transfer logs. Its transfer was emitted by ZTO
`0xd782bdea4ef02a0bd391eb9089470c8080f0a68e`, from the supplied Uniswap v4
PoolManager `0x000000000004444c5dc75cb358380d2e3de08a90` to
`0x2d30e495a15f2657d57c3e2caa08b06415c26cbf`.
The demo derives its expected recipient and amount from the receipt; it is a
decoding demonstration, not verification against an independent invoice.

An actual worker supplies its own recipient and minimum raw integer amount.
This explicit command reproduces the observed recipient and amount policy for the
recorded transaction:

```sh
python3 -B line-3/tools/payment-witness/witness.py --tx 0xc4ca304c305cae326cab066639ab2156412eee7f5f774b41a2a136369f817ef7 --recipient 0x2d30e495a15f2657d57c3e2caa08b06415c26cbf --minimum-raw 166357571280020680094504
```

Default policy: successful execution, canonical inclusion, at least 12 confirmations,
and finalized inclusion. `--confirmations N` changes the threshold;
`--allow-unfinalized` explicitly relaxes finality. `--token IMD` selects the real
IMD contract `0xd34a99bc0f67ae1bbd63c660e6d0b0dd03e263b7`. No decimal conversion
or floating-point math is used: amounts are decimal strings in token base units.
`--rpc https://eth.drpc.org` selects the alternate public endpoint. Both endpoints
are public reads only; the ancestor's RPC allowlist, size bound, 20-second timeout,
and custom User-Agent remain in effect.

The recipient's measure is incoming minus outgoing amounts across the chosen
token's exact ERC-20 Transfer events in this one receipt. Multiple transfers
aggregate; a self transfer or an equal incoming/outgoing pass-through cannot
satisfy a positive minimum. Another token or recipient does not count. Exact
three-topic encoding, address padding, uint256 data, unique log indices, removed
flags, transaction hash, block hash and height are checked. After the settlement
check the receipt is read again and bound to the same inclusion; the canonical
inclusion block is checked again after decoding. A changed anchor fails closed.

Exit 0 means `accepted: true`; exit 1 means valid evidence failed settlement or
amount policy; exit 2 means invalid input or unverifiable/malformed evidence.
`settled: true` can coexist with `accepted: false` when the amount is insufficient.

## What happened when tried

On 2026-10-14 the live demo exited 0: inclusion block 26190898, sampled head
26191361, 464 confirmations, finalized head 26191269. It recorded net
`166357571280020680094504` raw ZTO received, no outgoing ZTO in that receipt,
and `accepted: true`. The committed `live-evidence.json` reproduces that result
offline. No transaction was signed or sent.

```sh
python3 -B -m unittest discover -s line-3/tools/payment-witness -p 'test_*.py' -v
```

All 14 tests passed after correcting the synthetic fixture's confirmation count.
They cover exact/short amounts, aggregation, outgoing and self transfers,
wrong recipient/token, reverted/absent receipts, required/relaxed/unknown finality,
chain changes between settlement and amount checks, malformed or orphaned logs,
duplicate indices, uint256 precision, invalid policies, real transcript replay,
tampered/truncated/reordered evidence and workspace input restrictions. Fixture
identities are generated solely for offline tests, never substituted into live calls.
The unchanged ancestor's 16 tests also passed.

## Limits that matter to a worker

This trusts the chosen RPC provider and the chosen token's Transfer-event semantics.
It is not a cryptographic receipt proof, independent consensus check, sender
authentication, invoice registry, or account balance query. A mint Transfer to the
recipient is included in this event-based measure. Fee, rebase or dishonest-event
tokens could require a different accounting model. There is no promise about the
recipient's balance after this transaction, other transactions, or later reorgs.
The recipient is not proven to belong to a person, and the same transaction can
be checked repeatedly: a payment service must deduplicate it and store its own
invoice policy. A consistently dishonest provider or edited offline transcript
can defeat the evidence checks. Recheck live when current settlement matters.

## Round 25 file boundary repair

The replay reader now opens each relative path component with descriptor-relative
`O_NOFOLLOW` flags and checks the opened leaf is a regular file. It refuses
absolute, parent, hidden, empty-component and backslash paths; FIFOs cannot block
the read. Actual bytes, rather than a pre-open size, enforce the 90 KB bound.
Duplicate keys, nonfinite JSON and excessive nesting fail closed. POSIX no-follow
opens are required; unsupported platforms refuse the operation. The diagnostic
tool now passes a workspace-relative path to this reader. Ordinary documented
replay commands continue to work. Seven new file-boundary tests (including a
directory replacement race) are in provider-agreement's test suite.

An already-open regular file can still be edited in place by another writer;
hardlinked input provenance is not checked. Safe opening does not authenticate
a transcript. Policy and transfer accounting are unchanged.
