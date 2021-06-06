from .add import AddRepo
import os
import queue
import pickle
from pathlib import Path
from Comparers import FilesComparer
from CommitInfo import CommitInfo


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

    def get_path_on_branch(self, branch, start_commit, finish_commit_info):
        """
        Возвращает две переменных: путь-очередь коммитов
        и флаг движения изменений назад по истории.
        """
        commits_to_check = queue.Queue()
        finish = CommitInfo()
        finish.commit = finish_commit_info.commit
        back = self.prev_on_branch(finish_commit_info.prev_commit, finish)
        next = self.next_on_branch(
            finish_commit_info.get_next_commit_on_branch(branch),
            finish)
        commits_to_check.put(back)
        commits_to_check.put(next)
        while not commits_to_check.empty():
            checking = commits_to_check.get()
            if checking.commit is not None:
                if checking.commit == start_commit:
                    return self.get_commits_track_and_head_by_linked(checking)
                checking_info = self.get_commit_info(checking.commit)
                if checking.next_on_branch is None:
                    next = self.next_on_branch(
                        checking_info.get_next_commit_on_branch(
                            branch), checking)
                    commits_to_check.put(next)
                else:
                    back = self.prev_on_branch(checking_info.prev_commit,
                                               checking)
                    commits_to_check.put(back)

    @staticmethod
    def prev_on_branch(prev_commit, current):
        prev = CommitInfo()
        prev.commit = prev_commit
        prev.next_on_branch = current
        return prev

    @staticmethod
    def next_on_branch(next_commit, current):
        next = CommitInfo()
        next.commit = next_commit
        next.prev_commit = current
        return next

    @staticmethod
    def get_commits_track_and_head_by_linked(commit_info):
        """
        По односвязному списку от элемента commit_info
        возвращает очередь-путь и направление движения по истории коммитов.
        """
        track = queue.Queue()
        is_back = True
        if commit_info.next_on_branch is None:
            while commit_info.prev_commit is not None:
                track.put(commit_info.commit)
                commit_info = commit_info.prev_commit
        else:
            is_back = False
            commit_info = commit_info.next_on_branch
            while commit_info.next_on_branch is not None:
                track.put(commit_info.commit)
                commit_info = commit_info.next_on_branch
            track.put(commit_info.commit)
        return track, is_back

    def get_switch_back_track_by_steps(self, track, current, steps):
        """
        Добавление в очередь коммитов для прохождения
        на steps шагов назад по ветке
        """
        if steps == 0:
            return
        if steps > 0 and current is None:
            raise self.SwitchingException("You put a greater number "
                                          "than the commits amount.\n"
                                          "Rollback is impossible.")
        track.put(current)
        prev_commit = self.get_commit_info(current).prev_commit
        self.get_switch_back_track_by_steps(track, prev_commit, steps - 1)

    def get_switch_forward_track_by_steps(self, track, current, branch, steps):
        """
        Добавление в очередь коммитов для прохождения
        на steps шагов вперёд по ветке branch
        """
        if steps == 0:
            return
        commit_info = self.get_commit_info(current)
        if commit_info.branch == branch:
            next_commit = commit_info.next_on_branch
        else:
            next_commit = commit_info.branches_next[branch]
        if steps > 0 and next_commit is None:
            raise self.SwitchingException("You put a greater number "
                                          "than the commits amount.\n"
                                          "Switching is impossible.")
        track.put(next_commit)
        self.get_switch_forward_track_by_steps(track, next_commit,
                                               branch, steps - 1)

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

    class PathStep:
        def __init__(self, prev_step, commit, moving_back=None):
            self.prev_step = prev_step
            self.commit = commit
            self.is_back = moving_back

    def get_paths_through_branches(self, start_commit, finish_commit_info):
        """
        Возвращает список пар:
        1. Путь от коммита до коммита между разветвлениями;
        2. Флаг движения назад по истории.
        """
        commits_to_check = queue.Queue()
        finish_step = self.PathStep(None, finish_commit_info.commit)
        self.add_nearest_commits_to_queue(commits_to_check, finish_step,
                                     finish_commit_info)
        while not commits_to_check.empty():
            checking = commits_to_check.get()
            if checking.commit == start_commit:
                return self.get_paths_by_link(checking)
            checking_info = self.get_commit_info(checking.commit)
            self.add_nearest_commits_to_queue(commits_to_check, checking,
                                         checking_info)

    def add_nearest_commits_to_queue(self, queue, step, commit_info):
        if step.prev_step is None or \
                (commit_info.prev_commit is not None and
                 commit_info.prev_commit != step.prev_step.commit):
            back_step = self.PathStep(step, commit_info.prev_commit, False)
            if back_step is not None:
                queue.put(back_step)
        for next_commit in commit_info.get_all_next_commits():
            if step.prev_step is None or \
                    next_commit != step.prev_step.commit:
                next_step = self.PathStep(step, next_commit, True)
                queue.put(next_step)

    @staticmethod
    def get_paths_by_link(path_step):
        """
        По односвязному списку шагов возвращает список путей
        с соответствующим им направлениям.
        """
        paths = []
        path_queue = queue.Queue()
        is_back = path_step.is_back
        while path_step is not None:
            if path_step.is_back != is_back and path_step.is_back is not None:
                paths.append([path_queue, is_back])
                path_queue = queue.Queue()
                is_back = path_step.is_back
            path_queue.put(path_step.commit)
            path_step = path_step.prev_step
        paths.append([path_queue, is_back])
        return paths

    def switch_between_branches(self, finish_commit_info):
        """
        Совершает переход к заданному коммиту, находящемуся на другой ветке,
        возвращает коммит, ставший головным.
        """
        paths = self.get_paths_through_branches(self.head, finish_commit_info)
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
            file_lines = ''
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
            file_lines = ''
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


def switch(path, tag=None, steps_back=None, steps_forward=None):
    repo = SwitchingRepo(path)
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
            _tag_switching()
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
    if steps_back is not None:
        repo.get_switch_back_track_by_steps(switching_track, repo.head,
                                            int(steps_back))
    elif steps_forward is not None:
        branch = repo.get_head_commit_info().branch
        repo.get_switch_forward_track_by_steps(switching_track, repo.head,
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

    if (head_info.branch in tagged_info.all_commit_branches() or
            tagged_info.branch in head_info.all_commit_branches()):
        switching_track, is_back = repo.get_path_on_branch(
            head_info.branch, head_info.commit, tagged_info)
        new_head = repo.go_through_commits_return_current(switching_track,
                                                          is_back)
    else:
        new_head = repo.switch_between_branches(tagged_info)
    return new_head


def _log_switching(repo):
    """Запись информации о переключении состояния в логи"""
    with open(repo.logs, 'a') as logs:
        head = repo.get_head_commit_info()
        logs.write(f"Switch on commit {head.commit}\n")
        logs.write(f"On branch {head.branch}\n")
        logs.write('\n')
