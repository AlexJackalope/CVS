import queue
from CommitInfo import CommitInfo


class CommitsPathSeeker:
    class PathStep:
        def __init__(self, prev_step, commit, moving_back=None):
            self.prev_step = prev_step
            self.commit = commit
            self.is_back = moving_back

    def __init__(self, switch_repository):
        self.repo = switch_repository

    def get_switch_back_track_by_steps(self, track, current, steps):
        """
        Добавление в очередь коммитов для прохождения
        на steps шагов назад по ветке
        """
        if steps == 0:
            return
        if steps > 0 and current is None:
            raise self.repo.SwitchingException("You put a greater number "
                                               "than the commits amount.\n"
                                               "Rollback is impossible.")
        track.put(current)
        prev_commit = self.repo.get_commit_info(current).prev_commit
        self.get_switch_back_track_by_steps(track, prev_commit, steps - 1)

    def get_switch_forward_track_by_steps(self, track, current, branch, steps):
        """
        Добавление в очередь коммитов для прохождения
        на steps шагов вперёд по ветке branch
        """
        if steps == 0:
            return
        commit_info = self.repo.get_commit_info(current)
        if commit_info.branch == branch:
            next_commit = commit_info.next_on_branch
        else:
            next_commit = commit_info.branches_next[branch]
        if steps > 0 and next_commit is None:
            raise self.repo.SwitchingException("You put a greater number "
                                               "than the commits amount.\n"
                                               "Switching is impossible.")
        track.put(next_commit)
        self.get_switch_forward_track_by_steps(track, next_commit,
                                               branch, steps - 1)

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
            checking_info = self.repo.get_commit_info(checking.commit)
            self.add_nearest_commits_to_queue(commits_to_check, checking,
                                              checking_info)

    def add_nearest_commits_to_queue(self, queue, step, commit_info):
        """
        Добавление в очередь следующего коммита,
        на который ссылается данный commit_info
        """
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
                checking_info = self.repo.get_commit_info(checking.commit)
                if checking.next_on_branch is None:
                    next = self.next_on_branch(
                        checking_info.get_next_commit_on_branch(branch),
                        checking)
                    commits_to_check.put(next)
                else:
                    back = self.prev_on_branch(checking_info.prev_commit,
                                               checking)
                    commits_to_check.put(back)

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

    @staticmethod
    def prev_on_branch(prev_commit, current):
        """Возвращает имя предыдущего коммита"""
        prev = CommitInfo()
        prev.commit = prev_commit
        prev.next_on_branch = current
        return prev

    @staticmethod
    def next_on_branch(next_commit, current):
        """Возвращает имя следующего коммита"""
        next = CommitInfo()
        next.commit = next_commit
        next.prev_commit = current
        return next
