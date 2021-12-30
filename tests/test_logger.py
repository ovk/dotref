import os
import io
import contextlib
from unittest import TestCase, mock, main
from dotref import Logger


class TestLogger(TestCase):

    def test_default_has_colors(self):
        log = Logger()
        self.assertTrue(log.colored)
        self.assertEqual(log.hl('Hello'), Logger.YELLOW + 'Hello' + Logger.RESET)

    @mock.patch.dict(os.environ, {'NO_COLOR': '1'})
    def test_no_color(self):
        log = Logger()
        self.assertFalse(log.colored)
        self.assertEqual(log.hl('Hello'), 'Hello')

    @mock.patch.dict(os.environ, {'DOTREF_NO_COLOR': '1'})
    def test_dotref_no_color(self):
        log = Logger()
        self.assertFalse(log.colored)
        self.assertEqual(log.hl('Hello'), 'Hello')

    def test_colors(self):
        log = Logger()
        self.assertTrue(log.colored)
        self.assertEqual(log.hl('Hello'), Logger.YELLOW + 'Hello' + Logger.RESET)
        self.assertEqual(log.muted('Hello'), Logger.BLUE + 'Hello' + Logger.RESET)
        self.assertEqual(log.title('Hello'), Logger.MAGENTA + 'Hello' + Logger.RESET)

    def test_output(self):
        log = Logger()
        stdout = io.StringIO()
        stderr = io.StringIO()

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            log.out('Test out')
            log.err('Test err')

        self.assertEqual(stdout.getvalue(), 'Test out')
        self.assertEqual(stderr.getvalue(), Logger.RED + 'Test err' + Logger.RESET + '\n')

    def test_tree(self):
        log = Logger()
        stdout = io.StringIO()

        tree = {'n': 'Root', 'c': [
                {'n': 'Child 1', 'c': [
                    {'n': 'Child 1.1'},
                    {'n': 'Child 1.1'}]},
                {'n': 'Child 2'},
                {'n': 'Child 3', 'c': [
                    {'n': 'Child 3.1'},
                    {'n': 'Child 3.2'}]},
                ]}

        with contextlib.redirect_stdout(stdout):
            log.print_tree(tree, lambda x: x['n'], lambda x: x['c'] if 'c' in x else [])

        self.assertEqual(stdout.getvalue(), """Root
+-- Child 1
|   +-- Child 1.1
|   +-- Child 1.1
+-- Child 2
+-- Child 3
    +-- Child 3.1
    +-- Child 3.2
""")


if __name__ == '__main__':
    main()
