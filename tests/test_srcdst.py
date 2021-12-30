from unittest import TestCase, main
from dotref import SrcDstAction


class TestSrcDst(TestCase):

    def test_invalid_json(self):
        self.assertRaises(TypeError, SrcDstAction, 'foo', 'bar', 'string')
        self.assertRaises(TypeError, SrcDstAction, 'foo', 'bar', {'src': 42, 'dst': 'bar'})
        self.assertRaises(TypeError, SrcDstAction, 'foo', 'bar', {'src': 'foo'})

    def test_load(self):
        action = SrcDstAction('foo', 'bar', {'src': 'foo', 'dst': 'bar'})
        self.assertEqual(action.src, 'foo')
        self.assertEqual(action.dst, 'bar')


if __name__ == '__main__':
    main()
