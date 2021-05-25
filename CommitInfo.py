class CommitInfo:
    def __init__(self, branch=None, tag=None, comment=None, previous=None, next=None, commit=None):
        self.branch = branch
        self.tag = tag
        self.comment = comment
        self.prev_commit_index = previous
        self.next_commit_index = next
        self.commit_index = commit

    def set_next_commit_in_branch(self, prev_commit, tag, comment, commit_index):
        self.branch = prev_commit.branch
        self.tag = tag
        self.comment = comment
        self.prev_commit_index = prev_commit.commit_index
        prev_commit.next_commit_index = str(commit_index)
        self.commit_index = str(commit_index)

    def set_init_commit(self, tag, comment, commit_index):
        self.branch = 'main'
        self.tag = tag
        self.comment = comment
        self.prev_commit_index = None
        self.next_commit_index = str(0)
        self.commit_index = str(commit_index)

    def log_info_to_file(self, logs_file):
        with open(logs_file, 'a') as logs:
            self._log_value(self.branch, logs)
            self._log_value(self.tag, logs)
            self._log_value(self.comment, logs)
            self._log_value(self.prev_commit_index, logs)
            self._log_value(self.next_commit_index, logs)
            self._log_value(self.commit_index, logs)

    def _log_value(self, value, opened_file):
        if value:
            opened_file.write(value)
        opened_file.write('\n')
