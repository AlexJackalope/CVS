import argparse
import os
import sys
from pathlib import Path


def is_dir_empty(path):
    return not os.listdir(path)


def init(path):
    if not is_dir_empty(path):
        sys.exit("To initialize a repository choose an empty folder")
    repository = path + '\\repository'
    os.mkdir(repository)
    os.mkdir(repository + '\\objects')
    Path(repository + "\\index.bin").touch()
    Path(repository + "\\logs.bin").touch()
    print("Repository initialized")


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


if __name__ == '__main__':
    main()
