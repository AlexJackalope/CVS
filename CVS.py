from pathlib import Path
import argparse
import os
import sys
import pickle
import shutil
import queue
from CommitInfo import CommitInfo
from Comparers import DirContentComparer, FilesComparer, Deltas
from RepositoryInfo import RepositoryInfo


def is_dir_empty(path):
    return not os.listdir(path)


def init(path):
    if not is_dir_empty(path):
        sys.exit("To initialize a repository choose an empty folder")
    repo = RepositoryInfo(path)
    os.mkdir(os.path.join(path, "repository"))
    os.mkdir(repo.objects)
    os.mkdir(repo.last_state)
    for file in repo.repo_files:
        Path(file).touch()
    print("Repository initialized.")


def add(path):
    repo = RepositoryInfo(path)
    repo.check_repository()
    print("Repository is OK, start comparing.")
    print()

    dir_comparer = DirContentComparer(path)
    dir_comparer.compare()
    if is_last_state_relevant(path, dir_comparer):
        print("Adding finished, no changes.")
        return

    status_console_log(path, dir_comparer)
    info = Deltas(path, repo, dir_comparer)
    with open(repo.index, 'ab') as index:
        pickle.dump(info, index)
    update_last_state(path, repo)
    print()
    print("Adding finished")


def commit(path, tag=None, comment=None):
    repo = RepositoryInfo(path)
    commit_checks(path, repo, tag)

    commit_index = str(len(os.listdir(repo.objects)))
    commit_file = os.path.join(repo.objects, commit_index + ".dat")
    shutil.copyfile(repo.index, commit_file)
    repo.clear_index()
    repo.set_new_commit(commit_index)

    if tag is not None:
        repo.add_tag(tag, commit_index)

    log_commit(repo, commit_index, tag, comment)
    if tag is not None:
        print(f'Commited with tag: {tag}.')
    if comment is not None:
        print(f'Comment: {comment}.')
    print('Committing finished.')


def commit_checks(path, repo, tag):
    """
    Осуществляет проверки до создания коммита,
    выход из программы, если коммит невозможен.
    """
    repo.check_repository()

    if os.path.getsize(repo.index) == 0:
        if not is_last_state_relevant(path):
            sys.exit("Add changes before committing.")
        else:
            sys.exit("Nothing to commit.")

    if tag is not None:
        if repo.is_tag_in_repo_tree(tag):
            sys.exit("This tag is already used, "
                     "you can't give it to new commit.")

    if not repo.is_current_branch_free():
        sys.exit("This commit already has next one. "
                 "Create a branch to add.")

    print("Repository is OK, start committing.")
    print()


def log_commit(repo, commit, tag, comment):
    with open(repo.logs, 'a') as logs:
        logs.write(f"Commit {commit}\n")
        if tag is not None:
            logs.write(f"Tag: {tag}\n")
        if comment is not None:
            logs.write(f"Comment: {comment}\n")
        logs.write('\n')


def reset(path, tag=None, steps_back=None):
    repo = RepositoryInfo(path)
    checks_before_switching(path, repo)

    resets_track = queue.Queue()
    if tag is not None:
        tag_commit = repo.get_tag_commit(tag)
        get_resets_track_by_tag(repo, resets_track, repo.head, tag_commit)
    elif steps_back is not None:
        get_switch_back_track_by_steps(repo, resets_track, repo.head,
                                       int(steps_back))
    else:
        sys.exit("Put a tag or an amount of steps to reset")

    new_head_commit = go_through_commits_return_current(path, repo,
                                                        resets_track, True)
    repo.rewrite_head(new_head_commit)
    repo.cut_branch_after_head()
    update_last_state(path, repo)
    log_reset(repo, tag, steps_back)
    print('Resetting finished.')


def update_last_state(path, repo):
    """Копирование состояния основной папки в last_state"""
    comparer = DirContentComparer(path)
    comparer.compare()
    delete_files(repo.last_state, comparer.deleted)
    for file in comparer.added:
        to_add = os.path.join(path, file)
        copy_path = os.path.join(repo.last_state, file)
        copy_dir_path = os.path.dirname(copy_path)
        if not os.path.exists(copy_dir_path):
            os.makedirs(copy_dir_path)
        Path(copy_path).touch()
        shutil.copyfile(to_add, copy_path)
    for file in comparer.changed:
        changed = os.path.join(path, file)
        copy_path = os.path.join(repo.last_state, file)
        shutil.copyfile(changed, copy_path)


