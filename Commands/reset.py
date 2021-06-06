from .switch import SwitchingRepo
import queue


class ResetRepo(SwitchingRepo):
    def get_resets_track_by_tag(self, track, current, final):
        """
        Добавляет в очередь коммиты, которые нужно пройти
        назад по ветке до коммита с заданным тэгом.
        """
        if current == final:
            return
        track.put(current)
        prev_commit = self.get_commit_info(current).prev_commit
        self.get_resets_track_by_tag(track, prev_commit, final)

    def cut_branch_after_head(self):
        head_info = self.get_head_commit_info()
        head_info.next_on_branch = None
        self.add_commit_info(head_info)
        self.rewrite_branch_head(head_info)


def reset(path, tag=None, steps_back=None):
    repo = ResetRepo(path)
    try:
        repo.checks_before_switching()
    except (repo.CommitException, repo.RepositoryCheckingException) as e:
        print(e)
        return


    resets_track = queue.Queue()
    try:
        if tag is not None:
            tag_commit = repo.get_tag_commit(tag)
            repo.get_resets_track_by_tag(resets_track, repo.head, tag_commit)
        elif steps_back is not None:
            repo.get_switch_back_track_by_steps(resets_track, repo.head,
                                                int(steps_back))
        else:
            raise repo.SwitchingException("Put a tag or an amount of steps "
                                          "to reset")
    except repo.SwitchingException as e:
        print(e)
        return

    new_head = repo.go_through_commits_return_current(resets_track, True)
    repo.rewrite_head(new_head)
    repo.cut_branch_after_head()
    repo.update_last_state()
    _log_reset(repo, tag, steps_back)
    print('Resetting finished.')


def _log_reset(repo, tag, steps):
    """Запись информации о сбросе состояния в логи"""
    with open(repo.logs, 'a') as logs:
        logs.write(f"Reset on commit {repo.head}\n")
        if tag is not None:
            logs.write(f"With tag {tag}\n")
        if steps is not None:
            logs.write(f"{str(steps)} steps back\n")
        logs.write("\n")
