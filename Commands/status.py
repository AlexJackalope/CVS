from .add import AddRepo
import os
from Comparers import DirContentComparer


def status(args):
    repo = AddRepo(args.path)
    try:
        repo.check_repository()
    except repo.RepositoryCheckingException as e:
        print(e)
        return
    dir_comparer = DirContentComparer(args.path, repo.ignore_patterns)
    dir_comparer.compare()
    no_changes = repo.is_last_state_relevant(args.path, repo, dir_comparer)
    if no_changes:
        if os.path.getsize(repo.index) == 0:
            print("Current state of folder is saved.\n"
                  "Nothing to add, nothing to commit.")
        else:
            print("All tracked changes are added, commit them.")
    else:
        status_console_log(args.path, dir_comparer)


def status_console_log(path, comparer):
    print("Added files:")
    log_paths(path, comparer.added)
    print("Deleted files:")
    log_paths(path, comparer.deleted)
    print("Changed files:")
    log_paths(path, comparer.changed)


def log_paths(to_log):
    if len(to_log) == 0:
        print("\tNo files")
    else:
        for file in to_log:
            print("\t" + file)