def log_reset(repo, tag, steps):
    with open(repo.logs, 'a') as logs:
        logs.write(f"Reset on commit {commit}\n")
        if tag is not None:
            logs.write(f"With tag {tag}\n")
        if steps is not None:
            logs.write(f"{str(steps)} steps back\n")
        logs.write("\n")


def delete_files(path, to_delete):
    for file in to_delete:
        absolute_file = os.path.join(path, file)
        os.chmod(absolute_file, 0o777)
        if os.path.isdir(absolute_file):
            shutil.rmtree(absolute_file)
        else:
            os.remove(absolute_file)


def add_files(path, file_to_content):
    """Добавление файлов в папку и их заполнение соответствующим содержимым"""
    for file in file_to_content:
        content = file_to_content[file]
        absolute_file = os.path.join(path, file)
        file_dir_path = os.path.dirname(absolute_file)
        if not os.path.exists(file_dir_path):
            os.makedirs(file_dir_path)
        Path(absolute_file).touch()
        with open(absolute_file, 'w') as f:
            f.writelines(content)


def go_to_previous_state(path, deltas):
    """Откат состояния папки на один коммит назад"""
    delete_files(path, deltas.added.keys())
    add_files(path, deltas.deleted)
    for file in deltas.changed:
        file_lines = ''
        with open(file, 'r') as f:
            file_lines = f.readlines()
        prev_lines = FilesComparer().previous_file_version(
            file_lines, deltas.changed[file])
        with open(file, 'w') as f:
            f.writelines(prev_lines)


def go_to_next_state(path, deltas):
    """Переход состояния папки на один коммит вперёд"""
    delete_files(path, deltas.deleted.keys())
    add_files(path, deltas.added)
    for file in deltas.changed:
        file_lines = ''
        with open(file, 'r') as f:
            file_lines = f.readlines()
        next_lines = FilesComparer().next_file_version(file_lines,
                                                       deltas.changed[file])
        with open(file, 'w') as f:
            f.writelines(next_lines)


def get_resets_track_by_tag(repo, track, current, final):
    """
    Добавляет в очередь коммиты, которые нужно пройти
    назад по ветке до коммита с заданным тэгом.
    """
    if current == final:
        return
    track.put(current)
    prev_commit = repo.get_commit_info(current).prev_commit
    get_resets_track_by_tag(repo, track, prev_commit, final)


def get_switch_back_track_by_steps(repo, track, current, steps):
    if steps == 0:
        return
    if steps > 0 and current is None:
        sys.exit("You put a greater number than the commits amount.\n"
                 "Rollback is impossible.")
    track.put(current)
    prev_commit = repo.get_commit_info(current).prev_commit
    get_switch_back_track_by_steps(repo, track, prev_commit, steps - 1)


def get_switch_forward_track_by_steps(repo, track, current, branch, steps):
    if steps == 0:
        return
    commit_info = repo.get_commit_info(current)
    if commit_info.branch == branch:
        next_commit = commit_info.next_on_branch
    else:
        next_commit = commit_info.branches_next[branch]
    if steps > 0 and next_commit is None:
        sys.exit("You put a greater number than the commits amount.\n"
                 "Switching is impossible.")
    track.put(next_commit)
    get_switch_forward_track_by_steps(repo, track, next_commit,
                                      branch, steps - 1)


def is_last_state_relevant(path, dir_comparer=None):
    """Проверка совпадения состояния основной папки и last_state"""
    if dir_comparer is None:
        dir_comparer = DirContentComparer(path)
        dir_comparer.compare()
    return (len(dir_comparer.added) == 0 and
            len(dir_comparer.changed) == 0 and
            len(dir_comparer.deleted) == 0)


