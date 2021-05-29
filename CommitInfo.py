class CommitInfo:
    branch = None
    commit = None
    prev_commit = None
    next_on_branch = None
    branches_next = {}

    def set_init_commit(self, commit):
        self.branch = 'main'
        self.commit = commit

    def set_next_commit_on_branch(self, prev_info, commit):
        self.branch = prev_info.branch
        self.prev_commit = prev_info.commit
        self.commit = commit
        prev_info.next_on_branch = self.commit

    def set_new_branch(self, branch):
        self.branches_next[self.branch] = self.next_on_branch
        self.branch = branch
        self.next_on_branch = None

    def get_next_commit_on_branch(self, branch):
        if self.branch == branch:
            return self.next_on_branch
        if branch in self.branches_next:
            return self.branches_next[branch]
        return None
