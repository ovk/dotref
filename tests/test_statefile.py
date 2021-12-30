import pathlib
import tempfile
import shutil
import json
from unittest import TestCase, main
from dotref import StateFile


class TestStateFile(TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_invalid_json(self):
        path = self.tmpdir + '/invalid.json'

        with open(path, 'w') as f:
            f.write('{ "profile": invalid_json }')
        self.assertRaises(json.decoder.JSONDecodeError, StateFile, pathlib.Path(path))

        with open(path, 'w') as f:
            f.write('{ "profile": 42 }')
        self.assertRaises(TypeError, StateFile, pathlib.Path(path))

    def test_load_save(self):
        path = self.tmpdir + '/valid.json'

        with open(path, 'w') as f:
            f.write('{ "profile": "foo" }')

        sf = StateFile(pathlib.Path(path))
        self.assertEqual(sf.profile, 'foo')

        sf.profile = 'bar'
        sf.save()

        with open(path, 'r') as f:
            self.assertEqual(f.read(), '{"profile": "bar"}')


if __name__ == '__main__':
    main()