def switch(path, tag=None, steps_back=None, steps_forward=None):
    repo = RepositoryInfo(path)
    checks_before_switching(path, repo)
    switching_track = queue.Queue()
    if tag is None:
        is_back = True
        if steps_back is not None:
            get_switch_back_track_by_steps(repo, switching_track,
                                           repo.head, int(steps_back))

        elif steps_forward is not None:
            branch = repo.get_head_commit_info().branch
            get_switch_forward_track_by_steps(repo, switching_track, repo.head,
                                              branch, int(steps_forward))
            is_back = False
        else:
            sys.exit("Put a tag or an amount of steps to switch")
        new_head = go_through_commits_return_current(path, repo,
                                                     switching_track, is_back)
    else:
        tagged_commit = repo.get_tag_commit(tag)
        if tagged_commit is None:
            sys.exit("Commit with this tag does not exist")

        tagged_info = repo.get_commit_info(tagged_commit)
        head_info = repo.get_head_commit_info()

        if head_info.branch in tagged_info.all_commit_branches() or \
                tagged_info.branch in head_info.all_commit_branches():
            switching_track, is_back = get_path_on_branch(repo,
                                                          head_info.branch,
                                                          head_info.commit,
                                                          tagged_info)
            new_head = go_through_commits_return_current(path, repo,
                                                         switching_track,
                                                         is_back)
        else:
            new_head = switch_between_branches(path, repo,
                                               head_info, tagged_info)
    repo.rewrite_head(new_head)
    update_last_state(path, repo)
    print('Switching finished.')


def log_switching(repo):
    with open(repo.logs, 'a') as logs:
        logs.write(f"Switch on commit {commit}\n")
        logs.write('\n')


def checks_before_switching(path, repo):
    """Проверки на целостность репозитория и актуальность последнего коммита"""
    repo.check_repository()
    print("Repository is OK, start checking last commit.")
    print()

    relevant = is_last_state_relevant(path)
    if (not relevant) or os.path.getsize(repo.index) > 0:
        sys.exit("Your folder has uncommitted changes, "
                 "commit them before switching state.")
    print("Last commit is relevant.")
    print()


def go_through_commits_return_current(path, repo, commits_track, is_back):
    """
    Переход состояния папки вперёд или назад по истории коммитов
    внутри ветки
    """
    step_commit = None
    while not commits_track.empty():
        step_commit = commits_track.get()
        commit_file = os.path.join(repo.objects, step_commit + ".dat")
        with open(commit_file, 'rb') as commit:
            while True:
                try:
                    deltas_info = pickle.load(commit)
                    if is_back:
                        go_to_previous_state(path, deltas_info)
                    else:
                        go_to_next_state(path, deltas_info)
                except EOFError:
                    break
    if is_back:
        info = repo.get_commit_info(step_commit)
        return info.prev_commit
    else:
        return step_commit


def switch_between_branches(path, repo, head_info, finish_commit_info):
    """
    Совершает переход к заданному коммиту, находящемуся на другой ветке,
    возвращает коммит, ставший головным.
    """
    paths = get_paths_through_branches(repo, head_info.commit,
                                       finish_commit_info)
    for path_pair in paths:
        switching_track = path_pair[0]
        is_back = path_pair[1]
        new_head = go_through_commits_return_current(path, repo,
                                                     switching_track, is_back)
    return new_head


def get_path_on_branch(repo, branch, start_commit, finish_commit_info):
    """
    Возвращает две переменных: путь-очередь коммитов
    и флаг движения изменений назад по истории.
    """
    commits_to_check = queue.Queue()
    finish = CommitInfo()
    finish.commit = finish_commit_info.commit
    back = prev_on_branch(finish_commit_info.prev_commit, finish)
    next = next_on_branch(finish_commit_info.get_next_commit_on_branch(branch),
                          finish)
    commits_to_check.put(back)
    commits_to_check.put(next)
    while not commits_to_check.empty():
        checking = commits_to_check.get()
        if checking.commit is not None:
            if checking.commit == start_commit:
                return get_commits_track_and_head_by_linked(checking)
            checking_info = repo.get_commit_info(checking.commit)
            if checking.next_on_branch is None:
                next = next_on_branch(checking_info.get_next_commit_on_branch(
                    branch), checking)
                commits_to_check.put(next)
            else:
                back = prev_on_branch(checking_info.prev_commit, checking)
                commits_to_check.put(back)


