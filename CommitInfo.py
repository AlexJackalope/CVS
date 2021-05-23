from itertools import islice
from collections import deque

class CommitInfo:
    def __init__(self, branch=None, tag=None, comment=None, previous=None, next=None, commit=None):
        self.branch = branch
        self.tag = tag
        self.comment = comment
        self.prev_commit_index = previous
        self.next_commit_index = next
        self.commit_index = commit

    def set_last_commit_info(self, logs_file):
        info_list = []
        with open(logs_file) as f:
            info_list = list(deque(f, 7))
        if len(info_list) < 7:
            return
        self.init_info(info_list)

    def set_commit_info_by_line(self, logs_file, line):
        file = open(logs_file)
        lines = islice(file, line - 1, None)
        info_list = file.readlines(7)
        self.init_info(info_list)

    def init_info(self, info_list):
        self.branch = info_list[0]
        self.tag = info_list[1]
        self.comment = info_list[2]
        self.prev_commit_index = info_list[3]
        self.next_commit_index = info_list[4]
        self.commit_index = info_list[5]

    def set_next_commit_in_branch(self, prev_commit, tag, comment, commit):
        self.branch = prev_commit.branch
        self.tag = tag
        self.comment = comment
        self.prev_commit_index = prev_commit.commit_index
        prev_commit.next_commit_index = commit
        self.commit_index = commit

    def set_init_commit(self, tag, comment, commit):
        self.branch = 'main'
        self.tag = tag
        self.comment = comment
        self.prev_commit_index = None
        self.next_commit_index = 0
        self.commit_index = commit

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