from .add import AddRepo
from Commands.CommitsPathSeeker import CommitsPathSeeker
import os
import queue
import pickle
from pathlib import Path
from Comparers import FilesComparer


class SwitchingRepo(AddRepo):
    class SwitchingException(Exception):
        def __init__(self, message):
            if message:
                self.message = message

        def __str__(self):
            if self.message:
                return f'Switching exception: {self.message}'
            return 'Switching exception'

    def checks_before_switching(self):
        """
        Проверки на целостность репозитория
        и актуальность последнего коммита
        """
        self.check_repository()
        print("Repository is OK, start checking last commit.")
        print()

        relevant = self.is_last_state_relevant()
        if (not relevant) or os.path.getsize(self.index) > 0:
            raise self.CommitException("Your folder has uncommitted changes, "
                                       "commit them before switching state.")
        print("Last commit is relevant.")
        print()

    def go_through_commits_return_current(self, commits_track, is_back):
        """
        Переход состояния папки вперёд или назад по истории коммитов
        внутри ветки
        """
        step_commit = None
        while not commits_track.empty():
            step_commit = commits_track.get()
            commit_file = os.path.join(self.objects, step_commit + ".dat")
            with open(commit_file, 'rb') as commit:
                while True:
                    try:
                        deltas_info = pickle.load(commit)
                        if is_back:
                            self.go_to_previous_state(deltas_info)
                        else:
                            self.go_to_next_state(deltas_info)
                    except EOFError:
                        break
        if is_back:
            info = self.get_commit_info(step_commit)
            return info.prev_commit
        else:
            return step_commit

    def switch_between_branches(self, paths):
        """
        Совершает переход к заданному коммиту, находящемуся на другой ветке,
        возвращает коммит, ставший головным.
        """
        for path_pair in paths:
            switching_track = path_pair[0]
            is_back = path_pair[1]
            new_head = self.go_through_commits_return_current(switching_track,
                                                              is_back)
        return new_head

    def go_to_previous_state(self, deltas):
        """Откат состояния папки на один коммит назад"""
        self._delete_files(self.path, deltas.added.keys())
        self._add_files(self.path, deltas.deleted)
        for file in deltas.changed:
            with open(file, 'r') as f:
                file_lines = f.readlines()
            prev_lines = FilesComparer().previous_file_version(
                file_lines, deltas.changed[file])
            with open(file, 'w') as f:
                f.writelines(prev_lines)

    def go_to_next_state(self, deltas):
        """Переход состояния папки на один коммит вперёд"""
        self._delete_files(self.path, deltas.deleted.keys())
        self._add_files(self.path, deltas.added)
        for file in deltas.changed:
            with open(file, 'r') as f:
                file_lines = f.readlines()
            next_lines = FilesComparer().next_file_version(file_lines,
                                                           deltas.changed[
                                                               file])
            with open(file, 'w') as f:
                f.writelines(next_lines)

    @staticmethod
    def _add_files(path, file_to_content):
        """
        Добавление файлов в папку
        и их заполнение соответствующим содержимым
        """
        for file in file_to_content:
            content = file_to_content[file]
            absolute_file = os.path.join(path, file)
            file_dir_path = os.path.dirname(absolute_file)
            if not os.path.exists(file_dir_path):
                os.makedirs(file_dir_path)
            Path(absolute_file).touch()
            with open(absolute_file, 'w') as f:
                f.writelines(content)


def switch(args):
    tag = None
    steps_back = None
    steps_forward = None
    if len(args.command) == 2:
        sign = args.command[1][0]
        if sign == '-':
            steps_back = args.command[1][1:]
        if sign == '+':
            steps_forward = args.command[1][1:]
    else:
        tag = args.tag

    repo = SwitchingRepo(args.path)
    try:
        repo.checks_before_switching()
    except (repo.CommitException, repo.RepositoryCheckingException) as e:
        print(e)
        return

    switching_track = queue.Queue()
    try:
        if tag is None:
            new_head = _step_switching(repo, steps_back, steps_forward,
                                       switching_track)
        else:
            new_head = _tag_switching(repo, tag)
    except (repo.SwitchingException, repo.TagException) as e:
        print(e)
        return

    repo.rewrite_head(new_head)
    _log_switching(repo)
    repo.update_last_state()
    print('Switching finished.')


def _step_switching(repo, steps_back, steps_forward, switching_track):
    """
    Проход по числу коммитов вперёд/назад по текущей ветке с возвращением
    нового головного коммита
    """
    is_back = True
    seeker = CommitsPathSeeker(repo)
    if steps_back is not None:
        seeker.get_switch_back_track_by_steps(switching_track, repo.head,
                                              int(steps_back))
    elif steps_forward is not None:
        branch = repo.get_head_commit_info().branch
        seeker.get_switch_forward_track_by_steps(switching_track, repo.head,
                                                 branch, int(steps_forward))
        is_back = False
    else:
        raise repo.SwitchingException("Put a tag or an amount of steps "
                                      "to switch.")
    new_head = repo.go_through_commits_return_current(switching_track, is_back)
    return new_head


def _tag_switching(repo, tag):
    tagged_commit = repo.get_tag_commit(tag)
    if tagged_commit is None:
        raise repo.TagException("Commit with this tag does not exist")

    tagged_info = repo.get_commit_info(tagged_commit)
    head_info = repo.get_head_commit_info()
    seeker = CommitsPathSeeker(repo)

    if (head_info.branch in tagged_info.all_commit_branches() or
            tagged_info.branch in head_info.all_commit_branches()):
        switching_track, is_back = seeker.get_path_on_branch(
            head_info.branch, head_info.commit, tagged_info)
        new_head = repo.go_through_commits_return_current(switching_track,
                                                          is_back)
    else:
        paths = seeker.get_paths_through_branches(repo.head, tagged_info)
        new_head = repo.switch_between_branches(paths)
    return new_head


def _log_switching(repo):
    """Запись информации о переключении состояния в логи"""
    with open(repo.logs, 'a') as logs:
        head = repo.get_head_commit_info()
        logs.write(f"Switch on commit {head.commit}\n")
        logs.write(f"On branch {head.branch}\n")
        logs.write('\n')
