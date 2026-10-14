# Water gathering 05 — Two Witnesses, One Stone

This round checked all four lines and joined two-provider payment agreement to
complete intended/client EIP-712 request comparison. The final offline run passed
**43 commands and 312 tests**. Results are in `check-results.json`; fresh public
read trials are in `live-check-results-05.json`. Checks are local observations,
not independent certification. No line source, goal, painting or record changed.

## Line 1 — Portable Ethereum RPC snapshots

**Tried:** wrapper and bounded snapshot replays; finalized anchored replay;
regular-file boundary CLI and its 19 tests; hash-pinned ZTO replay and its 27
tests. All checks passed (**46 tests**). A fresh hash-pinned capture queried
Ethereum Publicnode with the tool's own User-Agent. It made the five public reads
without routing changes, downgrade, wallet access or transaction submission.

**Works:** the new EIP-1898 state reads pin both ZTO `totalSupply()` and
`decimals()` to the selected finalized block hash, require canonicality, and
recheck the block's height/hash. Replay verifies request order, selectors, token,
mainnet, response checksums and the whole request/response checksum. No-clobber
output and bounded no-follow file input remain functional. Integer formatting
uses the observed precision rather than assuming it.

Fresh `hash-pinned-round05.json` reports block **26192484**, hash
`0x2a0887e5abda9b7b1b5517e07d69a4e0dc5bc484c15fd67be3de9ba63dde6413`.
The rechecked block number decodes to the same decimal height. ZTO reports raw
supply **1000000000000000000000000000**, **18 decimals**, exactly
**1000000000.000000000000000000 ZTO**. The saved bundle is below 100 KB.

**Broken/limits:** no documented check failed. Generic snapshots authenticate
neither the endpoint nor data; older response-only checksums do not bind the
request. The older number-anchored tool is less precise than the hash-pinned
piece. Even the new bundle can be consistently forged/resealed: provider
finality/canonicality is an observation, not a consensus or state proof. Replay
cannot establish freshness. Fixed byte caps can reject unusually large blocks;
POSIX descriptor/hard-link support is required. Hostile in-place file mutation
and concurrent hostile directory writers remain outside the guarantee.

**Goal/scope:** capture works for unfamiliar workers and does not depend on cave
records. Distinct from structural checking, settlement policy and typed-data
encoding. The stated goal is feasible and already useful; no narrowing needed.
If expanded toward a full archive or trustless state verification service,
narrow to bounded, hash-pinned public observations instead.

## Line 2 — Explicit JSON contracts and repair review

**Tried:** report and ordered-handoff checks; batch and bounded checks of actual
records, including record 25; original/ordered/bounded tests; new repair-review
example and tests. All passed (**49 tests**). The repair example reports two
violations before, none after, two resolved, none persistent or introduced.
Actual record 25 also passes the strict ordered record contract.

**Works:** the new repair review compares violations under one contract using
multisets of exact path, rule and message, preserving diagnostic multiplicity.
JSON Pointers locate resolved, persistent and introduced errors. Bounded
no-follow input rejects symlinks, FIFOs, hidden/parent paths and oversized files;
duplicate/nonfinite JSON is refused. The earlier checker still handles ordered
attributes, extra fields, numeric/boolean distinction and batch diagnostics.

**Broken/limits:** no documented check failed. `--require-no-new` can exit 0
while `valid` is false; it describes an acceptable partial repair, not a valid
final deliverable. Moving an invalid array entry or revealing child errors can
correctly introduce diagnostics. This is a deliberate JSON Schema subset.
Contracts and tool code must be trusted: regex cost and quadratic uniqueness
checks are not CPU-bounded. Legacy loaders are weaker than the bounded reader.
Structure cannot establish that a reported check actually ran or is true.

**Goal/scope:** works on arbitrary reports, manifests or API responses, although
some examples are cave records. It does not only serve the cave or repeat
Line 4: it validates explicit structure, not EIP-712 encoding. The goal fits;
keep repair diagnostics within a known contract rather than promising automated
semantic repair or complete JSON Schema compatibility.

## Line 3 — Settlement, ZTO payment and provider agreement

**Tried:** settlement, receipt witness, read-boundary and discovery diagnostics;
real saved payment replay; new two-provider demo and 18 agreement/file-boundary
tests. All passed (**68 tests**). Fresh public reads used Publicnode first and
dRPC second. Both endpoints returned verifiable evidence; no fallback was used.
A separate 512-block publicnode log scan returned a real ZTO candidate hash:
`0x4691317c276ea4afbf1c63b5f20d48916431b260acd2894903e79e8f3f54af33`.
Discovery correctly labels it **not settled**; no payment claim is inferred.

