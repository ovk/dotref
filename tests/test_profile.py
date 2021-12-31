import os
import io
import contextlib
import pathlib
import tempfile
import shutil
from unittest import TestCase, main, mock
from dotref import Profile, ProfileError, ActionType, Logger


class TestProfile(TestCase):

    root_profile = """
    {
        "extends": [ "child_a" ],
        "vars": { "name": "root" },
        "create": [ { "name": "root" } ],
        "link": [ { "src": "root", "dst": "root_link" } ]
    }
    """

    child_a_profile = """
    {
        "extends": [ "child_b" ],
        "vars": { "name": "child_a", "child": "a"},
        "template": [ { "src": "test.tpl", "dst": "test.txt" } ]
    }
    """

    child_b_profile = """
    {
        "vars": { "name": "child_b", "child": "b", "foo": "bar"},
        "create": [ { "name": "child" } ],
        "link": [ { "src": "child", "dst": "child_b" } ]
    }
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cwd = os.getcwd()
        os.chdir(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        os.chdir(self.cwd)

    def writeFile(self, name, content):
        with open(name, 'w') as f:
            f.write(content)

    def test_invalid_json(self):
        fname = pathlib.Path(self.tmpdir, 'test.json')

        self.writeFile(fname, '{"invalid": json}')
        self.assertRaises(ProfileError, Profile, fname)

        self.writeFile(fname, '{"extends": "foo"}')
        self.assertRaises(ProfileError, Profile, fname)

        self.writeFile(fname, '{"extends": [42]}')
        self.assertRaises(ProfileError, Profile, fname)

        self.writeFile(fname, '{"vars": 42}')
        self.assertRaises(ProfileError, Profile, fname)

        self.writeFile(fname, '{"vars": {"a": 5}}')
        self.assertRaises(ProfileError, Profile, fname)

        self.writeFile(fname, '{"create": 42}')
        self.assertRaises(ProfileError, Profile, fname)

        self.writeFile(fname, '{"link": 42}')
        self.assertRaises(ProfileError, Profile, fname)

        self.writeFile(fname, '{"template": 42}')
        self.assertRaises(ProfileError, Profile, fname)

    def test_parse(self):
        fname = pathlib.Path(self.tmpdir, 'test.json')
        self.writeFile(fname, '{"extends": ["foo", "bar"], "vars": {"a": "b"}, \
                "create": [{"name": "foo", "mode": "750"}], \
                "link": [{"src": "from", "dst": "to"}], \
                "template": [{"src": "tpl", "dst": "bar"}]}')

        p = Profile(fname)
        self.assertEqual(p.name, 'test')
        self.assertListEqual(p.extends, ['foo', 'bar'])
        self.assertEqual(p.vars[0].name, 'a')
        self.assertEqual(p.vars[0].value, 'b')
        self.assertEqual(p.create[0].name, 'foo')
        self.assertEqual(p.create[0].mode, 488)
        self.assertEqual(p.link[0].src, 'from')
        self.assertEqual(p.link[0].dst, 'to')
        self.assertEqual(p.template[0].src, 'tpl')
        self.assertEqual(p.template[0].dst, 'bar')

    @mock.patch.dict(os.environ, {'NO_COLOR': '1'})
    def test_pretty_print(self):
        fname_root = pathlib.Path(self.tmpdir, 'root.json')
        fname_child_a = pathlib.Path(self.tmpdir, 'child_a.json')
        fname_child_b = pathlib.Path(self.tmpdir, 'child_b.json')
        self.writeFile(fname_root, self.root_profile)
        self.writeFile(fname_child_a, self.child_a_profile)
        self.writeFile(fname_child_b, self.child_b_profile)

        prof_child_b = Profile(fname_child_b)
        prof_child_b.parents = []
        prof_child_a = Profile(fname_child_a)
        prof_child_a.parents = [prof_child_b]
        prof_root = Profile(fname_root)
        prof_root.parents = [prof_child_a]

        log = Logger()
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            prof_root.pretty_print(log)

        self.assertEqual(stdout.getvalue(), """root
+-- child_a
    +-- child_b

Variables:
    name:  root
    child: a (child_a)
    foo:   bar (child_b)

Create:
    root:  default mode
    child: default mode (child_b)

Link:
    root:  root_link
    child: child_b (child_b)

Template:
    test.tpl: test.txt (child_a)
""")

    @mock.patch.dict(os.environ, {'NO_COLOR': '1'})
    def test_apply(self):
        fname_root = pathlib.Path('root.json')
        fname_child_a = pathlib.Path('child_a.json')
        fname_child_b = pathlib.Path('child_b.json')
        self.writeFile(fname_root, self.root_profile)
        self.writeFile(fname_child_a, self.child_a_profile)
        self.writeFile(fname_child_b, self.child_b_profile)

        template_src = pathlib.Path('test.tpl')
        self.writeFile(template_src, 'Rendered $name $child $foo')

        prof_child_b = Profile(fname_child_b)
        prof_child_b.parents = []
        prof_child_a = Profile(fname_child_a)
        prof_child_a.parents = [prof_child_b]
        prof_root = Profile(fname_root)
        prof_root.parents = [prof_child_a]

        log = Logger()
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            prof_root.action(ActionType.SYNC, log)

        self.assertEqual(stdout.getvalue(), """Profile: root

Create:
    [CREATED]  ./root\u0020\u0020
    [CREATED]  ./child\u0020

Link:
    [LINKED]   ./root   ->  ./root_link
    [LINKED]   ./child  ->  ./child_b

Template:
    [RENDERED] ./test.tpl  ->  ./test.txt

sync completed successfully and no conflicts were detected
""")

        self.assertTrue(pathlib.Path('root').exists())
        self.assertTrue(pathlib.Path('child').exists())
        self.assertTrue(pathlib.Path('root_link').samefile('root'))
        self.assertTrue(pathlib.Path('child_b').samefile('child'))

        with open('test.txt', 'r') as f:
            self.assertEqual(f.read(), 'Rendered root a bar')

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            prof_root.action(ActionType.UNLINK, log)

        self.assertEqual(stdout.getvalue(), """Profile: root

Link:
    [UNLINKED] ./root   ->  ./root_link
    [UNLINKED] ./child  ->  ./child_b

Template:
    [UNLINKED] ./test.tpl  ->  ./test.txt

unlink completed successfully and no conflicts were detected
""")

        self.assertTrue(pathlib.Path('root').exists())
        self.assertTrue(pathlib.Path('child').exists())
        self.assertFalse(pathlib.Path('root_link').exists())
        self.assertFalse(pathlib.Path('child_b').exists())
        self.assertFalse(pathlib.Path('test.txt').exists())


if __name__ == '__main__':
    main()
