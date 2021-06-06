from .add import AddRepo
import os
import shutil
import pickle


class CommitRepo(AddRepo):
    class TagPair:
        def __init__(self, tag, commit):
            self.tag = tag
            self.commit = commit

    def commit_checks(self, tag):
        """
        Осуществляет проверки до создания коммита,
        выход из программы, если коммит невозможен.
        """
        self.check_repository()

        if os.path.getsize(self.index) == 0:
            if not self.is_last_state_relevant():
                raise self.CommitException("Add changes before committing.")
            else:
                raise self.CommitException("Nothing to commit.")

        if tag is not None:
            if self.is_tag_in_repo_tree(tag):
                raise self.TagException("This tag is already used, "
                                        "you can't give it to new commit.")

        if not self.is_current_branch_free():
            raise self.CommitException("This commit already has next one. "
                                       "Create a branch to add.")

        print("Repository is OK, start committing.")
        print()

    def is_tag_in_repo_tree(self, tag):
        """Проверка существования тэга"""
        with open(self.tags, 'rb') as tags:
            while True:
                try:
                    pair = pickle.load(tags)
                    if tag == pair.tag:
                        return True
                except EOFError:
                    return False

    def is_current_branch_free(self):
        """
        Проверяет наличие следующего коммита у данного головного.
        True, если ветка свободно для добавления коммита,
        False, если в ветке есть следующий коммит.
        """
        head_info = self.get_head_commit_info()
        return head_info is None or head_info.next_on_branch is None

    def clear_index(self):
        """Очистка файла index.dat"""
        with open(self.index, 'wb'):
            pass

    def add_tag(self, tag, tagged_commit):
        """Добавление коммита в список по тэгу"""
        with open(self.tags, 'ab') as tags:
            tag_pair = self.TagPair(tag, tagged_commit)
            pickle.dump(tag_pair, tags)


def commit(path, tag=None, comment=None):
    repo = CommitRepo(path)
    try:
        repo.commit_checks(tag)
    except (repo.RepositoryCheckingException, repo.CommitException,
            repo.TagException) as e:
        print(e)
        return

    commit_index = str(len(os.listdir(repo.objects)))
    commit_file = os.path.join(repo.objects, commit_index + ".dat")
    shutil.copyfile(repo.index, commit_file)
    repo.clear_index()
    repo.set_new_commit(commit_index)

    if tag is not None:
        repo.add_tag(tag, commit_index)

    _log_commit(repo, repo.get_head_commit_info(), tag, comment)
    if tag is not None:
        print(f'Commited with tag: {tag}.')
    if comment is not None:
        print(f'Comment: {comment}.')
    print('Committing finished.')


def _log_commit(repo, commit_info, tag, comment):
    """Запись информации о сделанном коммите в логи"""
    with open(repo.logs, 'a') as logs:
        logs.write(f"Commit {commit_info.commit}\n")
        logs.write(f"On branch {commit_info.branch}\n")
        if tag is not None:
            logs.write(f"Tag: {tag}\n")
        if comment is not None:
            logs.write(f"Comment: {comment}\n")
        logs.write('\n')