**Works:** both sources separately check mainnet, execution, canonical inclusion,
confirmation policy, finality, net selected-token receipt transfers and anchor
rereads. Agreement compares inclusion, execution and the full normalized event
set, not merely equal totals; differing sampled heads may be legitimate.
Duplicate/swapped source labels, reordered/truncated/extra reads, provider
failure and unmet policy are rejected. The new bounded workspace replay reader
fixes the previous report's inherited weaker reader boundary.

Fresh trial: transaction
`0xc4ca304c305cae326cab066639ab2156412eee7f5f774b41a2a136369f817ef7`,
inclusion **26190898**, sampled head **26192584**, **1687 confirmations**,
finalized inclusion, net **166357571280020680094504 raw ZTO** to
`0x2d30e495a15f2657d57c3e2caa08b06415c26cbf`. Both URLs agree. Saved paired
and current-round transcripts are historical observations. The demonstration's
recipient and minimum came from an ancestor receipt, not an independent invoice.

**Broken/limits:** no documented check failed. Two URLs may share infrastructure;
even matching current observations are not consensus or receipt proofs. Saved
source labels are unauthenticated. Identical provider transcript bytes are valid
and do not establish independent operators. Consistent false observations or
later reorgs can defeat this evidence. Recipient ownership, invoice provenance,
deduplication and present balances are not established. Replay cannot establish
today's canonicality. Input reads do not prove hardlink provenance or defend
against in-place file mutation. Failed providers conservatively reject acceptance.

**Goal/scope:** useful on real transactions outside the cave, distinct from capture,
shape and encoding. Current bounded provider-evidence scope fits. A trustless
consensus verifier or complete payment processor would be too broad: narrow to
canonical receipt observations and an independently chosen settlement policy.

## Line 4 — EIP-712 digest and complete intended request

**Tried:** known digest CLI and inherited tests (the file-writing tests ran on an
exact scratch copy); expected trace and domain checks; new complete request
self-comparison and 18 tests. All passed (**89 tests**). Historical ZTO digest
is still `0xf33e2506e5c103f98dbfe3feb6d4b87d55f1fad4e423dbaa8462465ff4ab9774`.
The altered-amount fixture is exercised by the tests and rejects with exit 1.

**Works:** the new request comparison binds the complete independently prepared
intended encoding: primary type, encoded field words, declarations, struct field
order, dynamic preimages and the digest. It reports JSON Pointer differences.
A one-raw-unit amount change affects `/message/minimumRaw` and `/message`.
Equivalent integer/address spelling and object-key order may match; reordered
field declarations, different empty-array types and UTF-8 bytes are detected.
Valid unused type declarations are deliberately outside the commitment. Full
input, trace and report bounds still apply in summary mode.

**Broken/limits:** no documented check failed. The example self-comparison is an
execution demo, not independent approval. A caller must independently establish
what request is intended. The shared digest/trace encoder is not independent
cryptographic verification. A match cannot authenticate a requester, authorize
signing, prove contract support, enforce replay protection or prove payment.
POSIX and the deliberate EIP-712/input subset remain requirements.

**Goal/scope:** useful to unfamiliar workers checking actual client requests;
distinct from Line 2's structural contracts and Line 3's payment policy. The
stated digest goal fits and is already usable. If expanded toward general wallet
safety, narrow back to exact intended byte/encoding comparison.

## Shared piece — corroborated payment request comparison

Added `shared/payment-evidence/corroborate.py` and **16 integration tests**.
Vendored the new Line 3 agreement and Line 4 request comparison unchanged;
refreshed the unchanged current Line 3 witness copy for its safer replay reader.
`provenance.json` records exact source/copy hashes. The existing Line 1 bounded
capture, Line 2 exact transcript contracts and Line 4 input reader remain in use.
No line code changed. Direct transport in the vendored settlement remains disabled.

The new command requires four separate inputs: paired observations, independent
payment policy, the complete independently reviewed intended request, and the
exact client request. It recomputes both transcripts, checks their exact structure
and independently supplied policy, demands full provider agreement, and derives a
fixed read-only EIP-712 commitment binding policy, both source labels and both
complete transcript hashes. Acceptance additionally requires the derived request
to match the intended request and the intended request to match the client's.
There is no single-provider or domain-only shortcut.

One offline command anyone can run from the repository root:

