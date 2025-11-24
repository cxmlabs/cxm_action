import logging
import os
from collections.abc import Iterator
from importlib.metadata import version
from itertools import islice

import requests

logger = logging.getLogger(__name__)

CXM_API_KEY = os.getenv("CXM_API_KEY", "")
CXM_API_ENDPOINT = os.getenv("CXM_API_ENDPOINT", "")
logger.info(f"using CXM_API_ENDPOINT: {CXM_API_ENDPOINT}")
BATCH_SIZE = 1000
MAX_RETRIES = max(1, int(os.getenv("CXM_MAX_RETRIES", "3")))
TIMEOUT_SECONDS = int(os.getenv("CXM_TIMEOUT_SECONDS", "30"))

CRAWLER_VERSION = version("cxm-iac-crawler")


def _batch_generator(iterable: Iterator[dict], batch_size: int) -> Iterator[list[dict]]:
    """Yield successive batches from an iterator"""
    while True:
        batch = list(islice(iterable, batch_size))
        if not batch:
            break
        yield batch


def _send_single_batch(
    batch: list[dict],
    batch_index: int,
    repository_url: str,
    scan_metadata: dict,
) -> None:
    """Send a single batch of resources to CXM API with CI/CD metadata.

    Args:
        batch: List of resources to send
        batch_index: Index of the batch
        repository_url: URL of the repository being crawled
        scan_metadata: CI/CD platform metadata

    Raises:
        ValueError: If CXM_API_KEY or CXM_API_ENDPOINT is not configured
    """
    if not CXM_API_KEY or not CXM_API_ENDPOINT:
        raise ValueError("CXM_API_KEY and CXM_API_ENDPOINT must be configured")

    payload = {
        "resources": batch,
        "schema_version": 0,
        "repository_url": repository_url,
        "scan_metadata": scan_metadata,
        "scan_timestamp": scan_metadata["scan_timestamp"],
        "crawler_version": CRAWLER_VERSION,
    }

    headers = {"CXM-API-KEY": CXM_API_KEY, "Content-Type": "application/json"}

    for attempt in range(MAX_RETRIES):
        try:
            url = CXM_API_ENDPOINT.strip('/') + '/ci/events/resources'
            response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()

            logger.info(f"Successfully sent batch {batch_index + 1} ({len(batch)} resources)")
            return

        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                logger.warning(f"Failed to send batch {batch_index + 1} (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                continue

            logger.error(f"Failed to send batch {batch_index + 1} after {MAX_RETRIES} attempts: {e}")
            raise


def send_data_to_cxm(
    resource_list: Iterator[dict],
    repository_url: str,
    scan_metadata: dict,
    dry_run: bool = False,
) -> None:
    """
    Send resources to CXM API in batches from a generator.

    Args:
        resource_list: Iterator/generator yielding resource dictionaries
        repository_url: URL of the repository being crawled
        scan_metadata: CI/CD platform metadata
        dry_run: If True, parse data without sending to API

    Raises:
        ValueError: If CXM_API_KEY is not configured (unless in dry-run mode)
    """
    if not dry_run and not CXM_API_KEY:
        raise ValueError("CXM_API_KEY must be configured")

    if dry_run and (not CXM_API_KEY or not CXM_API_ENDPOINT):
        logger.warning("DRY-RUN MODE: CXM_API_KEY and/or CXM_API_ENDPOINT not configured - data will only be parsed")

    if dry_run:
        logger.info(f"DRY-RUN MODE: Processing data with batch size {BATCH_SIZE} (no data will be sent)")
    else:
        logger.info(f"Starting batch send with batch size: {BATCH_SIZE}")

    total_resources = 0
    total_batches = 0

    for batch_idx, batch in enumerate(_batch_generator(resource_list, BATCH_SIZE)):
        total_resources += len(batch)
        total_batches += 1

        if dry_run:
            logger.info(f"DRY-RUN: Would send batch {batch_idx + 1} ({len(batch)} resources)")
            logger.debug(f"DRY-RUN: Batch {batch_idx + 1} sample data: {batch[0] if batch else 'empty'}")
        else:
            _send_single_batch(
                batch,
                batch_idx,
                repository_url=repository_url,
                scan_metadata=scan_metadata,
            )

    if total_batches == 0:
        logger.warning("No resources were processed (generator was empty)")
    else:
        if dry_run:
            logger.info(f"DRY-RUN: Processed {total_batches} batches ({total_resources} resources) without sending")
        else:
            logger.info(f"Successfully sent all {total_batches} batches ({total_resources} resources)")
