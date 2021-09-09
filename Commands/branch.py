from .RepositoryInfo import RepositoryInfo
import pickle


class BranchRepo(RepositoryInfo):
    class BranchException(Exception):
        def __init__(self, message):
            if message:
                self.message = message

        def __str__(self):
            if self.message:
                return f'Branch exception: {self.message}'
            return 'Branch exception'

    def print_all_branches(self):
        current_branch = ''
        print("Branches:")
        with open(self.branches, 'rb') as branches:
            branches_dict = pickle.load(branches)
            for branch in branches_dict:
                print("\t" + branch)
                if branches_dict[branch] == self.head:
                    current_branch = branch
        print("Current branch:", current_branch)

    def add_branch(self, branch):
        """Добавление ветки в репозиторий"""
        head_commit = self.get_head_commit_info()
        head_commit.set_new_branch(branch)
        self.add_commit_info(head_commit)
        self._add_branch_to_branches(head_commit)

    def _add_branch_to_branches(self, branch_commit):
        """Добавление ветки и её головного коммита в список веток"""
        with open(self.branches, 'rb') as branches:
            branches_dict = pickle.load(branches)
        branches_dict[branch_commit.branch] = branch_commit.commit
        with open(self.branches, 'wb') as branches:
            pickle.dump(branches_dict, branches)


def branch(args):
    repo = BranchRepo(args.path)
    try:
        repo.check_repository()
    except repo.RepositoryCheckingException as e:
        print(e)
        return
    if args.branchname is None:
        repo.print_all_branches()
    else:
        repo.add_branch(args.branchname)
        print('Branch added')
