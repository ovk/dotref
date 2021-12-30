import os
import io
import sys
import contextlib
import pathlib
import tempfile
import shutil
import dotref
from unittest import TestCase, main, mock


class TestE2e(TestCase):

    root_profile = """
    {
        "extends": [ "child" ],
        "vars": { "name": "root" },
        "create": [ { "name": "root", "root": "foo" } ],
        "link": [ { "src": "root", "dst": "root_link" } ]
    }
    """

    child_profile = """
    {
        "vars": { "name": "child", "child": "bar"},
        "template": [ { "src": "test.tpl", "dst": "test.txt" } ]
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

    def runDotref(self, args, expectedOutput):
        stdout = io.StringIO()
        with mock.patch.object(sys, 'argv', ['dotref'] + args), contextlib.redirect_stdout(stdout):
            dotref.main()
        self.assertEqual(stdout.getvalue(), expectedOutput)

    def test_cli(self):
        # Version
        self.runDotref(['version'], 'dotref ' + dotref.__version__ + '\n')

        dotdir = pathlib.Path('test_dotdir')
        dotdir.mkdir()
        statefile = dotdir / 'sf.json'
        fname_root = pathlib.Path(dotdir / 'root.json')
        fname_child = pathlib.Path(dotdir / 'child.json')
        self.writeFile(fname_root, self.root_profile)
        self.writeFile(fname_child, self.child_profile)
        self.writeFile('test.tpl', 'Test $name $child')

        # Init
        self.runDotref(['init', '-p', 'root', '-d', str(dotdir), '-s', 'sf.json'],
                'Successfully initialized to use profile root\n')

        with open(statefile, 'r') as f:
            self.assertEqual(f.read(), '{"profile": "root"}')

        # Profiles
        self.runDotref(['profiles', '-d', str(dotdir), '-s', 'sf.json'], """root  (child)
child\u0020

Current profile: root
""")

        self.runDotref(['profiles', '-p', 'root', '-d', str(dotdir), '-s', 'sf.json'], """root
+-- child

Variables:
    name:  root
    child: bar (child)

Create:
    root: default mode

Link:
    root: root_link

Template:
    test.tpl: test.txt (child)
""")

        # Sync
        self.runDotref(['sync', '-d', str(dotdir), '-s', 'sf.json'], """Profile: root

Create:
    [CREATED]  ./root\u0020

Link:
    [LINKED]   ./root  ->  ./root_link

Template:
    [RENDERED] ./test.tpl  ->  ./test.txt

sync completed successfully and no conflicts were detected
""")

        self.assertTrue(pathlib.Path('root').exists())
        self.assertTrue(pathlib.Path('root_link').samefile('root'))
        with open('test.txt', 'r') as f:
            self.assertEqual(f.read(), 'Test root bar')

        # Status
        self.runDotref(['status', '-d', str(dotdir), '-s', 'sf.json'], """Profile: root

Create:
    [OK]       ./root\u0020

Link:
    [OK]       ./root  ->  ./root_link

Template:
    [OK]       ./test.tpl  ->  ./test.txt

status completed successfully and no conflicts were detected
""")

        # Unlink
        self.runDotref(['unlink', '-d', str(dotdir), '-s', 'sf.json'], """Profile: root

Link:
    [UNLINKED] ./root  ->  ./root_link

Template:
    [UNLINKED] ./test.tpl  ->  ./test.txt

unlink completed successfully and no conflicts were detected
""")

        self.assertTrue(pathlib.Path('root').exists())
        self.assertFalse(pathlib.Path('root_link').exists())
        self.assertFalse(pathlib.Path('test.txt').exists())


if __name__ == '__main__':
    main()