class PathStep:
    def __init__(self, prev_step, commit, moving_back=None):
        self.prev_step = prev_step
        self.commit = commit
        self.is_back = moving_back


def get_paths_through_branches(repo, start_commit, finish_commit_info):
    """
    Возвращает список пар:
    1. Путь от коммита до коммита между разветвлениями;
    2. Флаг движения назад по истории.
    """
    commits_to_check = queue.Queue()
    finish_step = PathStep(None, finish_commit_info.commit)
    add_nearest_commits_to_queue(commits_to_check, finish_step,
                                 finish_commit_info)
    while not commits_to_check.empty():
        checking = commits_to_check.get()
        if checking.commit == start_commit:
            return get_paths_by_link(checking)
        checking_info = repo.get_commit_info(checking.commit)
        add_nearest_commits_to_queue(commits_to_check, checking, checking_info)


def add_nearest_commits_to_queue(queue, step, commit_info):
    if step.prev_step is None or \
            (commit_info.prev_commit is not None and
             commit_info.prev_commit != step.prev_step.commit):
        back_step = PathStep(step, commit_info.prev_commit, False)
        if back_step is not None:
            queue.put(back_step)
    for next_commit in commit_info.get_all_next_commits():
        if step.prev_step is None or\
                next_commit != step.prev_step.commit:
            next_step = PathStep(step, next_commit, True)
            queue.put(next_step)


def get_paths_by_link(path_step):
    """
    По односвязному списку шагов возвращает список путей
    с соответствующим им направлениям.
    """
    paths = []
    path_queue = queue.Queue()
    is_back = path_step.is_back
    while path_step is not None:
        if path_step.is_back != is_back and path_step.is_back is not None:
            paths.append([path_queue, is_back])
            path_queue = queue.Queue()
            is_back = path_step.is_back
        path_queue.put(path_step.commit)
        path_step = path_step.prev_step
    paths.append([path_queue, is_back])
    return paths


def prev_on_branch(prev_commit, current):
    prev = CommitInfo()
    prev.commit = prev_commit
    prev.next_on_branch = current
    return prev


def next_on_branch(next_commit, current):
    next = CommitInfo()
    next.commit = next_commit
    next.prev_commit = current
    return next


def get_commits_track_and_head_by_linked(commit_info):
    """
    По односвязному списку от элемента commit_info
    возвращает очередь-путь и направление движения по истории коммитов.
    """
    track = queue.Queue()
    is_back = True
    if commit_info.next_on_branch is None:
        while commit_info.prev_commit is not None:
            track.put(commit_info.commit)
            commit_info = commit_info.prev_commit
    else:
        is_back = False
        commit_info = commit_info.next_on_branch
        while commit_info.next_on_branch is not None:
            track.put(commit_info.commit)
            commit_info = commit_info.next_on_branch
        track.put(commit_info.commit)
    return track, is_back


def status(path):
    repo = RepositoryInfo(path)
    repo.check_repository()
    dir_comparer = DirContentComparer(path)
    dir_comparer.compare()
    no_changes = is_last_state_relevant(path, dir_comparer)
    if no_changes:
        if os.path.getsize(repo.index) == 0:
            print("Current state of folder is saved.\n"
                  "Nothing to add, nothing to commit.")
        else:
            print("All tracked changes are added, commit them.")
    else:
        status_console_log(path, dir_comparer)


def status_console_log(path, comparer):
    print("Added files:")
    log_paths(path, comparer.added)
    print("Deleted files:")
    log_paths(path, comparer.deleted)
    print("Changed files:")
    log_paths(path, comparer.changed)


def log_paths(path, to_log):
    if len(to_log) == 0:
        print("\tNo files")
    else:
        for file in to_log:
            print("\t" + file)


def branch(path, branch_name=None):
    repo = RepositoryInfo(path)
    repo.check_repository()
    if branch_name is None:
        console_log_branches(repo)
    else:
        repo.add_branch(branch_name)
        print('Branch added')


