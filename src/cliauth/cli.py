from pathlib import Path
from typing import Annotated, Optional

import tomli_w
import typer

from cliauth import output
from cliauth.config import get_config_path, get_masked_config, init_config, load_config
from cliauth.providers import PROVIDER_REGISTRY
from cliauth.providers.base import AuthProvider

app = typer.Typer(
    name="cliauth",
    help="Unified CLI authentication manager.",
    no_args_is_help=True,
)

config_app = typer.Typer(help="Manage cliauth configuration.")
app.add_typer(config_app, name="config")

ConfigOption = Annotated[
    Optional[Path],
    typer.Option("--config", "-c", help="Path to config file"),
]


def _get_providers(
    config: dict, tool: str | None = None
) -> list[tuple[str, AuthProvider]]:
    if tool:
        if tool not in PROVIDER_REGISTRY:
            output.error(
                f"Unknown tool: {tool}. "
                f"Available: {', '.join(PROVIDER_REGISTRY.keys())}"
            )
            raise typer.Exit(1)
        provider_cls = PROVIDER_REGISTRY[tool]
        section_config = config.get(tool, {})
        return [(tool, provider_cls(section_config))]

    providers = []
    for name, provider_cls in PROVIDER_REGISTRY.items():
        section_config = config.get(name, {})
        providers.append((name, provider_cls(section_config)))
    return providers


@app.command()
def setup(
    tool: Annotated[
        Optional[str], typer.Argument(help="Specific tool to set up")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show commands without executing")
    ] = False,
    config_path: ConfigOption = None,
) -> None:
    """Set up authentication for all or a specific CLI tool."""
    try:
        config = load_config(config_path)
    except FileNotFoundError as e:
        output.error(str(e))
        raise typer.Exit(1) from e

    providers = _get_providers(config, tool)
    results: list[tuple[str, bool]] = []

    for name, provider in providers:
        missing = provider.validate_config()
        if missing:
            output.warning(
                f"[{name}] Skipping: missing config keys: {', '.join(missing)}"
            )
            results.append((name, False))
            continue

        if not provider.is_installed():
            output.warning(
                f"[{name}] Skipping: {provider.required_binary} not found on PATH"
            )
            results.append((name, False))
            continue

        ok = provider.setup(dry_run=dry_run)
        results.append((name, ok))

    succeeded = sum(1 for _, ok in results if ok)
    total = len(results)
    output.info(f"\nSetup complete: {succeeded}/{total} tools configured.")

    if succeeded < total:
        raise typer.Exit(1)


@app.command()
def status(
    tool: Annotated[
        Optional[str], typer.Argument(help="Specific tool to check")
    ] = None,
    config_path: ConfigOption = None,
) -> None:
    """Show authentication status for all or a specific CLI tool."""
    try:
        config = load_config(config_path)
    except FileNotFoundError as e:
        output.error(str(e))
        raise typer.Exit(1) from e

    providers = _get_providers(config, tool)
    all_rows: list[tuple[str, bool, str]] = []

    for name, provider in providers:
        if not provider.is_installed():
            all_rows.append((name, False, f"{provider.required_binary} not installed"))
            continue

        rows = provider.status()
        all_rows.extend(rows)

    output.print_status_table(all_rows)


@config_app.command("init")
def config_init(
    config_path: ConfigOption = None,
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite existing config")
    ] = False,
) -> None:
    """Create a template configuration file."""
    try:
        path = init_config(config_path, force=force)
        output.success(f"Config created: {path}")
        output.info("Edit this file with your tokens and settings.")
    except FileExistsError as e:
        output.error(str(e))
        raise typer.Exit(1) from e


@config_app.command("show")
def config_show(config_path: ConfigOption = None) -> None:
    """Show current configuration with tokens masked."""
    try:
        config = load_config(config_path)
    except FileNotFoundError as e:
        output.error(str(e))
        raise typer.Exit(1) from e

    masked = get_masked_config(config)
    output.console.print(tomli_w.dumps(masked))


@config_app.command("path")
def config_path_cmd() -> None:
    """Print the config file path."""
    path = get_config_path()
    exists = "[green]exists[/green]" if path.exists() else "[red]not found[/red]"
    output.console.print(f"{path} ({exists})")
