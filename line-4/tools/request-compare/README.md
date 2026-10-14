# Offline EIP-712 intended request comparison

Compare a client request against an independently prepared complete intended
request before trusting its digest. This standard-library Python tool calculates
both digests and reports JSON Pointer differences in encoded field words, types,
struct declarations and hash preimages. It requires no network, installation,
account, wallet or signing. Copy this whole folder to use it independently.

One working command, from the repository root:

```sh
python3 -B line-4/tools/request-compare/request_compare.py line-4/tools/request-compare/zto-intended.json line-4/tools/request-compare/zto-intended.json --summary
```

Tried: exit **0**, `accepted: true`, zero differences, digest
`0xf33e2506e5c103f98dbfe3feb6d4b87d55f1fad4e423dbaa8462465ff4ab9774`.
This self-comparison demonstrates execution, not independent approval.
To see a rejection, replace the second path with
`line-4/tools/request-compare/zto-altered.json`: exit **1**, two differences,
`/message/minimumRaw` and its containing `/message`. This deliberately altered
example increases the ZTO amount by one raw unit. Omit `--summary` to see the
exact intended and client encoding bytes. Parent differences are included so
the propagation into containing arrays and structs is visible.

For actual work, pass your independently prepared request first and the client's
request second. Each must include `types`, `primaryType`, `domain`, `message`,
and explicit `EIP712Domain`. A domain-only expectation leaves message values
unpinned; this tool compares the complete intended encoding. It does not impose
the ancestor domain checker's narrow domain profile: the intended request must
contain the domain fields and schema you actually expect.

Acceptance requires equal digests **and** equal traced encoding, including the
primary type, types, dynamic preimages and struct field/dependency order. Integer
notation, hex letter case and JSON object key order may differ when they encode
identically. Unicode text is compared by its actual UTF-8 bytes, without Unicode
normalization. Reordered declared fields, changed widths and changed empty-array
types are detected. Valid unused declarations are ignored because EIP-712 does
not commit to them. This compares commitments, not literal JSON documents.

The intended example is an unchanged copy of the ancestor trace's historical
real-ZTO payment observation: token
`0xd782bdea4ef02a0bd391eb9089470c8080f0a68e`, transaction
`0xc4ca304c305cae326cab066639ab2156412eee7f5f774b41a2a136369f817ef7`,
166357571280020680094504 raw units. Its read-only evidence domain has no verifier.
It is not a token permit or independently issued invoice. This round did not
fetch a fresh receipt; the tool does not validate the transfer or current chain
state. The altered example is explicitly a rejection fixture, not chain data.
See `provenance.json` for the unchanged encoder, trace and example source hashes.

Exit codes: **0** encoding matches; **1** valid requests differ; **2** malformed
input, unsafe file, argument error or exceeded limits. Files must be regular,
nonhidden paths under the current working directory; no symlinks or parent
traversal. The inherited POSIX no-follow reader and strict JSON parser limit
inputs to 65,536 bytes, depth 48 and 8,192 nodes. Duplicate keys, floating-point
numbers, malformed Unicode and cyclic Python inputs are refused. Each trace
and the full comparison report have a 1,048,576-byte cap; summary mode still
checks the complete report. Output goes only to stdout; errors go to stderr.
These are work bounds, not a process sandbox.

Tried all **18 new tests**, **71 ancestor tests**, both CLI modes and an isolated
copy of this folder, offline. All passed. The tests cover matching historical
ZTO bytes, a one-unit mismatch, wrong chain, equivalent representations, schema
order/types, added/removed array nodes, empty arrays, nested structs, Unicode,
unused declarations, primary type, immutability, invalid inputs, report limits,
exit codes, duplicate keys, oversize files and symlink refusal.

```sh
python3 -B -m unittest discover -s line-4/tools/request-compare -v
```

The encoder and trace are shared with earlier tools; their agreement is not
independent cryptographic verification. The caller must establish provenance of
the intended request separately. A match does not authenticate a requester,
recover a signature, authorize signing, establish contract support, prove a
payment or enforce replay protection. Encoding follows
[EIP-712](https://eips.ethereum.org/EIPS/eip-712).
