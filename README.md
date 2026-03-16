# cliauth

Unified CLI authentication manager. Configure all your CLI tools in one file, authenticate them with one command.

## Supported CLIs

| CLI | Auth Method |
|-----|-------------|
| **GitHub CLI** (`gh`) | Token via `gh auth login --with-token` |
| **AWS CLI** (`aws`) | SSO login trigger per profile |
| **Sentry CLI** (`sentry-cli`) | Token written to `~/.sentryclirc` |
| **Atlassian CLI** (`acli`) | API token via `acli jira auth login` |

## Installation

```bash
uv tool install cliauth
```

Or for development:

```bash
git clone https://github.com/8percent/cliauth.git
cd cliauth
uv tool install -e .
```

## Quick Start

```bash
# Create a config template
cliauth config init

# Edit ~/.config/cliauth/config.toml with your tokens

# Authenticate all CLIs
cliauth setup

# Check status
cliauth status
```

## Configuration

Config file: `~/.config/cliauth/config.toml`

Override with `--config` flag or `CLIAUTH_CONFIG` environment variable.

```toml
[gh]
token = "ghp_your_github_token"

[aws]
sso_profiles = ["profile-1", "profile-2"]

[sentry]
auth_token = "sntryu_your_sentry_token"
org = "your-org"
project = "your-project"  # optional

[acli]
site = "your-site.atlassian.net"
email = "your@email.com"
api_token = "your-atlassian-api-token"
```

## Commands

```bash
cliauth setup [TOOL]       # Set up auth for all or specific tool
cliauth setup --dry-run    # Preview commands without executing
cliauth status [TOOL]      # Check auth status
cliauth config init        # Create config template
cliauth config show        # Show config (tokens masked)
cliauth config path        # Print config file path
```

## Development

```bash
# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest tests/

# Run tests with coverage
uv run pytest tests/ --cov=src/

# Lint
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# Run tox
uv run tox
```

## License

MIT
