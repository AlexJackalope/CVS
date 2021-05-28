from pathlib import Path
import argparse
import os, sys
import pickle
import shutil
import queue
from Comparers import DirContentComparer, FilesComparer
from CommitInfo import CommitInfo


class RepositoryInfo:
    def __init__(self, path):
        self.path = path
        self.last_state = os.path.join(path, "repository", "last_state")
        self.objects = os.path.join(path, "repository", "objects")
        self.branches = os.path.join(path, "repository", "branches.dat")
        self.commits = os.path.join(path, "repository", "commits.dat")
        self.head = os.path.join(path, "repository", "head.txt")
        self.index = os.path.join(path, "repository", "index.dat")
        self.logs = os.path.join(path, "repository", "logs.txt")
        self.tags = os.path.join(path, "repository", "tags.dat")
        self.repo_files = [self.branches, self.commits, self.head, self.index, self.logs, self.tags]

    @staticmethod
    def does_dir_exist(path):
        return os.path.exists(path) and os.path.isdir(path)

    @staticmethod
    def check_file(file):
        return (os.path.exists(file) and os.path.isfile(file))

    def check_repository(self):
        repository = os.path.join(self.path, "repository")
        if not self.does_dir_exist(repository):
            sys.exit("Repository is not initialized, "
                     "call 'init' in an empty folder to do it.")
        objects = RepositoryInfo.does_dir_exist(self.objects)
        last_state = RepositoryInfo.does_dir_exist(self.last_state)
        if not (objects and last_state):
            sys.exit("Repository is damaged.")
        for file in self.repo_files:
            if not self.check_file(file):
                sys.exit("Repository is damaged.")

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
    status_console_log(path, dir_comparer)
    filesToCompare = [[os.path.join(repo.last_state, x),
                       os.path.join(path, x)] for x in dir_comparer.changed]
    files_comparer = FilesComparer(filesToCompare)
    diffs = files_comparer.compareFiles()
    deleted = deleted_content(path, dir_comparer.deleted)
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


def deleted_content(path, deleted_files):
    file_to_content = {}
    for file in deleted_files:
        deleted = os.path.join(path, "repository", "last_state", file)
        os.chmod(deleted, 0o777)
        with open(deleted, 'r') as f:
            file_to_content[file] = f.readlines()
    return file_to_content


def commit(path, tag=None, comment=None):
    repo = RepositoryInfo(path)
    repo.check_repository()
    print("Repository is OK, start committing.")
    print()

    if tag is not None:
        with open(repo.tags, 'rb') as tags:
            while True:
                try:
                    pair = pickle.load(tags)
                    if tag == pair[0]:
                        sys.exit("This tag is already used, you can't give it to new commit")
                except EOFError:
                    break

    commit_index = len(os.listdir(os.path.join(path, "repository", "objects")))
    commit_file = os.path.join(path, "repository", "objects", str(commit_index) + ".dat")
    shutil.copyfile(repo.index, commit_file)
    with open(repo.index, 'wb'):
        pass

    head = ''
    with open(repo.head, 'r') as f:
        head = f.read()
    last_commit = None
    commits_dict = {}
    if head != '':
        with open(repo.commits, 'rb') as commits:
            commits_dict = pickle.load(commits)
            last_commit = commits_dict[head]
    current_commit = CommitInfo()
    if last_commit is None:
        current_commit.set_init_commit(tag, comment, commit_index)
    else:
        current_commit.set_next_commit_in_branch(last_commit, tag, comment, commit_index)

    if tag is not None:
        with open(repo.tags, 'ab') as tags:
            tag_pair = [tag, current_commit]
            pickle.dump(tag_pair, tags)

    commits_dict[str(commit_index)] = current_commit
    with open(repo.commits, 'wb') as commits:
        pickle.dump(commits_dict, commits)

    set_head_commit(repo.head, repo.branches, current_commit)

    current_commit.log_info_to_file(repo.logs)
    if tag is not None:
        print('Commited with tag:', tag)
    if comment is not None:
        print('Comment:', comment)
    print('Committing finished')


def set_head_commit(head_record, branches_file, new_head_commit):
    with open(head_record, 'w') as head:
        head.write(new_head_commit.commit_index)

    branches_dict = {}
    if new_head_commit.prev_commit_index is not None:
        with open(branches_file, 'rb') as branches:
            branches_dict = pickle.load(branches)
    branches_dict[new_head_commit.branch] = new_head_commit
    with open(branches_file, 'wb') as branches:
        pickle.dump(branches_dict, branches)


def reset(path, tag):
    repo = RepositoryInfo(path)
    repo.check_repository()
    print("Repository is OK, start checking last commit.")
    print()
    relevant = is_last_commit_relevant(path)
    if not relevant:
        sys.exit("Your folder has uncommitted changes, commit before restoring.")
    print("Last commit is relevant, start resetting.")
    print()
    tag_commit_index = get_commit_info_by_tag(path, tag).commit_index
    head_index = ''
    with open(repo.head, 'r') as f:
        head_index = f.read()
    resets_track = queue.Queue()
    get_resets_track(path, resets_track, head_index, tag_commit_index)
    while not resets_track.empty():
        step_commit = resets_track.get()
        commit_file = os.path.join(repo.objects, step_commit + ".dat")
        deltas_info = {}
        with open(commit_file, 'rb') as commit:
            deltas_info = pickle.load(commit)
        for added_file in deltas_info["Added"]:
            absolute_file = os.path.join(path, added_file)
            os.chmod(absolute_file, 0o777)
            if os.path.isdir(absolute_file):
                shutil.rmtree(absolute_file)
            else:
                os.remove(absolute_file)
        for file in deltas_info["Deleted"]:
            content = deltas_info["Deleted"][file]
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
            reset_lines = FilesComparer().previous_file_version(file_lines,
                                                                deltas_info["Changed"][file])
            with open(file, 'w') as f:
                f.writelines(reset_lines)

    new_head_commit = CommitInfo()
    with open(repo.commits, 'rb') as f:
        commit_dict = pickle.load(f)
        new_head_commit = commit_dict[tag_commit_index]
    set_head_commit(repo.head, repo.branches, new_head_commit)
    print('Resetting finished.')


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
    if current == final:
        return
    track.put(current)
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


def status(path):
    repo = RepositoryInfo(path)
    repo.check_repository()
    dir_comparer = DirContentComparer(path)
    dir_comparer.compare()
    no_changes = len(dir_comparer.added) == 0 and \
                 len(dir_comparer.changed) == 0 and \
                 len(dir_comparer.deleted) == 0
    if no_changes:
        if os.path.getsize(repo.index) == 0:
            print("Current state of folder is saved.\nNothing to add, nothing to commit.")
        else:
            print("All tracked changes are added, commit them.")
    else:
        status_console_log(path, dir_comparer)


def branch(path):
    head_record = os.path.join(path, "repository", "head.txt")
    head_index = ''
    with open(head_record, 'r') as f:
        head_index = f.read()

    branches_file = os.path.join(path, "repository", "branches.dat")
    current_branch = ''
    print("Branches:")
    with open(branches_file, 'rb') as branches:
        branches_dict = pickle.load(branches)
        for branch in branches_dict:
            print(" ", branch)
            if branches_dict[branch].commit_index == head_index:
                current_branch = branch
    print("Current branch:", current_branch)


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
        branch(args.path)


if __name__ == '__main__':
    main()
