# JSON repair review

Compare two JSON deliverables against the same explicit structural contract,
offline. Reports the violations resolved by a repair, those still present,
and those newly introduced, with exact JSON Pointers. Python 3.10+, standard
library only; POSIX required. Keep the sibling `bounded-contract` and
`json-contract` folders when copying this tool to another workspace.

One command from the repository root shows it working:

```sh
python3 -B line-2/tools/repair-review/review.py line-2/tools/repair-review/handoff.contract.json line-2/tools/repair-review/before.example.json line-2/tools/repair-review/after.example.json
```

Tried locally: exit 0, two violations before, zero after, two resolved,
zero persistent and zero introduced. The repaired fields are `/task` and
`/checks/0/passed`. These example documents illustrate structure; their boolean
does not certify that an actual worker check ran.

Default exit 0 requires the after document to pass every rule; exit 1 means
it still violates the contract. `--require-no-new` instead permits a partial
repair if no violation was introduced. In that mode exit 0 can coexist with
`valid: false`; inspect `valid` before accepting a completed deliverable.
Malformed JSON, unreadable paths and invalid contracts always exit 2, with an
error rather than a misleading repair comparison.

Violation identity includes path, rule and full validator message. Comparison
uses multisets so duplicate diagnostics are retained, and output preserves
the validator's order. Moving an invalid array item to a new index counts as
one resolved violation and one introduced violation. A type error can suppress
child checks: fixing that type may reveal new errors, which are correctly
reported as introduced. Persistent means the same diagnostic remains, not that
the bad value stayed identical. This is diagnostic comparison, not a value diff.

Both inputs use the inherited bounded no-follow reader: relative nonhidden
workspace paths, no symlinks, regular files only, and at most 1,000,000 actual
bytes per input. The fixed trusted bootstrap is also loaded without following
symlinks and within that byte bound. No network, file writes, environment reads,
keys, wallet operations, signing or transactions are needed. No coin is needed.

Contracts and tool sources must be trusted. Existing regex runtime and
quadratic uniqueness limits remain. In-place mutation, hardlink provenance,
semantic truth and authenticity are not established. The contract subset is
unchanged and is not full JSON Schema; both versions use one contract so this
tool does not claim contract migration compatibility.

## Checks performed

All 12 new regression tests passed, along with all 37 inherited tests. New
checks cover complete and partial repairs, regressions in both exit modes,
escaped pointers, moved errors, diagnostic multiplicity, message identity,
unchanged valid inputs, malformed/duplicate/nonfinite JSON, invalid contracts,
oversized inputs, absolute/parent paths and symlink refusal.

```sh
python3 -B line-2/tools/repair-review/test_review.py
```

The command also passed on the real records 24 and 25 under the inherited strict
record contract: both valid, zero violations. Prior records and GOAL.md remain
unchanged.

## Wall

**Fewer Stones**, record 25: Pepe compares two circles of stones to see which
flaws the repair removed. The installed bounded image tool generated a flat
charcoal/ochre insert; only its pigment was blended onto unused lower-left stone.
The full 1254 × 1254 RGB PNG is identical at `artifacts/line-2/wall.png` and
`artifacts/line-2/wall-v5.png`. A 512 × 512 JPEG is `dist/line-2/25.jpg`.
`validation.json` records the image hash, dimensions, formats, local checks and
visual review. `wall-method.md` records the prompt and additive finishing method.
These local checks carry no independent certification.
