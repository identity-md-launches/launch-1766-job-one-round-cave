# Water gathering 05

This round checks all four lines, shares corroborated payment request comparison,
rebuilds the gallery and leaves **Two Witnesses, One Stone**. No line folder or
line record changed. Everything needed for offline use is ordinary Python/JSON
in the repository; Python's standard library is sufficient (POSIX file readers).

Run every line's documented offline checks and the shared integration checks:

```sh
python3 -B gathering/run_checks.py
```

The final run passed **43 commands and 312 tests**; `check-results.json` retains
the output. Tests that write beside source run on a copy in `test/scratch/`.
The new shared command and its limitations are documented in
`../shared/payment-evidence/README.md`. It requires two agreeing payment
observations, independent policy, complete intended request and exact client
encoding to pass together. It never signs or sends anything.

`REPORT.md` replaces the prior report with per-line trials, working behavior,
limits, goal scope and shared changes. `COINS.md` says none because ZTO already
provides usable real payment evidence, with IMD supported second. Fresh publicnode
hash-pinned ZTO capture, two-provider payment verification and discovery passed;
see `live-check-results-05.json` and `hash-pinned-round05.json`. Saved observations
are historical and unauthenticated, not current consensus proofs or invoices.
`live_checks_05.py` can make the public read trials again; offline checks never
require network. No package, wallet, secret or environment configuration is used.

The finished wall is **1254 × 1254 RGB PNG** at required
`artifacts/gathering/wall-v5.png` and `artifacts/gathering/wall.png`; both files
are identical. `dist/gathering/05.jpg` is a **512 × 512 JPEG**, 75,379 bytes.
`05.json` has the required six attributes and the PNG's lowercase SHA-256 URL.
The installed image tool produced the new paired-eye pigment. One-time finishing
added it to vacant stone below the ancestor bowl, preserving every outside pixel
and deep cracks. `finish_wall_05.py` records that composition and refuses to run
unless its input is the verified gathering-04 ancestor; it is not a command to
rerun on the finished image.

Both full wall and decoded JPEG were visually inspected: Pepe, inherited marks,
rock, cracks, colour, light and framing remain. No hands/handprints are depicted;
no digits to count. No forbidden text or other marks were observed. **No known
unmet visual requirements.** `wall-review-05.json` records the full image-tool
prompt, dimensions, formats, hashes and preservation/local review. The generated
draft was overwritten; no extra image is delivered.

The gallery has **121 records**, **25 paintings** and **96 pending slots**, by
wall with newest paintings first. It includes inline styles and all captions;
painted thumbnails load locally, full-size and pending-cave images use public
artifact URLs. This is the fifth gathering, so first-gathering placeholder
creation is not triggered. Existing pending records remain unchanged.

Rebuild and validate the deliverable:

```sh
python3 -B gathering/build_gallery.py
python3 -B gathering/check_delivery.py
```

The latter checks formats, dimensions, records, hashes, placeholder coverage,
goals, gallery order, vendored provenance, unchanged line folders and the 100 KB
file cap outside artifacts. These checks carry no independent certification.
Required PNGs remain untracked for the daemon's separate artifact upload.
