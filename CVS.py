from pathlib import Path
import argparse
import os, sys
import pickle
import shutil
import queue
from Comparers import DirContentComparer, FilesComparer
from CommitInfo import CommitInfo
from RepositoryInfo import RepositoryInfo, Deltas


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
    print("Repository initialized")


def add(path, files_to_add):
    repo = RepositoryInfo(path)
    repo.check_repository()
    print("Repository is OK, start comparing.")
    print()

    dir_comparer = DirContentComparer(path)
    dir_comparer.compare(files_to_add)
    if is_last_state_relevant(path, dir_comparer):
        print("Adding finished, no changes")
        return

    status_console_log(path, dir_comparer)
    filesToCompare = [[os.path.join(repo.last_state, x),
                       os.path.join(path, x)] for x in dir_comparer.changed]
    files_comparer = FilesComparer(filesToCompare)

    diffs = files_comparer.compareFiles()
    deleted = file_to_content(repo.last_state, dir_comparer.deleted)
    added = file_to_content(path, dir_comparer.added)
    info = Deltas(added, diffs, deleted)

    with open(repo.index, 'ab') as index:
        pickle.dump(info, index)
    update_last_state(path, repo, dir_comparer)
    print()
    print("Adding finished")


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


def file_to_content(path, deleted_files):
    file_to_content = {}
    for file in deleted_files:
        abs_path = os.path.join(path, file)
        os.chmod(abs_path, 0o777)
        with open(abs_path, 'r') as f:
            file_to_content[file] = f.readlines()
    return file_to_content


def commit(path, tag=None, comment=None):
    repo = RepositoryInfo(path)
    repo.check_repository()
    if os.path.getsize(repo.index) == 0:
        if not is_last_state_relevant(path):
            sys.exit("Add changes before committing")
        else:
            sys.exit("Nothing to commit")
    print("Repository is OK, start committing.")
    print()

    if tag is not None:
        if repo.is_tag_in_repo_tree(tag):
            sys.exit("This tag is already used, you can't give it to new commit")

    commit_index = str(len(os.listdir(repo.objects)))
    commit_file = os.path.join(repo.objects, commit_index + ".dat")
    shutil.copyfile(repo.index, commit_file)
    repo.clear_index()

    previous_commit = repo.get_head_commit_info()
    current_commit = CommitInfo()
    if previous_commit is None:
        current_commit.set_init_commit(commit_index)
    else:
        current_commit.set_next_commit_on_branch(previous_commit, commit_index)

    if tag is not None:
        repo.add_tag(tag, commit_index)
    repo.add_commit_info(current_commit)
    repo.rewrite_head(commit_index)
    repo.rewrite_branch_head(current_commit)

    log_commit(repo, commit_index, tag, comment)
    if tag is not None:
        print('Commited with tag:', tag)
    if comment is not None:
        print('Comment:', comment)
    print('Committing finished')


def log_commit(repo, commit, tag, comment):
    with open(repo.logs, 'a') as logs:
        logs.write("Commit")
        if tag is not None:
            logs.write("Tag: " + tag)
        if comment is not None:
            logs.write("Comment: " + comment)
        logs.write(commit)
        logs.write('\n')


def reset(path, tag=None, steps_back=None):
    repo = RepositoryInfo(path)
    checks_before_switching(path, repo)

    resets_track = queue.Queue()
    if tag is not None:
        tag_commit = repo.get_tag_commit(tag)
        get_resets_track_by_tag(repo, resets_track, repo.head, tag_commit)
    elif steps_back is not None:
        get_resets_track_by_steps(repo, resets_track, repo.head, int(steps_back), True)
    else:
        sys.exit("Put a tag or an amount of steps to reset")

    new_head_commit = go_through_commits_return_current(path, repo, resets_track, True)
    repo.rewrite_head(new_head_commit)
    head_info = repo.get_commit_info(new_head_commit)
    repo.rewrite_branch_head(head_info)
    print('Resetting finished.')


def checks_before_switching(path, repo):
    repo.check_repository()
    print("Repository is OK, start checking last commit.")
    print()

    relevant = is_last_state_relevant(path)
    if (not relevant) or os.path.getsize(repo.index) > 0:
        sys.exit("Your folder has uncommitted changes, commit them before switching state.")
    print("Last commit is relevant.")
    print()


def go_through_commits_return_current(path, repo, commits_track, is_back):
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


def update_last_state(path, repo, comparer):
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


def delete_files(path, to_delete):
    for file in to_delete:
        absolute_file = os.path.join(path, file)
        os.chmod(absolute_file, 0o777)
        if os.path.isdir(absolute_file):
            shutil.rmtree(absolute_file)
        else:
            os.remove(absolute_file)


def add_files(path, file_to_content):
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
    delete_files(path, deltas.added.keys())
    add_files(path, deltas.deleted)
    for file in deltas.changed:
        file_lines = ''
        with open(file, 'r') as f:
            file_lines = f.readlines()
        prev_lines = FilesComparer().previous_file_version(file_lines,
                                                            deltas.changed[file])
        with open(file, 'w') as f:
            f.writelines(prev_lines)


