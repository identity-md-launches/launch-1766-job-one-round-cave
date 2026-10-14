#!/usr/bin/env python3
"""Bounded read-only ZTO discovery diagnostics, or real historical payment replay."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location(
    "payment_witness", Path(__file__).resolve().parent.parent / "payment-witness" / "witness.py")
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)
s = w.settlement


class Trace:
    def __init__(self, rpc):
        self.rpc, self.reads = rpc, []

    def call(self, method, params):
        entry = {"method": method}
        if method == "eth_getLogs":
            entry["range"] = {key: params[0][key] for key in ("fromBlock", "toBlock")}
        self.reads.append(entry)
        try:
            result = self.rpc.call(method, params)
        except s.ReadFailure as exc:
            entry["status"] = "failed"
            entry["failure"] = exc.diagnostic
            raise
        entry["status"] = "returned"
        return result


def discover(rpc, lookback=2048):
    trace = Trace(rpc)
    try:
        tx = s.latest_zto_transfer(trace, lookback)
        return {"state": "candidate", "transactionHash": tx, "settled": False,
                "note": "Discovery is not settlement; check this hash with settlement-check.",
                "reads": trace.reads}, 0
    except s.EvidenceError as exc:
        report = {"state": "discovery_failed", "settled": False, "reason": str(exc)[:1024],
                  "reads": trace.reads,
                  "next": "Use a transaction hash you already know with settlement-check; no fallback hash is selected."}
        if isinstance(exc, s.ReadFailure):
            report["failedRead"] = exc.diagnostic
        return report, 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--discover", action="store_true")
    mode.add_argument("--replay-known", action="store_true",
                      help="Offline replay of inherited real ZTO evidence, no network")
    parser.add_argument("--rpc", choices=[s.RPC_URL, "https://eth.drpc.org"], default=s.RPC_URL)
    parser.add_argument("--lookback", type=int, default=2048)
    args = parser.parse_args(argv)
    if not 1 <= args.lookback <= 16384:
        parser.error("lookback must be 1..16384")
    if args.discover:
        report, code = discover(s.RPC(args.rpc), args.lookback)
    else:
        path = Path(__file__).resolve().parent.parent / "payment-witness" / "live-evidence.json"
        try:
            sample = w.load_workspace_json(path.relative_to(Path.cwd()))
            replay = w.Replay(sample["reads"])
            report = w.verify(replay, **sample["policy"])
            if replay.index != len(replay.reads):
                raise s.EvidenceError("unused replay reads")
            report["evidenceMode"] = "offline historical real ZTO evidence; not a current observation or independent invoice"
            code = 0 if report["accepted"] else 1
        except (s.EvidenceError, OSError, ValueError, KeyError, TypeError) as exc:
            report, code = {"state": "replay_failed", "accepted": False, "reason": str(exc)[:1024]}, 2
    print(json.dumps(report, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