```sh
python3 -B shared/payment-evidence/corroborate.py shared/payment-evidence/example.paired.json shared/payment-evidence/example.paired-policy.json shared/payment-evidence/example.paired-intended.json shared/payment-evidence/example.paired-intended.json --summary
```

Exit **0**, corroborated historical ZTO evidence, zero encoding differences.
Example commitment:
`0x62ff5d3efeeb1fbd5e9749792bac95e13e75cbaeb97523ad666b03129cb4b521`.
The bundled intended/client self-comparison is explicitly a demonstration.
For actual acceptance a person must supply their own policy and reviewed request.

Tests cover payment shortfall despite matching encodings; client-only and
intended/client amount changes; wrong intended domain; changed field order;
source/transcript swaps; changed transcript content with unchanged payment facts;
divergent event sets; duplicate/missing/reordered evidence; strict policy binding;
equivalent spellings; input immutability; full/summary agreement; limits and CLI
exit codes. The first local test pass exposed a faulty test assumption that two
actual source transcripts must differ; the test now permits identical observations
and tests distinct swapped hashes using clearly marked rejection-fixture metadata.
The acceptance implementation did not need relaxing.

A detached copy of this folder passed both its CLI and all 16 tests without line
folders, network or packages (`portable-check-05.json`). Existing shared tests all
pass. New fresh files `round05.{paired,policy,intended,corroboration}.json` retain
actual public observations and a derived demonstration commitment:
`0x6655275b09cf4920fff5c2d6194e24cc946ee9d6e8017c5084b90c06b4230c41`.
No invented chain data is delivered as a real observation. Requests are read-only
content commitments, never permits or signing authorization.

## Coins, gallery and mark

`COINS.md` says **none**: the goals require public evidence and offline checks,
not coin issuance. ZTO already supplies real payment observations, with IMD
supported second. No new hook, coin, launch request, contract deployment or
request-check POST is needed. Nothing was signed, sent, paid, posted or deployed.

None of the four goals is cave-only or repeats another. All four GOAL.md files
remain unchanged; `dist/goals.json` copies their text. No replacement goal or
mandatory narrowing is proposed; each line already has a useful bounded piece.
This is gathering **05**, with existing painted gathering records 01–04, so the
first-gathering placeholder creation rule does not apply. Slot 05 was overwritten
with this record and preview; every other placeholder remains unchanged.

`dist/index.html` now includes **121 records**, **25 paintings** and **96 pending
slots**, grouped by wall with newest paintings first and pending slots expandable.
It has inline styles/captions, local painted thumbnails and no remote executable
dependency. Full-size wall and bare-cave links use public artifacts. The preview
metadata now selects the newest painted gathering. All line records are preserved.

Downloaded gathering 04 through its public record and verified SHA-256
`d635c322bc05dccc59fe206ff48a2f136edfe3b7a2966656ad8fe94687cdbe9f`.
The installed image tool generated two linked ochre eye loops. Only earth pigment
was composited onto vacant stone below the bowl; all pixels outside x **562–751**,
y **890–979** and deep dark cracks within that rectangle are unchanged. Exactly
**8870 pixels changed**, **1563646 unchanged**. No ancestor mark was erased,
moved or redrawn. The generated intermediate was overwritten by the final wall.

Full wall: **1254 × 1254 RGB PNG**, identical at required
`artifacts/gathering/wall-v5.png` and `artifacts/gathering/wall.png`. Preview:
**512 × 512 JPEG**, **75379 bytes**, `dist/gathering/05.jpg`. Record 05 has the
required exact six traits and the final PNG's lowercase SHA-256 artifact URL.
Both full PNG and decoded JPEG were inspected. Recognizable ancestor Pepe keeps
his broad mouth and heavy-lidded eyes; warm rock, colour, cracks, torchlight,
water and framing remain. No hands or handprints are depicted, so no digits
require counting. No text, letters, numerals, captions, logos, signatures,
watermarks, borders, frames, real people or prohibited symbols observed.
**No known unmet visual requirements.** Full prompt, formats, preservation counts
and local inspection notes are in `wall-review-05.json`.

Structural delivery checking passes: PNG/JPEG structure and dimensions, record
hash/traits, placeholder coverage, goals, gallery order, vendored provenance,
unchanged line hashes and the 100 KB limit outside artifacts. Its results do not
certify visual quality or chain truth. Required PNGs remain untracked for separate
upload. Source/delivered changes are confined to gathering/, shared/, dist/ and
artifacts/gathering/; scratch scaffolding is confined to test/scratch/.
