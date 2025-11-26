import logging
from collections.abc import Iterator
from pathlib import Path

logger = logging.getLogger(__name__)

# Directories to exclude from entry point discovery
EXCLUDED_DIRS = {".terraform", "modules", ".git", ".hidden", "__pycache__", ".pytest_cache", ".venv", "node_modules"}


def _is_valid_entrypoint(lock_file_path: Path, root_path: Path) -> bool:
    """
    Check if a lock file is a valid entry point and not a false positive.

    Args:
        lock_file_path: Path to the .terraform.lock.hcl file
        root_path: Root directory for relative path calculation

    Returns:
        bool: True if the lock file is a valid entry point, False otherwise
    """
    # Get the parent directory containing the lock file
    parent_dir = lock_file_path.parent

    # Get relative path from root to parent directory
    try:
        rel_path = parent_dir.relative_to(root_path)
    except ValueError:
        # Path is not relative to root
        return False

    # Check if any part of the path contains excluded directories
    for part in rel_path.parts:
        if part in EXCLUDED_DIRS:
            logger.debug(f"Excluding lock file {lock_file_path}: contains excluded directory '{part}'")
            return False

    return True


def find_terraform_lock_files(root_dir: str | Path) -> Iterator[Path]:
    """
    Find all directories containing .terraform.lock.hcl files in a directory tree.
    Excludes false positives such as lock files in .terraform directories, modules, and other ignored directories.

    Args:
        root_dir: Root directory to search from

    Yields:
        Path objects for each directory containing a valid .terraform.lock.hcl file
    """
    root_path = Path(root_dir)

    if not root_path.exists():
        logger.error(f"Directory does not exist: {root_path}")
        raise FileNotFoundError(f"Directory does not exist: {root_path}")

    if not root_path.is_dir():
        logger.error(f"Path is not a directory: {root_path}")
        raise NotADirectoryError(f"Path is not a directory: {root_path}")

    logger.info(f"Searching for .terraform.lock.hcl files in {root_path}")

    for lock_file in root_path.rglob(".terraform.lock.hcl"):
        if _is_valid_entrypoint(lock_file, root_path):
            logger.debug(f"Found valid entry point: {lock_file.parent}")
            yield lock_file.parent
