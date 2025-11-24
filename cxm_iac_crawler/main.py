import logging
import os
import subprocess
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from .compute_terraform_show import compute_terraform_show
from .find_entrypoints import find_terraform_lock_files
from .send_to_cxm import CRAWLER_VERSION, send_data_to_cxm
from .unnest_tf_show import unnest_tf_show

logger = logging.getLogger(__name__)

base_keys = ["address", "mode", "type", "name", "provider_name", "schema_version"]
values_keys = ["arn", "description", "id", "name", "tags", "tags_all"]

# Supported CI/CD platforms
SUPPORTED_PLATFORMS = {"github", "gitlab", "generic"}


def detect_ci_platform(platform_hint: str | None = None) -> str:
    """
    Detect the CI/CD platform.

    Args:
        platform_hint: Optional platform name (github, gitlab, generic) to override auto-detection

    Returns:
        str: Platform name (github, gitlab, or generic)

    Raises:
        ValueError: If platform_hint is provided but not supported
    """
    # Use platform hint if provided
    if platform_hint:
        platform = platform_hint.lower()
        if platform not in SUPPORTED_PLATFORMS:
            raise ValueError(f"Unsupported platform: {platform}. Supported platforms: {', '.join(sorted(SUPPORTED_PLATFORMS))}")
        return platform
    # GitHub Actions
    elif os.getenv("GITHUB_ACTIONS") == "true":
        return "github"
    # GitLab CI
    elif os.getenv("GITLAB_CI"):
        return "gitlab"
    # Generic fallback
    else:
        return "generic"


def create_scan_metadata(platform: str) -> dict:
    """
    Create complete scan metadata for a given platform.

    Args:
        platform: Platform name (github, gitlab, or generic)

    Returns:
        dict: Complete CI/CD metadata structured for API payload

    Raises:
        ValueError: If platform is not supported
    """
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError(f"Unsupported platform: {platform}. Supported platforms: {', '.join(sorted(SUPPORTED_PLATFORMS))}")

    scan_metadata = {
        "platform": platform,
        "scan_timestamp": datetime.now(UTC).isoformat(),
        "crawler_version": CRAWLER_VERSION,
        "run_id": str(uuid.uuid4()),
    }

    # Collect platform-specific metadata
    match platform:
        case "github":
            scan_metadata.update(
                {
                    "workflow_id": os.getenv("GITHUB_WORKFLOW"),
                    "actor": os.getenv("GITHUB_ACTOR"),
                    "trigger_event": os.getenv("GITHUB_EVENT_NAME"),
                    "repository_owner": os.getenv("GITHUB_REPOSITORY_OWNER"),
                    "repository_name": os.getenv("GITHUB_REPOSITORY", "").split("/")[-1] if os.getenv("GITHUB_REPOSITORY") else None,
                    "repository_default_branch": os.getenv("GITHUB_REF_NAME")
                    if os.getenv("GITHUB_REF_NAME") in ("main", "master")
                    else None,
                    "runner_os": os.getenv("RUNNER_OS"),
                    "runner_arch": os.getenv("RUNNER_ARCH"),
                }
            )
        case "gitlab":
            scan_metadata.update(
                {
                    "workflow_id": os.getenv("CI_PIPELINE_ID"),
                    "actor": os.getenv("GITLAB_USER_LOGIN"),
                    "trigger_event": os.getenv("CI_PIPELINE_SOURCE"),
                    "repository_owner": os.getenv("CI_PROJECT_NAMESPACE"),
                    "repository_name": os.getenv("CI_PROJECT_NAME"),
                    "repository_default_branch": os.getenv("CI_DEFAULT_BRANCH"),
                    "runner_os": "linux",
                }
            )
        case "generic":
            # No platform-specific metadata for generic platform
            pass

    # Clean None values
    return {k: v for k, v in scan_metadata.items() if v is not None}


def select_essential_data(resource_list: Iterator[dict]) -> Iterator[dict]:
    for resource in resource_list:
        # Check for required fields
        if "address" not in resource:
            logger.warning("Skipping resource without 'address' field")
            continue

        if "values" not in resource or "arn" not in resource["values"]:
            logger.warning(f"Skipping resource {resource.get('address', 'unknown')} without 'arn' field")
            continue

        new_resource = {}
        for base_key in base_keys:
            if base_key in resource:
                new_resource[base_key] = resource[base_key]
        new_resource["values"] = {}
        for values_key in values_keys:
            if values_key in resource["values"]:
                new_resource["values"][values_key] = resource["values"][values_key]
        yield new_resource


def process_show_output(show_output: dict) -> Iterator[dict]:
    resources = unnest_tf_show(show_output)
    resources = select_essential_data(resources)
    return resources


def process_repository(
    repository_dir: str | Path,
    repository_url: str,
    platform: str,
    dry_run: bool = False,
    paths: list[Path] | None = None,
):
    """Process all Terraform configurations in a repository.

    Args:
        repository_dir: Root directory of the repository to scan
        repository_url: URL of the repository being crawled
        platform: CI/CD platform name (github, gitlab, or generic)
        dry_run: If True, parse data without sending to API
        paths: Optional list of specific Terraform entry points to scan. If provided, lock file discovery is skipped.

    Raises:
        subprocess.CalledProcessError: If terraform show fails
        ValueError: If platform is not supported
    """
    # Create scan metadata with timestamp and run_id
    scan_metadata = create_scan_metadata(platform)
    logger.info(f"Platform: {scan_metadata['platform']}, Run ID: {scan_metadata['run_id']}")
    logger.debug(f"Scan metadata: {scan_metadata}")

    entry_points_found = 0
    entry_points_processed = 0

    # If specific paths are provided, use them; otherwise discover via lock files
    if paths:
        entry_points = paths
        logger.info(f"Using {len(entry_points)} specified path(s), skipping lock file discovery")
    else:
        entry_points = find_terraform_lock_files(repository_dir)
        logger.info("Discovering Terraform configurations via lock files")

    errors = 0
    for entry_point in entry_points:
        entry_points_found += 1
        logger.info(f"Processing Terraform configuration at: {entry_point}")

        try:
            tfshow = compute_terraform_show(entry_point)
            resources = process_show_output(tfshow)
            send_data_to_cxm(resources, repository_url=repository_url, scan_metadata=scan_metadata, dry_run=dry_run)
            entry_points_processed += 1

        except subprocess.CalledProcessError as e:
            # terraform show failed - likely to fail for all entry points
            logger.error(f"Terraform show failed - aborting scan: {e}")
            raise

        except Exception as e:
            errors +=1
            logger.error(f"Failed to process {entry_point.parent}: {e}", exc_info=True)
            continue
    if errors > 0:
        raise e
    logger.info(f"Scan complete: processed {entry_points_processed}/{entry_points_found} Terraform configurations")
