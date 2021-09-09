import unittest
from CommitInfo import CommitInfo


class TestCommitInfo(unittest.TestCase):
    def test_next_on_branch(self):
        current = CommitInfo()
        current.set_init_commit('first')
        next = CommitInfo()
        next.set_next_commit_on_branch(current, 'second')
        self.assertEqual(current.branch, next.branch)
        self.assertEqual(current.next_on_branch, next.commit)
        self.assertEqual(current.commit, next.prev_commit)

    def test_get_all_branches(self):
        current = CommitInfo()
        with self.assertRaises(AttributeError):
            a = current.all_commit_branches()
        current.set_init_commit('first')
        self.assertEqual(1, len(current.all_commit_branches()))
        current.branches_next['branch'] = None
        self.assertEqual(2, len(current.all_commit_branches()))
        self.assertTrue('branch' in current.all_commit_branches())

    def test_setting_branch(self):
        current = CommitInfo()
        current.set_init_commit('first')
        next = CommitInfo()
        next.set_next_commit_on_branch(current, 'second')
        current.set_new_branch('branch')
        self.assertEqual(current.branch, 'branch')
        self.assertIsNone(current.next_on_branch)
        self.assertTrue('main' in current.all_commit_branches())
        self.assertEqual(current.branches_next['main'], 'second')

    def test_next_commit_on_branch(self):
        current = CommitInfo()
        current.set_init_commit('first')
        self.assertIsNone(current.get_next_commit_on_branch('main'))
        current.next_on_branch = 'main next'
        current.branches_next['branch'] = 'next on branch'
        self.assertEqual(current.get_next_commit_on_branch('main'),
                         'main next')
        self.assertEqual(current.get_next_commit_on_branch('branch'),
                         'next on branch')
        with self.assertRaises(ValueError):
            a = current.get_next_commit_on_branch('no')

    def test_get_all_next_commits(self):
        current = CommitInfo()
        self.assertEqual(0, len(current.get_all_next_commits()))
        current.next_on_branch = 'one'
        current.branches_next['branch'] = 'two'
        current.branches_next['branch2'] = None
        self.assertEqual(current.get_all_next_commits(), ['one', 'two'])


if __name__ == '__main__':
    unittest.main()
