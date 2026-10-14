#!/usr/bin/env python3
"""Regression checks; temporary fixtures stay under test/scratch/."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import types
import unittest

SOURCE = Path('line-2/tools/repair-review/review.py')
review = types.ModuleType('review_under_test')
review.__file__ = str(SOURCE.absolute())
exec(compile(SOURCE.read_bytes(), str(SOURCE), 'exec'), review.__dict__)
bounded = review.bounded_module()
engine = bounded.engine_module()


class ReviewTests(unittest.TestCase):
    def setUp(self):
        Path('test/scratch').mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir='test/scratch')
        self.root = Path(self.temp.name).relative_to(Path.cwd()) if Path(self.temp.name).is_absolute() else Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def write(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value), encoding='utf-8')
        return str(path)

    def cli(self, contract, before, after, *flags):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = review.main([contract, before, after, *flags])
        return code, json.loads(out.getvalue())

    def test_complete_repair(self):
        c = engine.prepare({'type': 'integer', 'minimum': 2})
        r = review.compare(engine, c, 1, 2)
        self.assertTrue(r['valid'])
        self.assertEqual(r['summary'], dict(before=1, after=0, resolved=1, persistent=0, introduced=0))

    def test_partial_repair_flags(self):
        c = self.write('contract.json', {'type': 'array', 'items': {'type': 'integer'}})
        b = self.write('before.json', ['bad', 'bad'])
        a = self.write('after.json', [1, 'bad'])
        code, result = self.cli(c, b, a)
        self.assertEqual(code, 1)
        self.assertFalse(result['valid'])
        self.assertTrue(result['no_new_violations'])
        self.assertEqual(result['persistent'][0]['path'], '/1')
        self.assertEqual(self.cli(c, b, a, '--require-no-new')[0], 0)

    def test_regression_rejected_in_both_modes(self):
        c = self.write('contract.json', {'type': 'integer'})
        b = self.write('before.json', 3)
        a = self.write('after.json', '3')
        for flags in [(), ('--require-no-new',)]:
            code, result = self.cli(c, b, a, *flags)
            self.assertEqual(code, 1)
            self.assertEqual(result['summary']['introduced'], 1)

    def test_pointer_escaping_and_order(self):
        c = engine.prepare({'type': 'object', 'properties': {
            'a/b~c': {'type': 'integer'}, 'next': {'type': 'boolean'}}})
        r = review.compare(engine, c, {'a/b~c': 'x', 'next': 1}, {'a/b~c': 2, 'next': 1})
        self.assertEqual(r['resolved'][0]['path'], '/a~1b~0c')
        self.assertEqual(r['persistent'][0]['path'], '/next')

    def test_location_change_is_new(self):
        c = engine.prepare({'type': 'array', 'items': {'type': 'integer'}})
        r = review.compare(engine, c, ['bad', 1], [1, 'bad'])
        self.assertEqual((r['summary']['resolved'], r['summary']['introduced']), (1, 1))

    def test_multiset_multiplicity(self):
        e = {'path': '/x', 'rule': 'type', 'message': 'expected integer'}
        self.assertEqual(review.partition([e, e], [e]), ([e], [e], []))
        self.assertEqual(review.partition([e], [e, e]), ([], [e], [e]))

    def test_message_identity(self):
        old = {'path': '', 'rule': 'uniqueItems', 'message': 'duplicates item at /0'}
        new = dict(old, message='duplicates item at /1')
        self.assertEqual(review.partition([old], [new]), ([old], [], [new]))

    def test_identical_valid(self):
        r = review.compare(engine, {'type': 'null'}, None, None)
        self.assertTrue(r['before_valid'] and r['valid'])
        self.assertFalse(any(r['summary'].values()))

    def test_bad_contract_fails_closed(self):
        c = self.write('contract.json', {'type': 'integer', 'typo': True})
        a = self.write('after.json', 1)
        code, result = self.cli(c, a, a, '--require-no-new')
        self.assertEqual(code, 2)
        self.assertIn('unsupported rules', result['error'])

    def test_bad_json_cannot_be_resolved(self):
        c = self.write('contract.json', {'type': 'integer'})
        a = self.write('after.json', 1)
        b = self.root / 'bad.json'
        for content in ['{', '{"x": 1, "x": 2}', 'NaN', '1e9999']:
            b.write_text(content)
            for before, after in [(str(b), a), (a, str(b))]:
                code, result = self.cli(c, before, after, '--require-no-new')
                self.assertEqual(code, 2)
                self.assertIn('error', result)
                self.assertNotIn('resolved', result)

    def test_file_boundaries(self):
        c = self.write('contract.json', {'type': 'integer'})
        a = self.write('after.json', 1)
        link = self.root / 'link.json'
        link.symlink_to('after.json')
        large = self.root / 'large.json'
        large.write_bytes(b' ' * 1_000_001)
        for bad in [str(link), str(large), str(Path(a).absolute()),
                    str(self.root / '..' / 'bad.json'), 'missing.json']:
            self.assertEqual(self.cli(c, bad, a)[0], 2)

    def test_example(self):
        prefix = 'line-2/tools/repair-review/'
        code, result = self.cli(prefix+'handoff.contract.json', prefix+'before.example.json',
                                prefix+'after.example.json')
        self.assertEqual(code, 0)
        self.assertEqual(result['summary']['resolved'], 2)


if __name__ == '__main__':
    unittest.main()
