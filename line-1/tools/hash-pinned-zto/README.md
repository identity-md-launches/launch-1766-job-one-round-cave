# Hash-pinned ZTO snapshots

Capture real ZTO supply and decimals as a portable Ethereum RPC snapshot. Each
state read uses the exact selected block hash and `requireCanonical: true`.
Pepe links each ZTO observation to one exact block.

One command from the repository root shows it working **offline**, using the
included real-chain capture and Python's standard library only:

```sh
python3 -B line-1/tools/hash-pinned-zto/pinned.py --verify line-1/tools/hash-pinned-zto/live-zto.json
```

The live trial on 2026-10-14 succeeded at finalized Ethereum block **26192324**,
hash `0x6eb178a92a831e6a987e54bf21e8f5d42ce62642fb3b9da54b09c7960b18f814`.
ZTO at `0xd782bdea4ef02a0bd391eb9089470c8080f0a68e` returned raw supply
`1000000000000000000000000000` and **18** decimals: exactly
`1000000000.000000000000000000` tokens. The source is
[Ethereum Publicnode](https://ethereum-rpc.publicnode.com), routed through the
assignment's supplied transport for the local trial. No local transport address
is stored in the capture. The saved bundle is **75,313 bytes**. Offline replay
and all **27 new tests** passed; the inherited **19 safe-file tests** also passed.

To capture another observation with a reachable public endpoint:

```sh
python3 -B line-1/tools/hash-pinned-zto/pinned.py --output test/scratch/new-hash-pinned-zto.json
```

Choose a new output filename each time. Capture makes five public reads in order:
chain ID, finalized block, hash-pinned ZTO `totalSupply()`, hash-pinned ZTO
`decimals()`, and a recheck of the anchor's height/hash. An unsupported hash
selector or noncanonical-block error fails the capture; it never silently falls
back to a block number or `latest`. Successful raw responses are retained.
Supply formatting uses integer arithmetic, without floating-point rounding or
assuming a token precision. The CLI is deliberately limited to these ZTO calls.

The hash selector follows [EIP-1898](https://eips.ethereum.org/EIPS/eip-1898).
Offline replay checks the fixed read order, mainnet ID, ZTO address/selectors,
the exact shared hash/canonical flag, one-word ABI results, decimals fitting
`uint8`, anchor recheck, UTC timestamp, and two checksum layers. The response
checksum covers each answer; the bundle checksum also covers the recorded
requests. Tests reseal malicious changes to demonstrate that semantic checks
still reject inconsistent hashes, wrong tokens, wrong chains and downgrades.

This piece reuses `../bounded-rpc-snapshot/snapshot.py` for strict JSON parsing,
RPC envelopes and redirect rejection, and `../safe-snapshot-files/safe_files.py`
for bounded no-follow input and atomic no-clobber output. All dependencies are
ordinary repository files; no install or network is required for replay/tests.
Transport disables environment proxy discovery, sets its own User-Agent, caps
response bytes and refuses redirects. Paths must be visible relative workspace
paths: no hidden, parent, absolute or symlink components. POSIX file-descriptor
and hard-link support is required. Run the focused tests with:

```sh
python3 -B line-1/tools/hash-pinned-zto/test_pinned.py
```

Limitations: a saved checksum is an integrity check, not authentication.
Provider-reported finality and `requireCanonical` are observations from the RPC
provider, not consensus or state proofs; offline replay cannot establish current
canonicality or freshness. Metadata such as capture time is not authenticated.
Even fully resealed and internally consistent invented evidence cannot be
distinguished from genuine evidence by this checker. The fixed 100,000-byte
response/file cap can reject unusually large block responses. Shared safe-file
limits still apply to concurrent in-place mutation or hostile directory writers.
The tool never signs, sends transactions, handles wallets, or uses a new coin.
