from Commands.RepositoryInfo import RepositoryInfo
from pathlib import Path
import os


class RepoInit(RepositoryInfo):
    def init(self):
        os.mkdir(os.path.join(self.path, "repository"))
        os.mkdir(self.objects)
        os.mkdir(self.last_state)
        for file in self.repo_files:
            Path(file).touch()
        print("Repository initialized.")


def init(path):
    if not RepositoryInfo.is_dir_empty(path):
        print("To initialize a repository choose an empty folder")
        return
    repo = RepoInit(path)
    repo.init()