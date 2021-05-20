import sys
import os
import unittest
import filecmp
import difflib

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             os.path.pardir))
import CVS


class TestUnidiffRestorer(unittest.TestCase):

    '''def __init__(self):
        self.dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "UnidiffRestore")

    def test_simple_text_diff(self):
        comparer = FilesComparer(null)
        text1 = "One\ntwo"
        text2 = "One"

    def test_simple_changes(self):
        first_file = os.path.join(self.dir, "SimpleBefore")
        second_file = os.path.join(self.dir, "SimpleAfter")
        restored_file = os.path.join(self.dir, "SimpleRestored")
        self.restore(first_file, second_file, restored_file)
        self.assertEqual(filecmp.cmp(restored_file, first_file), True)

    def restore(self, first, second, restored):
        restorer = CVS.UnidiffRestorer()
        file1 = open(first, 'r')
        file2 = open(second, 'r')
        unidiff = difflib.unified_diff(file1.readlines(), file2.readlines())
        file1.close()
        file2.close()
        restorer.restore_start_file(restored,
                                    second,
                                    unidiff)'''


if __name__ == '__main__':
    unittest.main()
