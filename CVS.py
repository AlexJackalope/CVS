from pathlib import Path
import argparse
import os
import sys
import pickle
import shutil
from itertools import islice
from collections import deque
from Comparers import DirContentComparer, FilesComparer


class CommitInfo:
    def __init__(self, branch=None, tag=None, comment=None, previous=None, this=None, commit=None):
        self.branch = branch
        self.tag = tag
        self.comment = comment
        self.prev_commit_line = previous
        self.this_commit_line = this
        self.commit = commit

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
        self.prev_commit_line = info_list[3]
        self.this_commit_line = info_list[4]
        self.commit = info_list[5]
        self.index = info_list[6]

    def set_next_commit_in_branch(self, prev_commit, tag, comment, line, commit, index):
        self.branch = prev_commit.branch
        self.tag = tag
        self.comment = comment
        self.prev_commit_line = prev_commit.this_commit_line
        self.this_commit_line = line
        self.commit = commit
        self.index = index

    def set_init_commit(self, tag, comment, commit):
        self.branch = 'main'
        self.tag = tag
        self.comment = comment
        self.prev_commit_line = None
        self.this_commit_line = 0
        self.commit = commit
        self.index = 0

    def log_info_to_file(self, logs_file):
        with open(logs_file, 'a') as logs:
            self._log_value(self.branch, logs)
            self._log_value(self.tag, logs)
            self._log_value(self.comment, logs)
            self._log_value(self.prev_commit_line, logs)
            self._log_value(self.this_commit_line, logs)
            self._log_value(self.commit, logs)
            self._log_value(self.index, logs)

    def _log_value(self, value, opened_file):
        if value:
            opened_file.write(value)
        opened_file.write('\n')


def is_dir_empty(path):
    return not os.listdir(path)

def does_dir_exist(path):
    return os.path.exists(path) and os.path.isdir(path)


def check_repository(path):
    repository = os.path.join(path, "repository")
    if not does_dir_exist(repository):
        sys.exit("Repository is not initialized, "
                 "call 'init' in an empty folder to do it.")
    objects = does_dir_exist(os.path.join(repository, "objects"))
    index = (os.path.exists(os.path.join(repository, "index.dat")) and
             os.path.isfile(os.path.join(repository, "index.dat")))
    tags = (os.path.exists(os.path.join(repository, "tags.dat")) and
             os.path.isfile(os.path.join(repository, "tags.dat")))
    logs = (os.path.exists(os.path.join(repository, "logs.txt")) and
            os.path.isfile(os.path.join(repository, "logs.txt")))
    if not (objects and index and tags and logs):
        sys.exit("Repository is damaged.")


def init(path):
    if not is_dir_empty(path):
        sys.exit("To initialize a repository choose an empty folder")
    os.mkdir(os.path.join(path, "repository"))
    os.mkdir(os.path.join(path, "repository", "objects"))
    os.mkdir(os.path.join(path, "repository", "last_state"))
    Path(os.path.join(path, "repository", "index.dat")).touch()
    Path(os.path.join(path, "repository", "tags.dat")).touch()
    Path(os.path.join(path, "repository", "logs.txt")).touch()
    print("Repository initialized")


def add(path, files_to_add):
    check_repository(path)
    print("Repository is OK, start comparing.")
    dir_comparer = DirContentComparer(path, files_to_add)
    dir_comparer.compare()
    add_console_log(path, dir_comparer)
    last_path = os.path.join(path, "repository", "last_state")
    filesToCompare = [[os.path.join(last_path, x),
                       os.path.join(path, x)] for x in dir_comparer.changed]
    files_comparer = FilesComparer(filesToCompare)
    diffs = files_comparer.compareFiles()
    info = {"Added": dir_comparer.added, "Deleted": dir_comparer.deleted, "Changed": diffs}
    index_file = os.path.join(path, "repository", "index.dat")
    with open(index_file, 'ab') as dump_out:
        pickle.dump(info, dump_out)
    update_last_state(path, dir_comparer)
    print("Adding finished")
    '''with open(index_file, 'rb') as dump_in:
        der = pickle.load(dump_in)'''


def update_last_state(path, comparer):
    repo_path = os.path.join(path, "repository", "last_state")
    for file in comparer.deleted:
        to_delete = os.path.join(repo_path, file)
        os.chmod(to_delete, 0o777)
        if os.path.isdir(to_delete):
            shutil.rmtree(to_delete)
        else:
            os.remove(to_delete)
    for file in comparer.added:
        to_add = os.path.join(path, file)
        copy_path = os.path.join(repo_path, file)
        copy_dir_path = os.path.dirname(copy_path)
        if not os.path.exists(copy_dir_path):
            os.makedirs(copy_dir_path)
        Path(copy_path).touch()
        shutil.copyfile(to_add, copy_path)
    for file in comparer.changed:
        changed = os.path.join(path, file)
        copy_path = os.path.join(repo_path, file)
        shutil.copyfile(changed, copy_path)


def add_console_log(path, comparer):
    print("    Added files:")
    log_paths(path, comparer.added)
    print("    Deleted files:")
    log_paths(path, comparer.deleted)
    print("    Changed files:")
    log_paths(path, comparer.changed)


def log_paths(path, to_log):
    if len(to_log) == 0:
        print("No files")
    else:
        for file in to_log:
            print(file)


def commit(path, tag=None, comment=None):
    check_repository(path)
    print("Repository is OK, start committing.")
    index_file = os.path.join(path, "repository", "index.dat")
    logs_file = os.path.join(path, "repository", "logs.txt")
    last_commit = CommitInfo()
    last_commit.set_last_commit_info(logs_file)
    commit_index = 1
    if last_commit.commit is not None:
        commit_index = last_commit.index + 1
    commit_file = os.path.join(path, "repository", "objects", str(commit_index) + ".dat")
    shutil.copyfile(index_file, commit_file)
    current_commit = CommitInfo()
    if last_commit.commit is None:
        current_commit.set_init_commit(tag, comment, commit_file)
        current_commit.log_info_to_file(logs_file)
    else:
        current_commit.set_next_commit_in_branch(last_commit, tag, comment, 9, commit_file, 1)
    print('Committing finished')


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", help="CVS command")
    parser.add_argument("path", help="path to a folder with repository")
    parser.add_argument("files", nargs='*',
                        help="bunch of files to add (only for 'add' command)")
    parser.add_argument("-c", "--comment", help="comment for new commit")
    parser.add_argument("-t", "--tag", help="tag of the commit")
    return parser.parse_args()


def main():
    args = parse_args()
    if not does_dir_exist(args.path):
        sys.exit("Given directory does not exist")
    if args.command == "init":
        init(args.path)
    if args.command == "add":
        add(args.path, args.files)
    if args.command == "commit":
        commit(args.path, args.tag, args.comment)


if __name__ == '__main__':
    main()
