class CommitInfo:
    branch = None
    commit = None
    prev_commit = None
    next_on_branch = None
    branches_next = {}

    def __getstate__(self):
        attributes = self.__dict__.copy()
        attributes['branches_next'] = self.branches_next
        attributes['prev_commit'] = self.prev_commit
        return attributes

    def set_init_commit(self, commit):
        self.branch = 'main'
        self.commit = commit

    def set_next_commit_on_branch(self, prev_info, commit):
        self.branch = prev_info.branch
        self.prev_commit = prev_info.commit
        self.commit = commit
        prev_info.next_on_branch = self.commit

    def set_new_branch(self, branch):
        next_on_branch = self.next_on_branch
        cur_branch = self.branch
        self.branches_next[cur_branch] = next_on_branch
        self.branch = branch
        self.next_on_branch = None

    def all_commit_branches(self):
        if self.branch is None:
            raise AttributeError('Commit branch is not initialized')
        branches = [self.branch]
        for branch in self.branches_next:
            branches.append(branch)
        return branches

    def get_next_commit_on_branch(self, branch):
        if self.branch == branch:
            return self.next_on_branch
        if branch in self.branches_next:
            return self.branches_next[branch]
        raise ValueError(f'Commit {self.commit} is not on branch {branch}.')

    def get_all_next_commits(self):
        next = []
        if self.next_on_branch is not None:
            next.append(self.next_on_branch)
        for commit in self.branches_next.values():
            if commit is not None:
                next.append(commit)
        return next
