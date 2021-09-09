import argparse
import sys
import Commands


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
                    "* clearlog - deletes information about commit changes\n"
                    "You can put a CVSignore.txt file in root folder (where "
                    "repository initializes)\n"
                    "and write there regular expressions line by line "
                    "to describe files\n"
                    "which you don't want to track.",
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
    if len(args.command) > 2:
        sys.exit("Input is wrong, please check it again.")
    if not Commands.RepositoryInfo.does_dir_exist(args.path):
        sys.exit(f"Given directory {args.path} does not exist.")

    try:
        if args.command[0] == 'RepositoryInfo':
            raise AttributeError('Incorrect command input')
        command = getattr(Commands, args.command[0])
        command(args)
    except Exception as e:
        print(e)
        print("Incorrect input. Call -h or --help to read manual.")


if __name__ == '__main__':
    main()