def checkout(path, branch_name):
    repo = RepositoryInfo(path)
    repo.check_repository()
    if branch_name is None:
        sys.exit("Put a name of branch to checkout.")
    branch_head = repo.get_branch_head_commit(branch_name)
    if branch_head is None:
        sys.exit("No such branch. Call 'branch' to see repository's branches.")
    head_info = repo.get_head_commit_info()
    if head_info.branch == branch_name:
        print("You are on branch. Switching to branch head commit.")
    branch_head_info = repo.get_commit_info(branch_head)
    new_head = switch_between_branches(path, repo, head_info, branch_head_info)
    repo.rewrite_head(new_head)
    update_last_state(path, repo)
    log_checkout(repo, branch_name)
    print("Branch switching finished.")


def log_checkout(repo, branch):
    with open(repo.logs, 'a') as logs:
        logs.write(f"Switch on branch {branch}\n")
        logs.write('\n')


def console_log_branches(repo):
    current_branch = ''
    print("Branches:")
    with open(repo.branches, 'rb') as branches:
        branches_dict = pickle.load(branches)
        for branch in branches_dict:
            print("\t"+branch)
            if branches_dict[branch] == repo.head:
                current_branch = branch
    print("Current branch:", current_branch)


def log(path):
    repo = RepositoryInfo(path)
    repo.check_repository()
    with open(repo.logs, 'r') as logsfile:
        logs = logsfile.read()
    print(logs)
    print('Logs printing finished.')


def clearlog(path):
    repo = RepositoryInfo(path)
    repo.check_repository()
    with open(repo.logs, 'w'):
        pass
    print('Logs cleared.')


def parse_args():
    parser = argparse.ArgumentParser(
        description="CVS version control system.\n"
                    "Commands:\n"
                    "* init - initializes a repository in an empty folder\n"
                    "* add - checks folder changes\n"
                    "* commit - saves added changes\n"
                    "\ttag on key -t - tag to turn to the commit\n"
                    "\tcomment on key -c - just your comment\n"
                    "* reset - returns to a commit on branch and "
                    "cut all next commits. Two ways to call:\n"
                    "\twith tag on key -t\n"
                    "\twith amount of steps back\n"
                    "* switch - changes a current state with commit, "
                    "commits tree won't change.\n"
                    "\tswitching on commit with tag\n"
                    "\tswitching on branch: +n - n steps forward, "
                    "-n - n steps back\n"
                    "* status - current state of repository: "
                    "information about uncommitted changes\n"
                    "* branch"
                    "\twithout keys shows list of branches and current\n"
                    "\twith key -b adds a branch\n"
                    "* checkout - turns to a head commit of branch on key -b\n"
                    "* log - prints information about commit changes\n"
                    "* clearlog - deletes information about commit changes\n",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("command", nargs='+', help="CVS command")
    parser.add_argument("path", help="path to a folder with repository")
    parser.add_argument("-b", "--branchname", help="name of branch "
                                                   "to create/checkout")
    parser.add_argument("-c", "--comment", help="comment for new commit")
    parser.add_argument("-t", "--tag", help="tag of the commit")
    return parser.parse_args()


def main():
    args = parse_args()
    if not RepositoryInfo.does_dir_exist(args.path):
        sys.exit("Given directory does not exist")
    elif args.command[0] == "init":
        init(args.path)
    elif args.command[0] == "add":
        add(args.path)
    elif args.command[0] == "commit":
        commit(args.path, args.tag, args.comment)
    elif args.command[0] == "reset":
        if len(args.command) == 2:
            reset(args.path, steps_back=args.command[1])
        else:
            reset(args.path, tag=args.tag)
    elif args.command[0] == "switch":
        if len(args.command) == 2:
            sign = args.command[1][0]
            if sign == '-':
                switch(args.path, steps_back=args.command[1][1:])
            if sign == '+':
                switch(args.path, steps_forward=args.command[1][1:])
        else:
            switch(args.path, tag=args.tag)
    elif args.command[0] == "status":
        status(args.path)
    elif args.command[0] == "branch":
        branch(args.path, args.branchname)
    elif args.command[0] == "checkout":
        checkout(args.path, args.branchname)
    elif args.command[0] == "log":
        log(args.path)
    elif args.command[0] == "clearlog":
        clearlog(args.path)
    else:
        sys.exit("Incorrect input. Call -h or --help to read manual.")


if __name__ == '__main__':
    main()
