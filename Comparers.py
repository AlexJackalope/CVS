import copy
import os
import filecmp
import difflib
import re


class DirContentComparer:
    def __init__(self, path):
        self._root = path
        self._repository = os.path.join(self._root, "repository")
        self._last_state = os.path.join(self._repository, "last_state")
        self._first_iter = True
        self._files = None
        self.added = []
        self.deleted = []
        self.changed = []

    def compare(self, files=None):
        if files is not None and len(files) > 0:
            self._files = self.full_paths_to_files(self._root, files)
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
        if self._files is not None:
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
    def __init__(self, file_pairs=None):
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
        diff = difflib.unified_diff(file1, file2, n=0)
        diff_str = [x for x in diff]
        self.deltas[name] = diff_str

    @staticmethod
    def previous_file_version(str_file2, deltas):
        """
        По дельте и файлу последующей версии возвращает предыдущую версию файла
        """
        new_file = copy.deepcopy(str_file2)
        count_rem_str = 0
        for i in range(2, len(deltas)):
            if re.match(r'@@', deltas[i]) is None:
                continue
            add_str = re.search(r'@@ -([,\d]+) \+([,\d]+) @@', deltas[i])[2].split(',')
            add_start_index = int(add_str[0])
            add_count = 1 if len(add_str) == 1 else int(add_str[1])
            for k in range(add_start_index, add_start_index + add_count):
                new_file.pop(k - count_rem_str - 1)
                count_rem_str += 1
        for i in range(2, len(deltas)):
            if re.match(r'@@', deltas[i]) is None:
                continue
            rem_str = re.search(r'@@ -([,\d]+) \+([,\d]+) @@', deltas[i])[1].split(',')
            rem_start_index = int(rem_str[0])
            rem_count = 1 if len(rem_str) == 1 else int(rem_str[1])
            for k in range(rem_start_index, rem_start_index + rem_count):
                new_file.insert(k - 1, deltas[i + k - rem_start_index + 1][1:])
        return new_file

    @staticmethod
    def next_file_version(str_file_1, deltas):
        """
        По дельте и файлу предыдущей версии возвращает последующую версию файла
        """
        new_file = copy.deepcopy(str_file_1)
        count_rem_str = 0
        for i in range(2, len(deltas)):
            if re.match(r'@@', deltas[i]) is None:
                continue
            rem_str = re.search(r'@@ -([,\d]+) \+([,\d]+) @@', deltas[i])[1].split(',')
            rem_start_index = int(rem_str[0])
            rem_count = 1 if len(rem_str) == 1 else int(rem_str[1])
            for k in range(rem_start_index, rem_start_index + rem_count):
                new_file.pop(k - count_rem_str - 1)
                count_rem_str += 1
        for i in range(2, len(deltas)):
            if re.match(r'@@', deltas[i]) is None:
                continue
            rem_str = re.search(r'@@ -([,\d]+) \+([,\d]+) @@', deltas[i])[1].split(',')
            rem_count = 1 if len(rem_str) == 1 else int(rem_str[1])
            add_str = re.search(r'@@ -([,\d]+) \+([,\d]+) @@', deltas[i])[2].split(',')
            add_start_index = int(add_str[0])
            add_count = 1 if len(add_str) == 1 else int(add_str[1])
            for k in range(add_start_index, add_start_index + add_count):
                new_file.insert(k - 1, deltas[rem_count + i + k - add_start_index + 1][1:])
        return new_file