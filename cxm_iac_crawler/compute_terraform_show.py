import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TERRAFORM_SHOW_TIMEOUT = int(os.getenv("TERRAFORM_SHOW_TIMEOUT", "300"))


def compute_terraform_show(terraform_dir: str | Path) -> dict[str, Any]:
    """
    Execute terraform init and terraform show, then return the result as a Python object

    Args:
        terraform_dir: Directory containing Terraform configuration

    Returns:
        Dictionary containing the terraform show output

    Raises:
        FileNotFoundError: If terraform_dir doesn't exist
        subprocess.CalledProcessError: If terraform command fails
        json.JSONDecodeError: If terraform output is not valid JSON
    """
    terraform_path = Path(terraform_dir)

    if not terraform_path.exists():
        logger.error(f"Directory does not exist: {terraform_path}")
        raise FileNotFoundError(f"Directory does not exist: {terraform_path}")

    if not terraform_path.is_dir():
        logger.error(f"Path is not a directory: {terraform_path}")
        raise NotADirectoryError(f"Path is not a directory: {terraform_path}")

    logger.info(f"Running terraform init in {terraform_path}")

    try:
        # Run terraform init first (with backend to access state)
        init_result = subprocess.run(
            ["terraform", "init"],
            cwd=terraform_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=TERRAFORM_SHOW_TIMEOUT,
        )
        logger.debug("Terraform init completed successfully")
        if init_result.stdout:
            logger.debug(f"Terraform init output: {init_result.stdout}")

        # Then run terraform show
        logger.info(f"Running terraform show in {terraform_path}")
        result = subprocess.run(
            ["terraform", "show", "-json"],
            cwd=terraform_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=TERRAFORM_SHOW_TIMEOUT,
        )

        logger.debug("Terraform show completed successfully")

        terraform_data = json.loads(result.stdout)
        logger.info(f"Parsed terraform show output ({len(result.stdout)} bytes)")

        return terraform_data

    except subprocess.TimeoutExpired:
        logger.error(f"Terraform show timed out after {TERRAFORM_SHOW_TIMEOUT} seconds in {terraform_path}")
        raise

    except subprocess.CalledProcessError as e:
        logger.error(f"Terraform show failed in {terraform_path}: exit code {e.returncode}, stderr: {e.stderr}")
        raise

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse terraform show output as JSON: {e}")
        raise