def go_to_next_state(path, deltas):
    delete_files(path, deltas.deleted.keys())
    add_files(path, deltas.added)
    for file in deltas.changed:
        file_lines = ''
        with open(file, 'r') as f:
            file_lines = f.readlines()
        next_lines = FilesComparer().next_file_version(file_lines, deltas.changed[file])
        with open(file, 'w') as f:
            f.writelines(next_lines)


def get_resets_track_by_tag(repo, track, current, final):
    if current == final:
        return
    track.put(current)
    prev_commit = repo.get_commit_info(current).prev_commit
    get_resets_track_by_tag(repo, track, prev_commit, final)


def get_resets_track_by_steps(repo, track, current, steps, is_backward):
    if steps == 0:
        return
    if steps > 0 and current is None:
        sys.exit("You put a greater number than the commits amount.\nRollback is impossible.")
    track.put(current)
    if is_backward:
        prev_commit = repo.get_commit_info(current).prev_commit
        get_resets_track_by_steps(repo, track, prev_commit, steps - 1)
    else:
        next_commit = repo.get_commit_info(current).next_on_branch
        get_resets_track_by_steps(repo, track, next_commit, steps - 1)


def is_last_state_relevant(path, dir_comparer=None):
    if dir_comparer is None:
        dir_comparer = DirContentComparer(path)
        dir_comparer.compare()
    return len(dir_comparer.added) == 0 and \
           len(dir_comparer.changed) == 0 and \
           len(dir_comparer.deleted) == 0


def switch(path, tag=None, steps_back=None, steps_forward=None):
    repo = RepositoryInfo(path)
    checks_before_switching(path, repo)
    switching_track = queue.Queue()
    if tag is None:
        head = None
        if steps_back is not None:
            get_resets_track_by_steps(repo, switching_track, repo.head, int(steps_back), True)
            head = go_through_commits_return_current(path, repo, switching_track, True)
        elif steps_forward is not None:
            get_resets_track_by_steps(repo, switching_track, repo.head, int(steps_forward), False)
            head = go_through_commits_return_current(path, repo, switching_track, False)
        else:
            sys.exit("Put a tag or an amount of steps to switch")
        repo.rewrite_head(head)
        head_info = repo.get_commit_info(head)
        repo.rewrite_branch_head(head_info)
        print('Switching finished.')
    elif tag is not None:
        pass


def status(path):
    repo = RepositoryInfo(path)
    repo.check_repository()
    dir_comparer = DirContentComparer(path)
    dir_comparer.compare()
    no_changes = is_last_state_relevant(path, dir_comparer)
    if no_changes:
        if os.path.getsize(repo.index) == 0:
            print("Current state of folder is saved.\nNothing to add, nothing to commit.")
        else:
            print("All tracked changes are added, commit them.")
    else:
        status_console_log(path, dir_comparer)


def branch(path, branch_name=None):
    repo = RepositoryInfo(path)
    repo.check_repository()
    if branch_name is None:
        log_branches(repo)
    else:
        repo.add_branch(branch_name)
        print('Branch added')


def log_branches(repo):
    current_branch = ''
    print("Branches:")
    with open(repo.branches, 'rb') as branches:
        branches_dict = pickle.load(branches)
        for branch in branches_dict:
            print("\t"+branch)
            if branches_dict[branch] == repo.head:
                current_branch = branch
    print("Current branch:", current_branch)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs='+', help="CVS command")
    parser.add_argument("path", help="path to a folder with repository")
    parser.add_argument("files", nargs='*',
                        help="bunch of files to add (only for 'add' command)")
    parser.add_argument("-b", "--branchname", help="name of branch to create/checkout")
    parser.add_argument("-c", "--comment", help="comment for new commit")
    parser.add_argument("-t", "--tag", help="tag of the commit")
    return parser.parse_args()


def main():
    args = parse_args()
    if not RepositoryInfo.does_dir_exist(args.path):
        sys.exit("Given directory does not exist")
    if args.command[0] == "init":
        init(args.path)
    if args.command[0] == "add":
        add(args.path, args.files)
    if args.command[0] == "commit":
        commit(args.path, args.tag, args.comment)
    if args.command[0] == "reset":
        if len(args.command) == 2:
            reset(args.path, steps_back=args.command[1])
        else:
            reset(args.path, tag=args.tag)
    if args.command[0] == "switch":
        if len(args.command) == 2:
            sign = args.command[1][0]
            if sign == '-':
                switch(args.path, steps_back=args.command[1][1:])
            if sign == '+':
                switch(args.path, steps_forward=args.command[1][1:])
        else:
            switch(args.path, tag=args.tag)
    if args.command[0] == "status":
        status(args.path)
    if args.command[0] == "branch":
        branch(args.path, args.branchname)
    if args.command[0] == "checkout":
        pass
    sys.exit("Incorrect input. Call -h or --help to read manual.")


if __name__ == '__main__':
    main()
