# Provider agreement

Check that two public Ethereum RPC URLs independently meet the same settlement
and ZTO payment policy, and agree on inclusion, execution and selected-token
Transfer events. A failed provider or disagreement refuses acceptance. Python
3.9+ and the standard library suffice. Copy this folder together with the sibling
payment-witness and settlement-check folders; no package install is needed.

One command from the repository root demonstrates it **offline** using saved
observations of a real ZTO payment from both public endpoints:

```sh
python3 -B line-3/tools/provider-agreement/agreement.py --demo
```

It exits 0 with `accepted: true`, `state: corroborated`. Both transcripts are
recomputed, including canonical anchors and payment amounts. Saved accepted flags
are never used. This is historical evidence, with unauthenticated source labels;
it does not establish today's chain state. The demo's recipient and minimum were
taken from the ancestor's real receipt observation, so it is a demonstration,
not verification against an independent invoice.

For a live check, supply the transaction, recipient and minimum from your own
payment policy. This runnable example uses the documented real historical ZTO
payment and its observed recipient/amount:

```sh
python3 -B line-3/tools/provider-agreement/agreement.py --tx 0xc4ca304c305cae326cab066639ab2156412eee7f5f774b41a2a136369f817ef7 --recipient 0x2d30e495a15f2657d57c3e2caa08b06415c26cbf --minimum-raw 166357571280020680094504
```

The sources are fixed to `https://ethereum-rpc.publicnode.com` and
`https://eth.drpc.org`; users cannot accidentally compare a URL to itself.
Mainnet, successful execution, canonical inclusion, at least 12 confirmations,
and finalized inclusion are required by default. `--confirmations N` changes
the threshold; `--allow-unfinalized` explicitly relaxes finality. ZTO is first;
`--token IMD` uses the supplied real IMD contract. All amounts are raw decimal
integer strings, and net receipt transfers include incoming minus outgoing.

Both providers run the inherited policy, anchor rereads and exact Transfer-log
checks separately. Their sampled latest/finalized heads may advance between
sequential reads and need not match. Inclusion height/hash, execution and all
selected-token Transfer events must match; event order is normalized by log
index. Comparing only a net amount could hide differing events, so the full
decoded event set is compared too. There is no single-provider fallback or retry.
Unknown finality cannot satisfy the default policy. No wallet, key, environment
variables, signing, sending, payment or deployment is involved.

Exit 0 means both observations meet policy and agree. Exit 1 means evidence
disagrees or at least one policy is unmet. Exit 2 means invalid input or an
unverifiable provider. JSON records individual reports and named differences.
A complete live result includes a `sample` object that can be saved separately
as a paired transcript and replayed with `--replay WORKSPACE_RELATIVE_FILE`.
Replay refuses malformed, duplicate-source, missing, reordered and extra reads;
policy overrides are refused. The safe workspace reader bounds input to 90 KB
and rejects symlink paths, FIFOs and nonregular files.

## What happened when tried

On 2026-10-15, both public endpoints returned successful finalized inclusion at
block **26190898**, sampled head **26192482**, and **1585 confirmations**.
They agreed on net **166357571280020680094504 raw ZTO** received by
`0x2d30e495a15f2657d57c3e2caa08b06415c26cbf`. The tool returned `corroborated`.
[live-check.json](live-check.json) holds the actual result, and
[paired-evidence.json](paired-evidence.json) holds both actual read transcripts.
No transaction was signed or sent.

```sh
python3 -B -m unittest discover -s line-3/tools/provider-agreement -p 'test_*.py' -v
```

All 18 tests passed: 11 agreement/CLI tests and seven file-boundary tests. They
cover divergent inclusion chains, identical totals with different events,
advancing heads, unmet minimums, a failed second source without fallback,
pre-read policy validation, transcript integrity, the real paired demo, unsafe
paths, ambiguous JSON, byte bounds, symlinks, FIFOs, a concurrent directory
replacement and unsupported safe-open platforms. Manipulated paired fixtures
reuse one historical observation only for tests; they are explicitly not fresh
observations from two providers. All 50 inherited checks still pass.

## Limits

Two URLs may share upstream infrastructure; agreement is not proof of independent
operators. Consistent lies, altered saved files or a later reorg can defeat this
evidence. This is not a consensus verifier, cryptographic receipt proof, recipient
ownership check, invoice registry or deduplication service. It inherits the
chosen token's Transfer-event semantics and does not prove a current balance.
Sequential queries can conservatively reject a newly settling transaction as
heads advance. A writer can mutate an opened regular input in place; hardlink
provenance is not checked. Each public read has a 20-second timeout and inherited
response bounds, custom User-Agent, read allowlist, disabled proxy discovery and
redirect refusal. No new coin is required.
