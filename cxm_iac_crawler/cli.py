"""CLI entry point for IAC Crawler."""

import argparse
import logging
import sys
from pathlib import Path

from .main import detect_ci_platform, process_repository


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the CLI.

    Args:
        verbose: Enable verbose (DEBUG level) logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )


def main() -> int:
    """Main CLI entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(description="Scan Terraform infrastructure and send resources to CXM API")
    parser.add_argument(
        "repository_path",
        type=Path,
        help="Path to the repository to scan for Terraform configurations",
    )
    parser.add_argument(
        "--repository-url",
        type=str,
        help="URL of the repository being crawled (included in API requests)",
        default=None,
    )
    parser.add_argument(
        "--platform",
        type=str,
        help="CI/CD platform (github, gitlab, or generic) - auto-detected if not provided",
        default=None,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Enable dry-run mode (parse data without posting to API)",
    )
    parser.add_argument(
        "--path",
        type=str,
        help="Specific Terraform entrypoint path(s) to scan (comma-separated). If provided, lock file discovery is skipped.",
        default=None,
    )

    args = parser.parse_args()

    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)

    try:
        repository_path = args.repository_path.resolve()

        if not repository_path.exists():
            logger.error(f"Repository path does not exist: {repository_path}")
            return 1

        if not repository_path.is_dir():
            logger.error(f"Repository path is not a directory: {repository_path}")
            return 1

        # Detect CI/CD platform (determination only, metadata created in process_repository)
        platform = detect_ci_platform(platform_hint=args.platform)
        logger.info(f"Detected platform: {platform}")

        # Ensure repository_url is provided
        repository_url = args.repository_url
        if not repository_url:
            logger.warning("Repository URL not provided, using 'unknown'")
            repository_url = "unknown"

        if args.dry_run:
            logger.info("DRY-RUN MODE: Data will be parsed but not sent to API")

        # Parse paths if provided
        paths = None
        if args.path:
            paths = [Path(p.strip()) for p in args.path.split(",")]
            # Convert relative paths to absolute paths relative to repository_path
            paths = [repository_path / p if not p.is_absolute() else p for p in paths]
            logger.info(f"Scanning {len(paths)} specific path(s): {', '.join(str(p) for p in paths)}")

        logger.info(f"Starting IAC scan of repository: {repository_path}")
        process_repository(
            repository_path, repository_url=repository_url, platform=platform, dry_run=args.dry_run, paths=paths
        )
        logger.info("IAC scan completed successfully")
        return 0

    except KeyboardInterrupt:
        logger.info("Scan interrupted by user")
        return 130

    except Exception as e:
        logger.exception(f"Fatal error during IAC scan: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
