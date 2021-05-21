import os
import filecmp
import difflib

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