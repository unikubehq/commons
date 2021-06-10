class RepositoryBranchUnavailable(Exception):
    pass


class RepositoryAuthenticationFailed(Exception):
    pass


class RepositoryCloningFailed(Exception):
    pass


class HelmDependencyError(Exception):
    pass


class HelmChartRenderError(Exception):
    pass
