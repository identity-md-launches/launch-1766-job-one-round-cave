#!/usr/bin/env python3
"""Compare two read-only Ethereum settlement/payment observations; stdlib only."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location(
    "agreement_witness", Path(__file__).resolve().parent.parent / "payment-witness" / "witness.py")
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)
s = w.settlement
PROVIDERS = ("https://ethereum-rpc.publicnode.com", "https://eth.drpc.org")
POLICY_KEYS = {"tx", "recipient", "minimum_raw", "token", "confirmations", "finalized"}


def validate_policy(policy):
    if not isinstance(policy, dict) or set(policy) != POLICY_KEYS:
        raise w.Error("policy must contain exactly the documented fields")
    tx, recipient = s.hash32(policy["tx"]), w.address(policy["recipient"])
    w.positive(policy["minimum_raw"])
    if policy["token"] not in w.TOKENS:
        raise w.Error("supported tokens are ZTO and IMD")
    if type(policy["confirmations"]) is not int or not 1 <= policy["confirmations"] <= 1000000:
        raise w.Error("confirmations must be 1..1000000")
    if type(policy["finalized"]) is not bool:
        raise w.Error("finalized must be boolean")
    return dict(policy, tx=tx, recipient=recipient)


def observe(rpc, policy):
    try:
        return w.verify(rpc, **policy)
    except (w.Error, ValueError, TypeError, KeyError, OSError):
        # A provider's body/path/exception text is never a diagnostic artifact.
        return {"accepted": False, "state": "unverifiable",
                "reason": "Provider observation could not be verified"}


def fingerprint(report):
    """Compare policy-relevant facts, allowing advancing latest/finalized heads."""
    evidence = report.get("transferEvidence")
    if evidence is not None:
        evidence = dict(evidence, events=sorted(evidence["events"], key=lambda e: e["logIndex"]))
    return {"chainId": report.get("chainId"),
            "transactionHash": report.get("transactionHash"),
            "inclusion": report.get("inclusion"),
            "execution": report.get("execution"),
            "transferEvidence": evidence}


def compare(reports, policy):
    if not isinstance(reports, list) or len(reports) != 2:
        raise w.Error("exactly two provider reports are required")
    result = {"accepted": False, "state": "provider_error", "policy": policy,
              "providers": [{"source": url, "report": report}
                            for url, report in zip(PROVIDERS, reports)],
              "evidenceLimit": "Agreement is provider evidence, not consensus or a receipt proof."}
    if any(report.get("state") == "unverifiable" for report in reports):
        result["reason"] = "Both providers must return verifiable observations; no single-provider fallback."
        return result
    facts = [fingerprint(report) for report in reports]
    differences = [key for key in facts[0] if facts[0][key] != facts[1][key]]
    result["differences"] = differences
    if differences:
        result.update(state="evidence_disagreement", reason="Provider facts disagree; do not rely on this payment.")
    elif not all(report.get("accepted") is True for report in reports):
        result.update(state="policy_not_met", reason="Both observations must independently meet the same policy.")
    else:
        result.update(accepted=True, state="corroborated",
                      reason="Both observations meet policy and agree on inclusion, execution and selected-token events.")
    return result


def collect(policy, rpc_factory=s.RPC):
    policy = validate_policy(policy)  # Refuse invalid input before any read.
    reports, providers = [], []
    for source in PROVIDERS:
        recorder = w.Recorder(rpc_factory(source))
        reports.append(observe(recorder, policy))
        providers.append({"source": source, "reads": recorder.reads})
    report = compare(reports, policy)
    # A failed transcript is intentionally not publishable as successful replay.
    if all(item.get("state") != "unverifiable" for item in reports):
        report["sample"] = {"version": 1, "policy": policy, "providers": providers}
    report["evidenceMode"] = "live sequential observations from two public URLs"
    return report


def replay(sample):
    if not isinstance(sample, dict) or set(sample) != {"version", "policy", "providers"}:
        raise w.Error("invalid paired replay envelope")
    if type(sample["version"]) is not int or sample["version"] != 1:
        raise w.Error("unsupported paired replay version")
    policy = validate_policy(sample["policy"])
    providers = sample["providers"]
    if not isinstance(providers, list) or len(providers) != 2:
        raise w.Error("paired replay requires two transcripts")
    reports = []
    for source, item in zip(PROVIDERS, providers):
        if not isinstance(item, dict) or set(item) != {"source", "reads"} or item["source"] != source:
            raise w.Error("paired replay sources must be distinct and in documented order")
        rpc = w.Replay(item["reads"])
        # Invalid saved evidence is an input error, never a policy rejection.
        reports.append(w.verify(rpc, **policy))
        if rpc.index != len(rpc.reads):
            raise w.Error("unused paired replay reads")
    result = compare(reports, policy)
    result["evidenceMode"] = "offline historical observations; source labels are unauthenticated"
    return result


def exit_code(report):
    if report["accepted"]:
        return 0
    return 2 if report["state"] == "provider_error" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--tx")
    mode.add_argument("--replay", help="workspace-relative paired transcript")
    mode.add_argument("--demo", action="store_true", help="offline real-ZTO paired observation")
    parser.add_argument("--recipient")
    parser.add_argument("--minimum-raw")
    parser.add_argument("--token", choices=w.TOKENS, default="ZTO")
    parser.add_argument("--confirmations", type=int, default=12)
    parser.add_argument("--allow-unfinalized", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.demo or args.replay:
            if (args.recipient is not None or args.minimum_raw is not None or args.token != "ZTO"
                    or args.confirmations != 12 or args.allow_unfinalized):
                raise w.Error("offline replay uses saved policy; overrides are refused")
            path = args.replay
            if args.demo:
                path = str((Path(__file__).resolve().parent / "paired-evidence.json").relative_to(Path.cwd()))
            report = replay(w.load_workspace_json(path))
            if args.demo:
                report["demoNote"] = "Historical ZTO recipient/amount from ancestor observation, not an independent invoice."
        else:
            report = collect(dict(tx=args.tx, recipient=args.recipient, minimum_raw=args.minimum_raw,
                                  token=args.token, confirmations=args.confirmations,
                                  finalized=not args.allow_unfinalized))
        print(json.dumps(report, indent=2))
        return exit_code(report)
    except (w.Error, ValueError, TypeError, KeyError, OSError, RecursionError):
        print(json.dumps({"accepted": False, "state": "input_error",
                          "reason": "Invalid policy or paired replay evidence"}, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
