from pathlib import Path
import argparse
import os
import sys
import pickle
import shutil
import queue
from Comparers import DirContentComparer, FilesComparer
from CommitInfo import CommitInfo


def is_dir_empty(path):
    return not os.listdir(path)

def does_dir_exist(path):
    return os.path.exists(path) and os.path.isdir(path)


def check_repository(path):
    repository = os.path.join(path, "repository")
    if not does_dir_exist(repository):
        sys.exit("Repository is not initialized, "
                 "call 'init' in an empty folder to do it.")
    objects = does_dir_exist(os.path.join(repository, "objects"))
    index = check_file(repository, "index.dat")
    tags = check_file(repository, "tags.dat")
    branches = check_file(repository, "branches.dat")
    commits = check_file(repository, "commits.dat")
    head = check_file(repository, "head.txt")
    logs = check_file(repository, "logs.txt")
    if not (objects and index and tags and branches and commits and head and logs):
        sys.exit("Repository is damaged.")

def check_file(repository, filename):
    return (os.path.exists(os.path.join(repository, filename)) and
             os.path.isfile(os.path.join(repository, filename)))


def init(path):
    if not is_dir_empty(path):
        sys.exit("To initialize a repository choose an empty folder")
    os.mkdir(os.path.join(path, "repository"))
    os.mkdir(os.path.join(path, "repository", "objects"))
    os.mkdir(os.path.join(path, "repository", "last_state"))
    Path(os.path.join(path, "repository", "index.dat")).touch()
    Path(os.path.join(path, "repository", "tags.dat")).touch()
    Path(os.path.join(path, "repository", "branches.dat")).touch()
    Path(os.path.join(path, "repository", "commits.dat")).touch()
    Path(os.path.join(path, "repository", "head.txt")).touch()
    Path(os.path.join(path, "repository", "logs.txt")).touch()
    print("Repository initialized")


def add(path, files_to_add):
    check_repository(path)
    print("Repository is OK, start comparing.")
    print()
    dir_comparer = DirContentComparer(path, files_to_add)
    dir_comparer.compare()
    add_console_log(path, dir_comparer)
    last_path = os.path.join(path, "repository", "last_state")
    filesToCompare = [[os.path.join(last_path, x),
                       os.path.join(path, x)] for x in dir_comparer.changed]
    files_comparer = FilesComparer(filesToCompare)
    diffs = files_comparer.compareFiles()
    deleted = deleted_content(dir_comparer.deleted)
    info = {"Added": dir_comparer.added, "Deleted": deleted, "Changed": diffs}
    index_file = os.path.join(path, "repository", "index.dat")
    with open(index_file, 'ab') as dump_out:
        pickle.dump(info, dump_out)
    update_last_state(path, dir_comparer)
    print()
    print("Adding finished")


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


def add_console_log(path, comparer):
    print("Added files:")
    log_paths(path, comparer.added)
    print("Deleted files:")
    log_paths(path, comparer.deleted)
    print("Changed files:")
    log_paths(path, comparer.changed)


def log_paths(path, to_log):
    if len(to_log) == 0:
        print("    No files")
    else:
        for file in to_log:
            print("   ", file)


def deleted_content(deleted_files):
    file_to_content = {}
    for file in deleted_files:
        with open(file, 'r') as f:
            file_to_content[file] = f.readlines()
    return file_to_content


