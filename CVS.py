from pathlib import Path
import argparse
import os
import sys
import filecmp


class StatesComparer:
    def __init__(self, path, files):
        self._root = path
        self._repository = os.path.join(self._root, "repository")
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
        a = cmp.left_only
        self.deleted.extend(self.full_paths_to_files(orig, cmp.left_only))

        all_added = self.full_paths_to_files(orig, cmp.right_only)
        added_dirs, added_files = self.split_dirs_and_files(all_added)
        requested_added = self.requested_files_from_dir(added_files)
        self.added.extend(requested_added)
        if len(added_dirs) > 0:
            self.add_files_in_new_dirs(added_dirs)

        changed_files = self.full_paths_to_files(orig, cmp.diff_files)
        requested_changed = self.requested_files_from_dir(changed_files)
        self.changed.extend(requested_changed)

        subdirs = [file.path for file in os.scandir(orig) if file.is_dir()]
        if self._first_iter:
            self._first_iter = False
            subdirs.remove(self._repository)
        for subdir in subdirs:
            repo_changed_dir = os.path.join(repo, os.path.basename(subdir))
            self.full_closure_compare(repo_changed_dir, subdir)

    def requested_files_from_dir(self, dir_files):
        if len(self._files) > 0:
            return list(set(dir_files) & set(self._files))
        else:
            return dir_files

    def full_paths_to_files(self, path, files):
        return list(map(lambda x: os.path.join(path, x), files))

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
            self.added.extend(requested_added)
            if len(new_dirs) > 0:
                self.add_files_in_new_dirs(new_dirs)


def is_dir_empty(path):
    return not os.listdir(path)


def check_repository(path):
    repository = os.path.join(path, "repository")
    if not does_dir_exist(repository):
        sys.exit("Repository is not initialized, "
                 "call 'init' in an empty folder to do it.")
    objects = does_dir_exist(os.path.join(repository, "objects"))
    index = (os.path.exists(os.path.join(repository, "index.bin")) and
             os.path.isfile(os.path.join(repository, "index.bin")))
    logs = (os.path.exists(os.path.join(repository, "logs.bin")) and
            os.path.isfile(os.path.join(repository, "logs.bin")))
    if not (objects and index and logs):
        sys.exit("Repository is damaged.")


def init(path):
    if not is_dir_empty(path):
        sys.exit("To initialize a repository choose an empty folder")
    os.mkdir(os.path.join(path, "repository"))
    os.mkdir(os.path.join(path, "repository", "objects"))
    os.mkdir(os.path.join(path, "repository", "last_state"))
    Path(os.path.join(path, "repository", "index.bin")).touch()
    Path(os.path.join(path, "repository", "logs.bin")).touch()
    print("Repository initialized")


def add(path, files_to_add):
    check_repository(path)
    print("Repository is OK, start comparing.")
    comparer = StatesComparer(path, files_to_add)
    comparer.compare()
    add_console_log(path, comparer)


def add_console_log(path, comparer):
    print("    Added files:")
    for file in comparer.added:
        print(os.path.relpath(file, path))
    print("    Deleted files:")
    for file in comparer.deleted:
        print(os.path.relpath(file, path))
    print("    Changed files:")
    for file in comparer.changed:
        print(os.path.relpath(file, path))


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
