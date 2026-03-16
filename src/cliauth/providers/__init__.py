from cliauth.providers.acli import AtlassianProvider
from cliauth.providers.aws import AWSProvider
from cliauth.providers.gh import GitHubProvider
from cliauth.providers.sentry import SentryProvider

PROVIDER_REGISTRY: dict[str, type] = {
    "gh": GitHubProvider,
    "aws": AWSProvider,
    "sentry": SentryProvider,
    "acli": AtlassianProvider,
}

__all__ = [
    "PROVIDER_REGISTRY",
    "AtlassianProvider",
    "AWSProvider",
    "GitHubProvider",
    "SentryProvider",
]
