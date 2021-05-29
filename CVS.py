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
    update_last_state(path, dir_comparer)
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


def reset(path, tag):
    repo = RepositoryInfo(path)
    repo.check_repository()
    print("Repository is OK, start checking last commit.")
    print()
    relevant = is_last_state_relevant(path)
    if not relevant:
        sys.exit("Your folder has uncommitted changes, commit before restoring.")
    print("Last commit is relevant, start resetting.")
    print()
    tag_commit = repo.get_tag_commit(tag)
    resets_track = queue.Queue()
    get_resets_track(repo, resets_track, repo.head, tag_commit)

    while not resets_track.empty():
        step_commit = resets_track.get()
        commit_file = os.path.join(repo.objects, step_commit + ".dat")
        deltas_info = {}
        with open(commit_file, 'rb') as commit:
            while True:
                try:
                    deltas_info = pickle.load(commit)
                    go_to_previous_state(path, repo, deltas_info)
                except EOFError:
                    pass

    new_head_commit = CommitInfo()
    with open(repo.commits, 'rb') as f:
        commit_dict = pickle.load(f)
        new_head_commit = commit_dict[tag_commit]
    repo.rewrite_head(new_head_commit.commit)
    repo.rewrite_branch_head(new_head_commit.commit)
    print('Resetting finished.')


def update_last_state(path, comparer):
    repo_path = os.path.join(path, "repository", "last_state")
    delete_files(path, comparer.deleted)
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


def delete_files(path, to_delete):
    for file in to_delete:
        absolute_file = os.path.join(path, file)
        os.chmod(absolute_file, 0o777)
        if os.path.isdir(absolute_file):
            shutil.rmtree(absolute_file)
        else:
            os.remove(absolute_file)


def go_to_previous_state(path, deltas):
    delete_files(path, deltas.added)
    for file in deltas.deleted:
        content = deltas.deleted[file]
        absolute_file = os.path.join(path, file)
        file_dir_path = os.path.dirname(absolute_file)
        if not os.path.exists(file_dir_path):
            os.makedirs(file_dir_path)
        Path(absolute_file).touch()
        with open(absolute_file, 'w') as f:
            f.writelines(content)
    for file in deltas.changed:
        file_lines = ''
        with open(file, 'r') as f:
            file_lines = f.readlines()
        reset_lines = FilesComparer().previous_file_version(file_lines,
                                                            deltas.changed[file])
        with open(file, 'w') as f:
            f.writelines(reset_lines)


def get_resets_track(repo, track, current, final):
    if current == final:
        return
    track.put(current)
    prev_commit = repo.get_commit_info().prev_commit
    get_resets_track(repo, track, prev_commit, final)


def is_last_state_relevant(path, dir_comparer=None):
    if dir_comparer is None:
        dir_comparer = DirContentComparer(path)
        dir_comparer.compare()
    return len(dir_comparer.added) == 0 and \
           len(dir_comparer.changed) == 0 and \
           len(dir_comparer.deleted) == 0


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
    parser.add_argument("command", help="CVS command")
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
    if args.command == "init":
        init(args.path)
    if args.command == "add":
        add(args.path, args.files)
    if args.command == "commit":
        commit(args.path, args.tag, args.comment)
    if args.command == "reset":
        reset(args.path, args.tag)
    if args.command == "status":
        status(args.path)
    if args.command == "branch":
        branch(args.path, args.branchname)


if __name__ == '__main__':
    main()