def commit(path, tag=None, comment=None):
    check_repository(path)
    print("Repository is OK, start committing.")
    print()
    index_file = os.path.join(path, "repository", "index.dat")
    commits_file = os.path.join(path, "repository", "commits.dat")
    tags_file = os.path.join(path, "repository", "tags.dat")
    branches_file = os.path.join(path, "repository", "branches.dat")
    logs_file = os.path.join(path, "repository", "logs.txt")
    head_record = os.path.join(path, "repository", "head.txt")

    if tag is not None:
        with open(tags_file, 'rb') as tags:
            while True:
                try:
                    pair = pickle.load(tags)
                    if tag == pair[0]:
                        sys.exit("This tag is already used, you can't give it to new commit")
                except EOFError:
                    break

    commit_index = len(os.listdir(os.path.join(path, "repository", "objects")))
    commit_file = os.path.join(path, "repository", "objects", str(commit_index) + ".dat")
    shutil.copyfile(index_file, commit_file)
    with open(index_file, 'wb'):
        pass

    head = ''
    with open(head_record, 'r') as f:
        head = f.read()
    last_commit = None
    commits_dict = {}
    if head != '':
        with open(commits_file, 'rb') as commits:
            commits_dict = pickle.load(commits)
            last_commit = commits_dict[head]
    current_commit = CommitInfo()
    if last_commit is None:
        current_commit.set_init_commit(tag, comment, commit_index)
    else:
        current_commit.set_next_commit_in_branch(last_commit, tag, comment, commit_index)

    if tag is not None:
        with open(tags_file, 'ab') as tags:
            tag_pair = [tag, current_commit]
            pickle.dump(tag_pair, tags)

    commits_dict[str(commit_index)] = current_commit
    with open(commits_file, 'wb') as commits:
        pickle.dump(commits_dict, commits)

    with open(head_record, 'w') as head:
        head.write(str(commit_index))

    branches_dict = {}
    if last_commit is not None:
        with open(branches_file, 'rb') as branches:
            branches_dict = pickle.load(branches)
    branches_dict[current_commit.branch] = current_commit
    with open(branches_file, 'wb') as branches:
        pickle.dump(branches_dict, branches)

    current_commit.log_info_to_file(logs_file)
    print('Committing finished')


def reset(path, tag):
    check_repository(path)
    print("Repository is OK, start checking last commit.")
    print()
    relevant = is_last_commit_relevant(path)
    if not relevant:
        sys.exit("Your folder has uncommitted changes, commit before restoring.")
    print("Last commit is relevant, start resetting.")
    print()
    tag_commit_index = get_commit_info_by_tag(path, tag).commit_index
    head_record = os.path.join(path, "repository", "head.txt")
    head_index = ''
    with open(head_record, 'r') as f:
        head_index = f.read()
    resets_track = queue.Queue()
    get_resets_track(path, resets_track, head_index, tag_commit_index)
    resets_track.get()
    while not resets_track.empty():
        step_commit = resets_track.get()
        commit_file = os.path.join(path, "repository", "objects", step_commit + ".dat")
        deltas_info = None
        with open(commit_file, 'rb') as commit:
            deltas_info = pickle.load(commit)
        for file in deltas_info["Added"]:
            absolute_file = os.path.join(path, file)
            os.chmod(absolute_file, 0o777)
            if os.path.isdir(absolute_file):
                shutil.rmtree(absolute_file)
            else:
                os.remove(absolute_file)
        for file_info in deltas_info["Deleted"]:
            file = file_info[0]
            content = file_info[1]
            absolute_file = os.path.join(path, file)
            file_dir_path = os.path.dirname(absolute_file)
            if not os.path.exists(file_dir_path):
                os.makedirs(file_dir_path)
            Path(absolute_file).touch()
            with open(absolute_file, 'w') as f:
                f.writelines(content)
        for file in deltas_info["Changed"]:
            file_lines = ''
            with open(file, 'r') as f:
                file_lines = f.readlines()
            comparer = FilesComparer()
            reset_lines = comparer.previous_file_version(file_lines, deltas_info["Changed"][file])
            with open(file, 'w') as f:
                f.writelines(reset_lines)


def get_commit_info_by_tag(path, tag):
    tags_file = os.path.join(path, "repository", "tags.dat")
    with open(tags_file, 'rb') as tags:
        while True:
            try:
                pair = pickle.load(tags)
                if tag == pair[0]:
                    return pair[1]
            except EOFError:
                sys.exit("No commits with such tag")


def get_resets_track(path, track, current, final):
    track.put(current)
    if current == final:
        return
    commits_file = os.path.join(path, "repository", "commits.dat")
    commits_dict = {}
    with open(commits_file, 'rb') as commits:
        commits_dict = pickle.load(commits)
    cur_commit = commits_dict[current]
    get_resets_track(path, track, cur_commit.prev_commit_index, final)


def is_last_commit_relevant(path):
    dir_comparer = DirContentComparer(path)
    return len(dir_comparer.added) == 0 and \
           len(dir_comparer.changed) == 0 and \
           len(dir_comparer.deleted) == 0


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", help="CVS command")
    parser.add_argument("path", help="path to a folder with repository")
    parser.add_argument("files", nargs='*',
                        help="bunch of files to add (only for 'add' command)")
    parser.add_argument("-c", "--comment", help="comment for new commit")
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
    if args.command == "commit":
        commit(args.path, args.tag, args.comment)
    if args.command == "reset":
        reset(args.path, args.tag)


if __name__ == '__main__':
    main()
