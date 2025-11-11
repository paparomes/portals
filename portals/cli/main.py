"""Main CLI entry point for Portals."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click

from portals import __version__
from portals.services.init_service import InitService
from portals.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


@click.group()
@click.version_option(version=__version__, prog_name="Portals")
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    envvar="LOG_LEVEL",
    help="Set the logging level",
)
@click.option(
    "--log-format",
    type=click.Choice(["human", "json"], case_sensitive=False),
    default="human",
    envvar="LOG_FORMAT",
    help="Set the logging format",
)
@click.pass_context
def cli(ctx: click.Context, log_level: str, log_format: str) -> None:
    """Portals - Multi-platform document synchronization tool.

    Keeps local markdown files in sync with Notion, Google Docs, and Obsidian.

    \b
    Examples:
      # Initialize mirror mode for Notion sync
      docsync init notion-mirror --teamspace=portals

      # Start watching for changes
      docsync watch

      # Check sync status
      docsync status

      # Sync a specific file
      docsync sync path/to/file.md

    For more help on a specific command, run:
      docsync COMMAND --help
    """
    # Store config in context
    ctx.ensure_object(dict)
    ctx.obj["LOG_LEVEL"] = log_level
    ctx.obj["LOG_FORMAT"] = log_format

    # Configure logging
    configure_logging(level=log_level, format=log_format)

    logger.debug("cli_started", version=__version__, log_level=log_level)


@cli.command()
@click.option(
    "--root-page-id",
    required=True,
    help="Notion root page ID where synced pages will be created as children",
)
@click.option(
    "--notion-token",
    envvar="NOTION_API_TOKEN",
    help="Notion API token (or set NOTION_API_TOKEN env var)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be created without actually creating pages",
)
@click.option(
    "--path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=".",
    help="Directory to sync (defaults to current directory)",
)
@click.pass_context
def init(
    ctx: click.Context,
    root_page_id: str,
    notion_token: str | None,
    dry_run: bool,
    path: str,
) -> None:
    """Initialize Portals mirror mode for Notion sync.

    Sets up bidirectional sync between a local directory and Notion pages.

    \b
    Example:
      docsync init --root-page-id=abc123 --notion-token=secret_xxx

    Or set NOTION_API_TOKEN environment variable:
      export NOTION_API_TOKEN=secret_xxx
      docsync init --root-page-id=abc123
    """
    # Get Notion token
    if not notion_token:
        click.echo("❌ Error: Notion API token required")
        click.echo("   Set --notion-token or NOTION_API_TOKEN environment variable")
        raise click.Abort()

    logger.info(
        "init_command",
        root_page_id=root_page_id,
        dry_run=dry_run,
        path=path,
    )

    # Run async initialization
    async def run_init() -> None:
        base_path = Path(path).resolve()

        click.echo(f"🔍 Initializing Portals in {base_path}")
        if dry_run:
            click.echo("   (DRY RUN - no pages will be created)")

        # Create init service
        init_service = InitService(
            base_path=base_path,
            notion_token=notion_token,
            root_page_id=root_page_id,
        )

        # Run initialization
        try:
            result = await init_service.initialize_mirror_mode(dry_run=dry_run)

            if result.success:
                click.echo("\n✅ Initialization complete!")
                click.echo(f"   Files synced: {result.files_synced}")
                click.echo(f"   Pages created: {result.pages_created}")

                if not dry_run:
                    click.echo(f"\n💡 Metadata saved to {base_path / '.docsync'}")
                    click.echo("   Run 'docsync sync' to perform bidirectional sync")
                    click.echo("   Run 'docsync watch' to auto-sync changes")
            else:
                click.echo("\n⚠️  Initialization completed with errors:")
                for error in result.errors:
                    click.echo(f"   - {error}")

        except Exception as e:
            click.echo(f"\n❌ Initialization failed: {e}")
            logger.error("init_failed", error=str(e))
            raise click.Abort() from e

    asyncio.run(run_init())


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show sync status of all paired documents."""
    logger.info("status_command", message="Status command (not yet implemented)")
    click.echo("📊 Status display (coming in Phase 4)")


@cli.command()
@click.argument("path", required=False)
@click.pass_context
def sync(ctx: click.Context, path: str | None) -> None:
    """Sync documents (bidirectional).

    If PATH is provided, sync only that file.
    Otherwise, sync all paired documents.
    """
    logger.info("sync_command", path=path, message="Sync command (not yet implemented)")
    if path:
        click.echo(f"🔄 Syncing {path} (coming in Phase 4)")
    else:
        click.echo("🔄 Syncing all documents (coming in Phase 4)")


@cli.command()
@click.pass_context
def watch(ctx: click.Context) -> None:
    """Watch for file changes and prompt to sync.

    Runs continuously, monitoring for local and remote changes.
    Press Ctrl+C to stop.
    """
    logger.info("watch_command", message="Watch command (not yet implemented)")
    click.echo("👀 Watch mode (coming in Phase 6)")


@cli.command()
@click.pass_context
def version(ctx: click.Context) -> None:
    """Show version information."""
    click.echo(f"Portals version {__version__}")
    click.echo("Multi-platform document synchronization tool")
    click.echo("CLI command: docsync")
    click.echo("\nProject: https://github.com/paparomes/portals")


if __name__ == "__main__":
    cli()
