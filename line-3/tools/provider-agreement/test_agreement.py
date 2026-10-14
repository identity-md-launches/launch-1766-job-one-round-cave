"""Offline adversarial tests. Paired fixtures reuse one historical observation.

Only paired-evidence.json records two actual sources; these manipulated fixtures
make no claim about provider provenance or live Ethereum state.
"""
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import agreement as a


def fixture():
    original = a.w.load_workspace_json("line-3/tools/payment-witness/live-evidence.json")
    return {"version": 1, "policy": original["policy"],
            "providers": [{"source": source, "reads": copy.deepcopy(original["reads"])}
                          for source in a.PROVIDERS]}


class AgreementTests(unittest.TestCase):
    def test_matching_inclusion_and_payment(self):
        result = a.replay(fixture())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["state"], "corroborated")

    def test_different_sampled_heads_are_allowed(self):
        sample = fixture()
        reads = sample["providers"][1]["reads"]
        head = next(x["result"] for x in reads if x["params"] == ["latest", False])
        old_height = head["number"]
        for item in reads:
            if item["method"] == "eth_getBlockByNumber" and item["params"][0] in ("latest", old_height):
                item["result"]["number"] = hex(int(old_height, 16) + 1)
                item["result"]["hash"] = "0x" + "ab" * 32  # offline fixture only
                if item["params"][0] == old_height:
                    item["params"][0] = item["result"]["number"]
        self.assertTrue(a.replay(sample)["accepted"])

    def test_same_amount_different_events_refused(self):
        sample = fixture()
        for item in sample["providers"][1]["reads"]:
            receipt = item["result"]
            if item["method"] == "eth_getTransactionReceipt":
                event = next(log for log in receipt["logs"] if log["address"].lower() == a.w.TOKENS["ZTO"])
                event["topics"][1] = "0x" + "0" * 24 + "ab" * 20  # fixture sender
        result = a.replay(sample)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["state"], "evidence_disagreement")
        self.assertEqual(result["differences"], ["transferEvidence"])

    def test_different_inclusion_chains_refused(self):
        sample = fixture()
        reads = sample["providers"][1]["reads"]
        old = next(x["result"]["blockHash"] for x in reads if x["method"] == "eth_getTransactionReceipt")
        def replace(value):
            if isinstance(value, dict):
                return {k: replace(v) for k, v in value.items()}
            if isinstance(value, list):
                return [replace(v) for v in value]
            return "0x" + "cd" * 32 if value == old else value
        sample["providers"][1]["reads"] = replace(reads)
        result = a.replay(sample)
        self.assertFalse(result["accepted"])
        self.assertIn("inclusion", result["differences"])

    def test_policy_shortfall_is_not_an_input_error(self):
        sample = fixture()
        sample["policy"]["minimum_raw"] = str(int(sample["policy"]["minimum_raw"]) + 1)
        result = a.replay(sample)
        self.assertEqual(result["state"], "policy_not_met")
        self.assertEqual(a.exit_code(result), 1)

    def test_one_provider_failure_has_no_fallback(self):
        sample = fixture()
        calls = []
        class Failed:
            def call(self, method, params):
                raise a.s.ReadFailure(method, "transport", "fixture error")
        def factory(source):
            calls.append(source)
            return a.w.Replay(sample["providers"][0]["reads"]) if source == a.PROVIDERS[0] else Failed()
        result = a.collect(sample["policy"], factory)
        self.assertEqual(calls, list(a.PROVIDERS))
        self.assertFalse(result["accepted"])
        self.assertEqual(a.exit_code(result), 2)
        self.assertNotIn("sample", result)

    def test_invalid_policy_precedes_reads(self):
        for change in ({"confirmations": True}, {"finalized": 1}, {"recipient": None}, {"minimum_raw": "0"}):
            policy = dict(fixture()["policy"], **change)
            with self.assertRaises(a.w.Error):
                a.collect(policy, lambda url: self.fail("unexpected network construction"))

    def test_source_cardinality_and_version(self):
        for change in ("duplicate", "swapped", "missing", "bool_version", "extra"):
            sample = fixture()
            if change == "duplicate": sample["providers"][1]["source"] = a.PROVIDERS[0]
            if change == "swapped": sample["providers"].reverse()
            if change == "missing": sample["providers"].pop()
            if change == "bool_version": sample["version"] = True
            if change == "extra": sample["accepted"] = True
            with self.subTest(change=change), self.assertRaises(a.w.Error):
                a.replay(sample)

    def test_truncated_extra_and_reordered_reads(self):
        for change in ("truncated", "extra", "reordered"):
            sample = fixture()
            reads = sample["providers"][1]["reads"]
            if change == "truncated": reads.pop()
            if change == "extra": reads.append(copy.deepcopy(reads[-1]))
            if change == "reordered": reads.reverse()
            with self.subTest(change=change), self.assertRaises(a.w.Error):
                a.replay(sample)

    def test_demo_replays_two_actual_sources(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = a.main(["--demo"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output.getvalue())["accepted"])

    def test_cli_refuses_replay_policy_override(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(a.main(["--demo", "--minimum-raw", "1"]), 2)


class FileBoundaryTests(unittest.TestCase):
    def setUp(self):
        Path("test/scratch").mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir="test/scratch")
        self.root = Path(self.temp.name)
        if self.root.is_absolute():
            self.root = self.root.relative_to(Path.cwd())
        self.regular = self.root / "regular.json"
        self.regular.write_text('{"ok": true}')

    def tearDown(self):
        self.temp.cleanup()

    def test_regular_and_bounded_actual_bytes(self):
        self.assertEqual(a.w.load_workspace_json(self.regular), {"ok": True})
        self.regular.write_bytes(b" " * (a.w.LIMIT + 1))
        with self.assertRaisesRegex(a.w.Error, "90 KB"):
            a.w.load_workspace_json(self.regular)

    def test_ambiguous_json_refused(self):
        for raw in ('{"ok":true,"ok":false}', '{"x":NaN}', '[', '[[' * 2000):
            self.regular.write_text(raw)
            with self.subTest(raw=raw[:30]), self.assertRaises(a.w.Error):
                a.w.load_workspace_json(self.regular)

    def test_absolute_parent_hidden_and_empty_parts(self):
        for name in (str(self.regular.absolute()), "../file.json", ".hidden/file.json",
                     "test//scratch/file.json", "test/./scratch/file.json", "", "test\\scratch"):
            with self.subTest(name=name), self.assertRaises(a.w.Error):
                a.w.load_workspace_json(name)

    def test_leaf_and_directory_symlinks_refused(self):
        leaf = self.root / "leaf.json"
        leaf.symlink_to("regular.json")
        directory = self.root / "alias"
        directory.symlink_to(".", target_is_directory=True)
        for name in (leaf, directory / "regular.json"):
            with self.assertRaises(a.w.Error):
                a.w.load_workspace_json(name)

    def test_directory_and_fifo_refused_without_blocking(self):
        fifo = self.root / "pipe"
        os.mkfifo(fifo)
        for name in (self.root, fifo):
            with self.assertRaises(a.w.Error):
                a.w.load_workspace_json(name)

    def test_replaced_directory_stays_on_open_descriptor(self):
        directory = self.root / "input"
        directory.mkdir()
        (directory / "record.json").write_text('{"opened":"original"}')
        replacement = self.root / "replacement"
        replacement.mkdir()
        (replacement / "record.json").write_text('{"opened":"replacement"}')
        real_open = os.open
        def raced_open(path, flags, **kwargs):
            if path == "record.json":
                directory.rename(self.root / "old")
                directory.symlink_to("replacement", target_is_directory=True)
            return real_open(path, flags, **kwargs)
        # os.supports_dir_fd stores the real function identity.
        with patch.object(a.w.os, "open", raced_open), patch.object(a.w.os, "supports_dir_fd", {raced_open}):
            result = a.w.load_workspace_json(directory / "record.json")
        self.assertEqual(result, {"opened": "original"})

    def test_unsupported_platform_fails_closed(self):
        with patch.object(a.w.os, "supports_dir_fd", set()), self.assertRaises(a.w.Error):
            a.w.load_workspace_json(self.regular)


if __name__ == "__main__":
    unittest.main()
