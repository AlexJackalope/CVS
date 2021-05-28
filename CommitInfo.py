class CommitInfo:
    branch = None
    commit = None
    prev_commit = None
    next_on_branch = None
    branches_next = {}

    def set_init_commit(self, commit):
        self.branch = 'main'
        self.prev_commit = None
        self.commit = str(commit)

    def set_next_commit_on_branch(self, prev_info, commit):
        self.branch = prev_info.branch
        self.prev_commit = prev_info.commit
        self.commit = str(commit)
        prev_info.next_on_branch = self.commit

    def set_new_branch(self, branch):
        self.branches_next[self.branch] = self.next_on_branch
        self.branch = branch
        self.next_on_branch = None
