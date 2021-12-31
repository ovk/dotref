import pathlib
import tempfile
import shutil
from unittest import TestCase, main
from dotref import TemplateAction, ActionState, ActionType


class TestTemplate(TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_missing_var(self):
        tpl = pathlib.Path(self.tmpdir) / 'foo.tpl'
        with open(tpl, 'w') as f:
            f.write('Hello $name')

        action = TemplateAction('foo', {'src': str(tpl), 'dst': str(pathlib.Path(self.tmpdir) / 'dst')})
        self.assertRaises(KeyError, action.apply, ActionType.SYNC, {'foo': 'bar'})

    def test_apply_ok(self):
        vars = {'foo': 'vara', 'bar': 'varb'}
        src = pathlib.Path(self.tmpdir) / 'src.tpl'
        dst = pathlib.Path(self.tmpdir) / 'dst.tpl'
        with open(src, 'w') as f:
            f.write('Hello $foo and ${bar}')

        action = TemplateAction('foo', {'src': str(src), 'dst': str(dst)})
        state, asrc, adst = action.apply(ActionType.STATUS, vars)
        self.assertEqual(state, ActionState.MISSING)
        self.assertEqual(src, asrc)
        self.assertEqual(dst, adst)
        self.assertFalse(dst.exists())

        state, _, _ = action.apply(ActionType.UNLINK, vars)
        self.assertEqual(state, ActionState.OK)
        self.assertFalse(dst.exists())

        state, _, _ = action.apply(ActionType.SYNC, vars)
        self.assertEqual(state, ActionState.RENDERED)
        self.assertTrue(dst.exists())
        with open(dst, 'r') as f:
            self.assertEqual(f.read(), 'Hello vara and varb')

        state, _, _ = action.apply(ActionType.SYNC, vars)
        self.assertEqual(state, ActionState.OK)

        state, _, _ = action.apply(ActionType.STATUS, vars)
        self.assertEqual(state, ActionState.OK)

        with open(src, 'w') as f:
            f.write('Hello updated $foo and ${bar}')

        state, _, _ = action.apply(ActionType.STATUS, vars)
        self.assertEqual(state, ActionState.DIFFERS)

        state, _, _ = action.apply(ActionType.UNLINK, vars)
        self.assertEqual(state, ActionState.DIFFERS)
        self.assertTrue(dst.exists())

        state, _, _ = action.apply(ActionType.SYNC, vars)
        self.assertEqual(state, ActionState.RENDERED)
        with open(dst, 'r') as f:
            self.assertEqual(f.read(), 'Hello updated vara and varb')

        state, _, _ = action.apply(ActionType.UNLINK, vars)
        self.assertEqual(state, ActionState.UNLINKED)
        self.assertFalse(dst.exists())

    def test_apply_conflict(self):
        vars = {'foo': 'vara', 'bar': 'varb'}
        src = pathlib.Path(self.tmpdir) / 'src.tpl'
        dst = pathlib.Path(self.tmpdir) / 'dst_dir'
        dst.mkdir()
        with open(src, 'w') as f:
            f.write('Hello $foo and ${bar}')

        action = TemplateAction('foo', {'src': str(src), 'dst': str(dst)})
        state, _, _ = action.apply(ActionType.STATUS, vars)
        self.assertEqual(state, ActionState.CONFLICT)


if __name__ == '__main__':
    main()
