from Commands.RepositoryInfo import RepositoryInfo
import os
import pickle
import shutil
from pathlib import Path
from Comparers import DirContentComparer, Deltas


class AddRepo(RepositoryInfo):
    def is_last_state_relevant(self, dir_comparer=None):
        """Проверка совпадения состояния основной папки и last_state"""
        if dir_comparer is None:
            dir_comparer = DirContentComparer(self.path, self.ignore_patterns)
            dir_comparer.compare()
        return (len(dir_comparer.added) == 0 and
                len(dir_comparer.changed) == 0 and
                len(dir_comparer.deleted) == 0)

    def add_info(self, info):
        """Запись информации об изменениях в виде Deltas в файл index"""
        with open(self.index, 'ab') as index:
            pickle.dump(info, index)

    def update_last_state(self):
        """Копирование состояния основной папки в last_state"""
        comparer = DirContentComparer(self.path, self.ignore_patterns)
        comparer.compare()
        self._delete_files(self.last_state, comparer.deleted)
        for file in comparer.added:
            to_add = os.path.join(self.path, file)
            copy_path = os.path.join(self.last_state, file)
            copy_dir_path = os.path.dirname(copy_path)
            if not os.path.exists(copy_dir_path):
                os.makedirs(copy_dir_path)
            Path(copy_path).touch()
            shutil.copyfile(to_add, copy_path)
        for file in comparer.changed:
            changed = os.path.join(self.path, file)
            copy_path = os.path.join(self.last_state, file)
            shutil.copyfile(changed, copy_path)

    @staticmethod
    def _delete_files(path, to_delete):
        for file in to_delete:
            absolute_file = os.path.join(path, file)
            os.chmod(absolute_file, 0o777)
            if os.path.isdir(absolute_file):
                shutil.rmtree(absolute_file)
            else:
                os.remove(absolute_file)


def add(path):
    repo = AddRepo(path)
    repo.check_repository()
    print("Repository is OK, start comparing.")
    print()

    dir_comparer = DirContentComparer(path, repo.ignore_patterns)
    dir_comparer.compare()
    if repo.is_last_state_relevant(dir_comparer):
        print("Adding finished, no changes.")
        return

    dir_comparer.status_console_log()
    repo.add_info(Deltas(path, repo, dir_comparer))
    repo.update_last_state()
    print()
    print("Adding finished")
