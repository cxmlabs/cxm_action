import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class SensitiveKeyError(Exception):
    """Raised when a resource key matches a sensitive field pattern"""

    pass


# Load sensitive fields from environment variable or use defaults
_env_sensitive = os.getenv("SENSITIVE_FIELDS", "")
_additional_sensitive = [f.strip() for f in _env_sensitive.split(",") if f.strip()]
SENSITIVE_FIELDS = ["public_key"] + _additional_sensitive


def is_key_sensitive(key: str) -> bool:
    """Check if a key contains sensitive field names.

    Args:
        key: The key name to check against sensitive field patterns.

    Returns:
        True if the key may be sensitive, False otherwise.
    """
    return any(field in key for field in SENSITIVE_FIELDS)


def check_sensitive_fields_config():
    for field in ["arn", "values", "address"]:
        if is_key_sensitive(field):
            raise SensitiveKeyError(field)


def remove_sensitive_data(resource: dict):
    """Remove sensitive data from a Terraform resource.

    Uses the resource's sensitive_values metadata to identify and redact
    sensitive fields in the resource values.

    Args:
        resource: A Terraform resource dictionary containing 'values' and
                 optionally 'sensitive_values' keys.

    Returns:
        The resource dictionary with sensitive values redacted.

    Raises:
        SensitiveKeyError: If the resource's arn or address matches a sensitive field pattern
    """
    # Check if arn or address match sensitive fields
    if "sensitive_values" in resource:
        resource["values"] = remove_sensitive_recursive(
            resource["values"], resource["sensitive_values"]
        )
    else:
        resource["values"] = remove_sensitive_recursive(resource["values"], {})
    return resource


def remove_sensitive_recursive(values: Any, sensitive_values: dict | list | bool):
    """Recursively redact sensitive values from nested data structures.

    Traverses nested dictionaries and lists, replacing sensitive values with
    redaction markers based on Terraform's sensitive_values metadata structure.

    Args:
        values: The actual values from the Terraform resource (dict, list, or primitive).
        sensitive_values: The sensitive_values metadata that mirrors the structure
                         of values, where True indicates a sensitive field, dicts/lists
                         contain nested sensitivity markers.

    Returns:
        The values structure with sensitive data replaced by '**SENSITIVE**' or
        '**REDACTED**' markers.
    """
    if isinstance(sensitive_values, dict):
        new_values = {}
        for key, value in values.items():
            if is_key_sensitive(key):
                new_values[key] = "**REDACTED**"
            elif key in sensitive_values:
                new_values[key] = remove_sensitive_recursive(
                    value, sensitive_values[key]
                )
            else:
                new_values[key] = value
        return new_values
    elif isinstance(sensitive_values, list):
        new_values = []
        for resource_value, sensitive_value in zip(values, sensitive_values):
            new_values.append(
                remove_sensitive_recursive(resource_value, sensitive_value)
            )
        return new_values
    elif sensitive_values is True:
        return "**SENSITIVE**"
    else:
        return values


def recursive_unnest_child_modules(module: dict):
    """Recursively extract and sanitize resources from a module and its children.

    Flattens the hierarchical module structure from Terraform show output,
    yielding all resources with sensitive data removed.

    Args:
        module: A Terraform module dictionary containing 'resources' and
               optionally 'child_modules' keys.

    Yields:
        Sanitized resource dictionaries with sensitive values redacted.
    """
    yield from map(remove_sensitive_data, module["resources"])
    for child_module in module.get("child_modules", []):
        yield from recursive_unnest_child_modules(child_module)


def unnest_tf_show(show_data: dict):
    """Extract all resources from Terraform show output with sensitive data removed.

    Parses the output of 'terraform show -json' and flattens the module hierarchy,
    yielding individual resources with all sensitive values redacted.

    Args:
        show_data: The parsed JSON output from 'terraform show -json' command.
                  Expected to have structure: {'values': {'root_module': {...}}}
                  If no state exists, show_data may be empty or missing 'values'.

    Yields:
        Sanitized resource dictionaries, one for each resource found in the
        Terraform state across all modules. Yields nothing if no state exists.
    """
    check_sensitive_fields_config()

    # Handle empty state (no resources deployed yet)
    if "values" not in show_data:
        logger.info("No state found in terraform show output (no 'values' key)")
        return

    root_module = show_data["values"].get("root_module")
    if root_module is None:
        logger.info("No root_module found in terraform show output")
        return

    yield from recursive_unnest_child_modules(root_module)
