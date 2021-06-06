from .switch import SwitchingRepo
from .branch import BranchRepo


class CheckoutRepo(SwitchingRepo, BranchRepo):
    def checkout_checks(self, branch_name):
        self.check_repository()
        if branch_name is None:
            raise self.BranchException("Put a name of branch to checkout.")
        branch_head = self.get_branch_head_commit(branch_name)
        if branch_head is None:
            raise self.BranchException(
                "No such branch. Call 'branch' to see repository's branches.")
        head_info = self.get_head_commit_info()
        if head_info.branch == branch_name:
            print("You are on branch. Switching to branch head commit.")


def checkout(path, branch_name):
    repo = CheckoutRepo(path)
    try:
        repo.checkout_checks(branch_name)
    except (repo.BranchException, repo.RepositoryCheckingException) as e:
        print(e)
        return
    branch_head = repo.get_branch_head_commit(branch_name)
    branch_head_info = repo.get_commit_info(branch_head)
    new_head = repo.switch_between_branches(branch_head_info)
    repo.rewrite_head(new_head)
    repo.update_last_state()
    _log_checkout(repo, branch_name)
    print("Branch switching finished.")


def _log_checkout(repo, branch):
    """апись о смене ветки в логи"""
    with open(repo.logs, 'a') as logs:
        logs.write(f"Checkout on branch {branch}\n")
        logs.write('\n')
