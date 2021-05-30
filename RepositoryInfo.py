import os, sys
import pickle


class TagPair:
    def __init__(self, tag, commit):
        self.tag = tag
        self.commit = commit


class Deltas:
    def __init__(self, added, changed, deleted):
        self.added = added
        self.changed = changed
        self.deleted = deleted


class RepositoryInfo:
    def __init__(self, path):
        self.path = path
        self.last_state = os.path.join(path, "repository", "last_state")
        self.objects = os.path.join(path, "repository", "objects")
        self.branches = os.path.join(path, "repository", "branches.dat")
        self.commits = os.path.join(path, "repository", "commits.dat")
        self._head_file = os.path.join(path, "repository", "head.txt")
        self.index = os.path.join(path, "repository", "index.dat")
        self.logs = os.path.join(path, "repository", "logs.txt")
        self.tags = os.path.join(path, "repository", "tags.dat")
        self.repo_files = [self.branches, self.commits, self._head_file, self.index, self.logs, self.tags]

    @staticmethod
    def does_dir_exist(path):
        return os.path.exists(path) and os.path.isdir(path)

    @staticmethod
    def check_file(file):
        return os.path.exists(file) and os.path.isfile(file)

    @property
    def head(self):
        """Имя головного коммита"""
        head = ''
        with open(self._head_file, 'r') as f:
            head = f.read()
        return head

    def check_repository(self):
        """Проверка существования служебных файлов репозитория"""
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

    def get_tag_commit(self, tag):
        """Имя коммита по тэгу, None, если тэга не существует"""
        with open(self.tags, 'rb') as tags:
            while True:
                try:
                    pair = pickle.load(tags)
                    if tag == pair.tag:
                        return pair.commit
                except EOFError:
                    return None

    def get_branch_head_commit(self, branch):
        """Имя головного коммита ветки, None, если ветки не существует"""
        with open(self.branches, 'rb') as branches:
            try:
                branches_dict = pickle.load(branches)
                if branch in branches_dict:
                    return branches_dict[branch]
                else:
                    return None
            except EOFError:
                sys.exit("Make your first commit to setup branches.")

    def add_tag(self, tag, tagged_commit):
        with open(self.tags, 'ab') as tags:
            tag_pair = TagPair(tag, tagged_commit)
            pickle.dump(tag_pair, tags)

    def rewrite_head(self, commit):
        """Установка головного коммита"""
        with open(self._head_file, 'w') as head:
            head.write(commit)

    def rewrite_branch_head(self, commit_info):
        """Установка головного коммита ветки"""
        branches_dict = {}
        with open(self.branches, 'rb') as branches:
            try:
                branches_dict = pickle.load(branches)
            except EOFError:
                pass
        branches_dict[commit_info.branch] = commit_info.commit
        with open(self.branches, 'wb') as branches:
            pickle.dump(branches_dict, branches)

    def add_branch(self, branch):
        head_commit = self.get_head_commit_info()
        head_commit.set_new_branch(branch)
        self.add_commit_info(head_commit)
        self._add_branch_to_branches(head_commit)

    def _add_branch_to_branches(self, branch_commit):
        branches_dict = {}
        with open(self.branches, 'rb') as branches:
            branches_dict = pickle.load(branches)
        branches_dict[branch_commit.branch] = branch_commit.commit
        with open(self.branches, 'wb') as branches:
            pickle.dump(branches_dict, branches)

    def clear_index(self):
        with open(self.index, 'wb'):
            pass

    def get_commit_info(self, commit):
        """Информация о коммите по его имени"""
        commit_info = None
        with open(self.commits, 'rb') as commits:
            commits_dict = pickle.load(commits)
            commit_info = commits_dict[commit]
        return commit_info

    def get_head_commit_info(self):
        head = self.head
        if head != '':
            return self.get_commit_info(head)
        else:
            return None

    def add_commit_info(self, commit_info):
        """Обновление информации о коммите"""
        commits_dict = {}
        with open(self.commits, 'rb') as commits:
            try:
                commits_dict = pickle.load(commits)
            except EOFError:
                pass
        commits_dict[commit_info.commit] = commit_info
        with open(self.commits, 'wb') as commits:
            pickle.dump(commits_dict, commits)
