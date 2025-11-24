import logging
from collections.abc import Iterator
from pathlib import Path

logger = logging.getLogger(__name__)


def find_terraform_lock_files(root_dir: str | Path) -> Iterator[Path]:
    """
    Find all directories containing .terraform.lock.hcl files in a directory tree

    Args:
        root_dir: Root directory to search from

    Yields:
        Path objects for each directory containing a .terraform.lock.hcl file
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
        yield lock_file.parent
