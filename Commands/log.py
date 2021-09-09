from .RepositoryInfo import RepositoryInfo


def log(args):
    repo = RepositoryInfo(args.path)
    repo.check_repository()
    with open(repo.logs, 'r') as logsfile:
        logs = logsfile.read()
    print(logs)
    print('Logs printing finished.')


def clearlog(args):
    repo = RepositoryInfo(args.path)
    repo.check_repository()
    with open(repo.logs, 'w'):
        pass
    print('Logs cleared.')
