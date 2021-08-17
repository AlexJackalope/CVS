import sys
import os
import unittest
from Comparers import DirContentComparer, FilesComparer
import difflib

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             os.path.pardir))


class TestDirContentComparer(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestDirContentComparer, self).__init__(*args, **kwargs)
        self.dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "FolderToCompare")
        self.comparer = DirContentComparer(self.dir)
        self.comparer.compare()

    @staticmethod
    def expected_list(filename):
        first_level = os.path.join("Folder", "OneLevel" + filename)
        second_level = os.path.join("Folder", "Folder", "TwoLevels" + filename)
        return [filename, first_level, second_level]

    def test_all_added_files(self):
        comparer_added = self.comparer.added
        added_list = self.expected_list("Added.txt")
        added_list.append(os.path.join("AddedFolder", "Added.txt"))
        self.assertEqual(len(added_list), len(comparer_added))
        for file in comparer_added:
            self.assertTrue(file in added_list)

    def test_all_changed_files(self):
        comparer_changed = self.comparer.changed
        changed_list = self.expected_list("Changed.txt")
        self.assertEqual(len(changed_list), len(comparer_changed))
        for file in comparer_changed:
            self.assertTrue(file in changed_list)

    def test_all_deleted_files(self):
        comparer_deleted = self.comparer.deleted
        deleted_list = self.expected_list("Deleted.txt")
        self.assertEqual(len(deleted_list), len(comparer_deleted))
        for file in comparer_deleted:
            self.assertTrue(file in deleted_list)


class TestFileComparerRestoring(unittest.TestCase):
    def comparing(self, start, finish):
        diff = difflib.unified_diff(start, finish, n=0)
        delta = [x for x in diff]
        self.assertEqual(FilesComparer.previous_file_version(finish, delta),
                         start)
        self.assertEqual(FilesComparer.next_file_version(start, delta), finish)

    def test_restore_string_adding(self):
        start = ["one", "two"]
        finish = ["one", "three", "two"]
        self.comparing(start, finish)

    def test_restore_string_deleting(self):
        start = ["one", "two", "three"]
        finish = ["two", "three"]
        self.comparing(start, finish)

    def test_restore_string_changing(self):
        start = ["one", "two", "three", "five"]
        finish = ["one", "two", "four", "five"]
        self.comparing(start, finish)

    def test_restore_distant_changes(self):
        start = ["one", "two", "three", "four", "five",
                 "six", "seven", "eight", "nine", "ten",
                 "one", "two", "three", "four", "five",
                 "six", "seven", "eight", "nine", "ten"]
        finish = ["one", "three", "four", "five",
                  "six", "seven", "eight", "nine", "twenty",
                  "one", "two", "three", "one", "four", "five",
                  "six", "seven", "eight", "nine", "5"]
        self.comparing(start, finish)


if __name__ == '__main__':
    unittest.main()
