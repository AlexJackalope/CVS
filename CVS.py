import argparse
import os
import sys
from pathlib import Path


def is_dir_empty(path):
    return not os.listdir(path)


def check_repository(path):
    repository = os.path.join(path, "repository")
    if not does_dir_exist(repository):
        sys.exit("Repository is not initialized, call 'init' in an empty folder to do it.")
    objects = does_dir_exist(os.path.join(repository, "objects"))
    index = os.path.exists(os.path.join(repository, "index.bin")) and \
            os.path.isfile(os.path.join(repository, "index.bin"))
    logs = os.path.exists(os.path.join(repository, "logs.bin")) and \
           os.path.isfile(os.path.join(repository, "logs.bin"))
    if not (objects and index and logs):
        sys.exit("Repository is damaged.")


def init(path):
    if not is_dir_empty(path):
        sys.exit("To initialize a repository choose an empty folder")
    os.mkdir(os.path.join(path, "repository"))
    os.mkdir(os.path.join(path, "repository", "objects"))
    Path(os.path.join(path, "repository", "index.bin")).touch()
    Path(os.path.join(path, "repository", "logs.bin")).touch()
    print("Repository initialized")


def add(path, files):
    check_repository(path)
    print("Repository is OK")
    for directory in path:
        print("a")


def does_dir_exist(path):
    return os.path.exists(path) and os.path.isdir(path)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", help="CVS command")
    parser.add_argument("path", help="path to a folder with repository")
    parser.add_argument("files", nargs='*',
                        help="bunch of files to add (only for 'add' command)")
    parser.add_argument("-c", "-comment", help="comment for new commit")
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


if __name__ == '__main__':
    main()
