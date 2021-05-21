from pathlib import Path
import argparse
import os
import sys
import shutil
import filecmp
import difflib
import pickle
import shutil
import subprocess


class DirContentComparer:
    def __init__(self, path, files):
        self._root = path
        self._repository = os.path.join(self._root, "repository")
        self._last_state = os.path.join(self._repository, "last_state")
        self._first_iter = True
        self._files = self.full_paths_to_files(path, files)
        self.added = []
        self.deleted = []
        self.changed = []

    def compare(self):
        last_state = os.path.join(self._repository, "last_state")
        self.full_closure_compare(last_state, self._root)
        self._first_iter = True

    def full_closure_compare(self, repo, orig):
        cmp = filecmp.dircmp(repo, orig, ignore=["repository"])
        relative_repo_folder = os.path.relpath(repo, self._last_state)
        if relative_repo_folder == '.':
            relative_repo_folder = ''
        self.deleted.extend(self.full_paths_to_files(
            relative_repo_folder, cmp.left_only))

        all_added = self.full_paths_to_files(orig, cmp.right_only)
        added_dirs, added_files = self.split_dirs_and_files(all_added)
        requested_added = self.requested_files_from_dir(added_files)
        self.added.extend(self.relative_paths_to_files(requested_added))
        if len(added_dirs) > 0:
            self.add_files_in_new_dirs(added_dirs)

        changed_files = self.full_paths_to_files(orig, cmp.diff_files)
        requested_changed = self.requested_files_from_dir(changed_files)
        self.changed.extend(self.relative_paths_to_files(requested_changed))

        subdirs = [file.path for file in os.scandir(orig) if file.is_dir()]
        if self._first_iter:
            self._first_iter = False
            subdirs.remove(self._repository)
        for subdir in subdirs:
            if subdir in added_dirs:
                continue
            repo_changed_dir = os.path.join(repo, os.path.basename(subdir))
            self.full_closure_compare(repo_changed_dir, subdir)

    def requested_files_from_dir(self, dir_files):
        if len(self._files) > 0:
            return list(set(dir_files) & set(self._files))
        else:
            return dir_files

    def full_paths_to_files(self, path, files):
        return list(map(lambda x: os.path.join(path, x), files))

    def relative_paths_to_files(self, files):
        return list(map(lambda x: os.path.relpath(x, self._root)
        if os.path.relpath(x, self._root) != '.' else '', files))

    def split_dirs_and_files(self, names):
        dirs = []
        files = []
        for path in names:
            if os.path.isdir(path):
                dirs.append(path)
            else:
                files.append(path)
        return dirs, files

    def add_files_in_new_dirs(self, dirs):
        for new_dir in dirs:
            dir_content = os.listdir(new_dir)
            new_dirs, new_files = self.split_dirs_and_files(
                self.full_paths_to_files(new_dir, dir_content))
            requested_added = self.requested_files_from_dir(new_files)
            self.added.extend(self.relative_paths_to_files(requested_added))
            if len(new_dirs) > 0:
                self.add_files_in_new_dirs(new_dirs)


class FilesComparer:
    def __init__(self, file_pairs):
        self.files = file_pairs
        self.deltas = {}

    def compareFiles(self):
        for pair in self.files:
            file1 = open(pair[0], 'r')
            file2 = open(pair[1], 'r')
            self.compare(file1.readlines(), file2.readlines(), pair[1])
            file1.close()
            file2.close()
        return self.deltas

    def compare(self, file1, file2, name):
        diff = difflib.unified_diff(file1, file2)
        diff_str = [x for x in diff]
        self.deltas[name] = diff_str


def is_dir_empty(path):
    return not os.listdir(path)


def check_repository(path):
    repository = os.path.join(path, "repository")
    if not does_dir_exist(repository):
        sys.exit("Repository is not initialized, "
                 "call 'init' in an empty folder to do it.")
    objects = does_dir_exist(os.path.join(repository, "objects"))
    index = (os.path.exists(os.path.join(repository, "index.dat")) and
             os.path.isfile(os.path.join(repository, "index.dat")))
    logs = (os.path.exists(os.path.join(repository, "logs.dat")) and
            os.path.isfile(os.path.join(repository, "logs.dat")))
    if not (objects and index and logs):
        sys.exit("Repository is damaged.")


def init(path):
    if not is_dir_empty(path):
        sys.exit("To initialize a repository choose an empty folder")
    os.mkdir(os.path.join(path, "repository"))
    os.mkdir(os.path.join(path, "repository", "objects"))
    os.mkdir(os.path.join(path, "repository", "last_state"))
    Path(os.path.join(path, "repository", "index.dat")).touch()
    Path(os.path.join(path, "repository", "logs.dat")).touch()
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
    update_last_state(path, dir_comparer)
    '''with open(index_file, 'wb') as dump_out:
        pickle.dump(info, dump_out)'''
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
            #repo_file = os.path.join(repo_path, "index.dat")


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


def does_dir_exist(path):
    return os.path.exists(path) and os.path.isdir(path)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", help="CVS command")
    parser.add_argument("path", help="path to a folder with repository")
    parser.add_argument("files", nargs='*',
                        help="bunch of files to add (only for 'add' command)")
    parser.add_argument("-c", "-comment", help="comment for new commit")
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


if __name__ == '__main__':
    main()
