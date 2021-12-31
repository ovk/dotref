import os
import pathlib
import tempfile
import shutil
from unittest import TestCase, main
from dotref import CreateAction, ActionState, ActionType


class TestCreate(TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_invalid_json(self):
        self.assertRaises(TypeError, CreateAction, 'foo', 'string')
        self.assertRaises(TypeError, CreateAction, 'foo', {'foo': 'bar'})
        self.assertRaises(TypeError, CreateAction, 'foo', {'name': 42})
        self.assertRaises(TypeError, CreateAction, 'foo', {'name': 'bar', 'mode': 777})
        self.assertRaises(ValueError, CreateAction, 'foo', {'name': 'bar', 'mode': '778'})

    def test_apply_ok(self):
        path = pathlib.Path(self.tmpdir) / 'foo'
        action = CreateAction('foo', {'name': str(path), 'mode': '742'})
        state, dir, none = action.apply(ActionType.STATUS)
        self.assertEqual(state, ActionState.MISSING)
        self.assertEqual(dir, path)
        self.assertIsNone(none)
        self.assertFalse(path.exists())

        state, _, _ = action.apply(ActionType.UNLINK)
        self.assertEqual(state, ActionState.OK)
        self.assertFalse(path.exists())

        state, _, _ = action.apply(ActionType.SYNC)
        self.assertEqual(state, ActionState.CREATED)
        self.assertTrue(path.exists())
        umask = os.umask(0o666)
        os.umask(umask)
        self.assertEqual(path.stat().st_mode & 0o777, 0o742 & (~umask))

        state, _, _ = action.apply(ActionType.SYNC)
        self.assertEqual(state, ActionState.OK)
        self.assertTrue(path.exists())

        state, _, _ = action.apply(ActionType.STATUS)
        self.assertEqual(state, ActionState.OK)

        state, _, _ = action.apply(ActionType.UNLINK)
        self.assertEqual(state, ActionState.OK)
        self.assertTrue(path.exists())

    def test_apply_conflict(self):
        path = pathlib.Path(self.tmpdir) / 'foo.file'
        with open(path, 'w') as f:
            f.write('hello')

        action = CreateAction('foo', {'name': str(path)})
        state, dir, _ = action.apply(ActionType.STATUS)
        self.assertEqual(state, ActionState.CONFLICT)
        self.assertEqual(dir, path)

        state, _, _ = action.apply(ActionType.SYNC)
        self.assertEqual(state, ActionState.CONFLICT)

        state, _, _ = action.apply(ActionType.UNLINK)
        self.assertEqual(state, ActionState.CONFLICT)

        self.assertTrue(path.exists())


if __name__ == '__main__':
    main()
