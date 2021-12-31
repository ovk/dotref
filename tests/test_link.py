import pathlib
import tempfile
import shutil
from unittest import TestCase, main
from dotref import LinkAction, ActionState, ActionType


class TestLink(TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def apply(self, src, dst):
        action = LinkAction('foo', {'src': str(src), 'dst': str(dst)})
        state, asrc, adst = action.apply(ActionType.STATUS)
        self.assertEqual(state, ActionState.MISSING)
        self.assertEqual(asrc, src)
        self.assertEqual(adst, dst)

        state, _, _ = action.apply(ActionType.UNLINK)
        self.assertEqual(state, ActionState.OK)
        self.assertFalse(dst.exists())

        state, _, _ = action.apply(ActionType.SYNC)
        self.assertEqual(state, ActionState.LINKED)
        self.assertTrue(dst.exists())
        self.assertTrue(dst.is_symlink())
        self.assertTrue(dst.samefile(src))

        state, _, _ = action.apply(ActionType.SYNC)
        self.assertEqual(state, ActionState.OK)

        state, _, _ = action.apply(ActionType.STATUS)
        self.assertEqual(state, ActionState.OK)

        state, _, _ = action.apply(ActionType.UNLINK)
        self.assertEqual(state, ActionState.UNLINKED)
        self.assertFalse(dst.exists())
        self.assertTrue(src.exists())

    def test_src_does_not_exist(self):
        action = LinkAction('foo', {'src': 'foo', 'dst': 'bar'})
        self.assertRaises(ValueError, action.apply, ActionType.STATUS)

    def test_apply_file(self):
        src_dir = pathlib.Path(self.tmpdir) / 'src'
        dst_dir = pathlib.Path(self.tmpdir) / 'dst'
        src_dir.mkdir()
        dst_dir.mkdir()

        src = pathlib.Path(self.tmpdir) / 'src' / 'foo.src'
        dst = pathlib.Path(self.tmpdir) / 'dst' / 'foo.dst'
        with open(src, 'w') as f:
            f.write('hello')

        self.apply(src, dst)

    def test_apply_dir(self):
        src_dir = pathlib.Path(self.tmpdir) / 'src'
        dst_dir = pathlib.Path(self.tmpdir) / 'dst'
        src_dir.mkdir()
        dst_dir.mkdir()

        src = pathlib.Path(self.tmpdir) / 'src' / 'foo_src'
        dst = pathlib.Path(self.tmpdir) / 'dst' / 'foo_dst'
        src.mkdir()

        with open(src / 'somefile', 'w') as f:
            f.write('hello')

        self.apply(src, dst)

    def test_apply_conflict(self):
        src = pathlib.Path(self.tmpdir) / 'src.file'
        dst = pathlib.Path(self.tmpdir) / 'dst.file'

        with open(src, 'w') as f:
            f.write('hello')

        with open(dst, 'w') as f:
            f.write('hello')

        action = LinkAction('foo', {'src': str(src), 'dst': str(dst)})
        state, _, _ = action.apply(ActionType.STATUS)
        self.assertEqual(state, ActionState.CONFLICT)

        state, _, _ = action.apply(ActionType.SYNC)
        self.assertEqual(state, ActionState.CONFLICT)

        state, _, _ = action.apply(ActionType.UNLINK)
        self.assertEqual(state, ActionState.CONFLICT)

        dst = pathlib.Path(self.tmpdir) / 'dst.dir'
        dst.mkdir()

        action = LinkAction('foo', {'src': str(src), 'dst': str(dst)})
        state, _, _ = action.apply(ActionType.STATUS)
        self.assertEqual(state, ActionState.CONFLICT)

        state, _, _ = action.apply(ActionType.SYNC)
        self.assertEqual(state, ActionState.CONFLICT)


if __name__ == '__main__':
    main()
