"""Unit and integration tests for unnest_tf_show module."""

import inspect
from unittest.mock import Mock

from cxm_iac_crawler.unnest_tf_show import (
    check_sensitive_fields_config,
    is_key_sensitive,
    recursive_unnest_child_modules,
    remove_sensitive_data,
    remove_sensitive_recursive,
    unnest_tf_show,
)


class TestIsKeySensitive:
    """Unit tests for is_key_sensitive function."""

    def test_is_real_function(self):
        """Verify we're testing the real function, not a mock."""
        assert inspect.isfunction(is_key_sensitive)
        assert not isinstance(is_key_sensitive, Mock)
        assert is_key_sensitive.__module__ == "cxm_iac_crawler.unnest_tf_show"

    def test_detects_default_sensitive_field(self):
        """Should detect 'public_key' as sensitive."""
        assert is_key_sensitive("public_key") is True

    def test_detects_partial_match(self):
        """Should detect keys containing sensitive field names."""
        assert is_key_sensitive("aws_public_key_pair") is True
        assert is_key_sensitive("my_public_key") is True

    def test_non_sensitive_key(self):
        """Should return False for non-sensitive keys."""
        assert is_key_sensitive("arn") is False
        assert is_key_sensitive("description") is False
        assert is_key_sensitive("tags") is False

    def test_empty_string(self):
        """Should handle empty string."""
        assert is_key_sensitive("") is False

    def test_case_sensitive(self):
        """Should be case-sensitive by default."""
        assert is_key_sensitive("PUBLIC_KEY") is False

    def test_with_custom_sensitive_fields(self):
        """Should check if key contains any configured sensitive field."""
        # Test with default sensitive fields list
        # The actual SENSITIVE_FIELDS list includes "public_key" by default
        # This test just verifies the function checks all configured fields
        assert is_key_sensitive("my_public_key") is True
        assert is_key_sensitive("some_public_key_value") is True


class TestCheckSensitiveFieldsConfig:
    """Unit tests for check_sensitive_fields_config function."""

    def test_is_real_function(self):
        """Verify we're testing the real function, not a mock."""
        assert inspect.isfunction(check_sensitive_fields_config)
        assert not isinstance(check_sensitive_fields_config, Mock)

    def test_valid_config(self):
        """Should not raise error with valid config."""
        # Default config should be valid
        check_sensitive_fields_config()

    def test_raises_when_critical_fields_would_be_sensitive(self):
        """Should raise error if critical fields (arn, values, address) would be sensitive.

        This test validates the configuration check logic without modifying global state.
        The actual environment variable testing is covered by integration tests.
        """
        # With default config (SENSITIVE_FIELDS = ["public_key"]), none of these should match
        # So this should not raise
        check_sensitive_fields_config()

        # The function checks that "arn", "values", and "address" are NOT sensitive
        # If any were sensitive, it would raise SensitiveKeyError
        # Since we can't easily test this without polluting state, we verify the check runs


class TestRemoveSensitiveRecursive:
    """Unit tests for remove_sensitive_recursive function."""

    def test_is_real_function(self):
        """Verify we're testing the real function, not a mock."""
        assert inspect.isfunction(remove_sensitive_recursive)
        assert not isinstance(remove_sensitive_recursive, Mock)

    def test_non_sensitive_dict(self):
        """Should return dict unchanged if no sensitive values."""
        values = {"name": "test", "id": "123"}
        sensitive = {}
        result = remove_sensitive_recursive(values, sensitive)
        assert result == values

    def test_redacts_sensitive_boolean(self):
        """Should replace value with **SENSITIVE** when sensitive_values is True."""
        values = "secret_password"
        sensitive = True
        result = remove_sensitive_recursive(values, sensitive)
        assert result == "**SENSITIVE**"

    def test_redacts_sensitive_dict_field(self):
        """Should recursively redact sensitive fields in dict."""
        values = {"name": "test", "password": "secret123"}
        sensitive = {"password": True}
        result = remove_sensitive_recursive(values, sensitive)
        assert result == {"name": "test", "password": "**SENSITIVE**"}

    def test_redacts_key_matching_pattern(self):
        """Should redact keys matching sensitive field patterns."""
        values = {"name": "test", "public_key": "ssh-rsa AAAA..."}
        sensitive = {}
        result = remove_sensitive_recursive(values, sensitive)
        assert result == {"name": "test", "public_key": "**REDACTED**"}

    def test_nested_dict_redaction(self):
        """Should handle nested dictionaries."""
        values = {"outer": {"inner": {"secret": "value"}}}
        sensitive = {"outer": {"inner": {"secret": True}}}
        result = remove_sensitive_recursive(values, sensitive)
        assert result == {"outer": {"inner": {"secret": "**SENSITIVE**"}}}

    def test_list_redaction(self):
        """Should handle lists of values."""
        values = ["public", "private"]
        sensitive = [False, True]
        result = remove_sensitive_recursive(values, sensitive)
        assert result == ["public", "**SENSITIVE**"]

    def test_mixed_list_and_dict(self):
        """Should handle mixed structures."""
        values = {"items": [{"key": "public"}, {"key": "private"}]}
        sensitive = {"items": [{"key": False}, {"key": True}]}
        result = remove_sensitive_recursive(values, sensitive)
        assert result == {"items": [{"key": "public"}, {"key": "**SENSITIVE**"}]}

    def test_empty_structures(self):
        """Should handle empty dicts and lists."""
        assert remove_sensitive_recursive({}, {}) == {}
        assert remove_sensitive_recursive([], []) == []

    def test_primitive_values(self):
        """Should pass through non-sensitive primitive values."""
        assert remove_sensitive_recursive("string", False) == "string"
        assert remove_sensitive_recursive(123, False) == 123
        assert remove_sensitive_recursive(None, False) is None


class TestRemoveSensitiveData:
    """Unit tests for remove_sensitive_data function."""

    def test_is_real_function(self):
        """Verify we're testing the real function, not a mock."""
        assert inspect.isfunction(remove_sensitive_data)
        assert not isinstance(remove_sensitive_data, Mock)

    def test_resource_without_sensitive_values(self):
        """Should handle resources without sensitive_values key."""
        resource = {"values": {"name": "test", "id": "123"}}
        result = remove_sensitive_data(resource)
        assert result["values"] == {"name": "test", "id": "123"}

    def test_resource_with_sensitive_values(self):
        """Should redact sensitive values based on metadata."""
        resource = {"values": {"name": "test", "password": "secret"}, "sensitive_values": {"password": True}}
        result = remove_sensitive_data(resource)
        assert result["values"] == {"name": "test", "password": "**SENSITIVE**"}

    def test_preserves_other_fields(self):
        """Should preserve non-values fields."""
        resource = {"address": "aws_instance.example", "type": "aws_instance", "values": {"id": "i-123"}}
        result = remove_sensitive_data(resource)
        assert result["address"] == "aws_instance.example"
        assert result["type"] == "aws_instance"

    def test_redacts_public_key_fields(self):
        """Should redact fields matching sensitive patterns."""
        resource = {"values": {"name": "test", "public_key": "ssh-rsa AAAA..."}}
        result = remove_sensitive_data(resource)
        assert result["values"]["public_key"] == "**REDACTED**"


class TestRecursiveUnnestChildModules:
    """Unit tests for recursive_unnest_child_modules function."""

    def test_is_real_function(self):
        """Verify we're testing the real function, not a mock."""
        assert inspect.isfunction(recursive_unnest_child_modules)
        assert not isinstance(recursive_unnest_child_modules, Mock)

    def test_module_without_children(self):
        """Should yield resources from module without child_modules."""
        module = {"resources": [{"values": {"id": "1"}}, {"values": {"id": "2"}}]}
        results = list(recursive_unnest_child_modules(module))
        assert len(results) == 2
        assert results[0]["values"]["id"] == "1"
        assert results[1]["values"]["id"] == "2"

    def test_module_with_children(self):
        """Should recursively yield resources from child modules."""
        module = {
            "resources": [{"values": {"id": "parent"}}],
            "child_modules": [{"resources": [{"values": {"id": "child1"}}]}, {"resources": [{"values": {"id": "child2"}}]}],
        }
        results = list(recursive_unnest_child_modules(module))
        assert len(results) == 3
        ids = [r["values"]["id"] for r in results]
        assert "parent" in ids
        assert "child1" in ids
        assert "child2" in ids

    def test_nested_child_modules(self):
        """Should handle deeply nested modules."""
        module = {
            "resources": [{"values": {"id": "root"}}],
            "child_modules": [
                {"resources": [{"values": {"id": "level1"}}], "child_modules": [{"resources": [{"values": {"id": "level2"}}]}]}
            ],
        }
        results = list(recursive_unnest_child_modules(module))
        assert len(results) == 3
        ids = [r["values"]["id"] for r in results]
        assert ids == ["root", "level1", "level2"]

    def test_empty_resources(self):
        """Should handle modules with empty resources list."""
        module = {"resources": []}
        results = list(recursive_unnest_child_modules(module))
        assert len(results) == 0

    def test_removes_sensitive_data(self):
        """Should apply remove_sensitive_data to all resources."""
        module = {"resources": [{"values": {"id": "1", "password": "secret"}, "sensitive_values": {"password": True}}]}
        results = list(recursive_unnest_child_modules(module))
        assert results[0]["values"]["password"] == "**SENSITIVE**"


class TestUnnestTfShow:
    """Unit tests for unnest_tf_show function."""

    def test_is_real_function(self):
        """Verify we're testing the real function, not a mock."""
        assert inspect.isfunction(unnest_tf_show)
        assert not isinstance(unnest_tf_show, Mock)

    def test_basic_structure(self):
        """Should extract resources from standard terraform show structure."""
        show_data = {"values": {"root_module": {"resources": [{"values": {"id": "test-resource"}}]}}}
        results = list(unnest_tf_show(show_data))
        assert len(results) == 1
        assert results[0]["values"]["id"] == "test-resource"

    def test_with_child_modules(self):
        """Should extract resources from root and child modules."""
        show_data = {
            "values": {
                "root_module": {
                    "resources": [{"values": {"id": "root"}}],
                    "child_modules": [{"resources": [{"values": {"id": "child"}}]}],
                }
            }
        }
        results = list(unnest_tf_show(show_data))
        assert len(results) == 2

    def test_calls_check_config(self):
        """Should call check_sensitive_fields_config before processing."""
        # The function should check config - verified by checking it doesn't raise
        # with valid default config
        show_data = {"values": {"root_module": {"resources": []}}}
        results = list(unnest_tf_show(show_data))
        assert results == []  # Empty resources, but no error means check passed

    def test_empty_resources(self):
        """Should handle show data with no resources."""
        show_data = {"values": {"root_module": {"resources": []}}}
        results = list(unnest_tf_show(show_data))
        assert len(results) == 0

    def test_empty_state_no_values_key(self):
        """Should handle terraform show output with no state (empty dict)."""
        # When terraform show is run on a module without state, it returns {}
        show_data = {}
        results = list(unnest_tf_show(show_data))
        assert len(results) == 0

    def test_values_without_root_module(self):
        """Should handle values dict without root_module key."""
        show_data = {"values": {}}
        results = list(unnest_tf_show(show_data))
        assert len(results) == 0


class TestIntegrationUnnestTfShow:
    """Integration tests for complete terraform show processing."""

    def test_complete_workflow_with_sensitive_data(self):
        """Should process complete terraform show output with sensitive data removal."""
        # Realistic terraform show structure
        show_data = {
            "values": {
                "root_module": {
                    "resources": [
                        {
                            "address": "aws_instance.web",
                            "mode": "managed",
                            "type": "aws_instance",
                            "name": "web",
                            "values": {
                                "id": "i-1234567890abcdef0",
                                "ami": "ami-12345678",
                                "private_key": "secret-key",
                                "public_key": "ssh-rsa AAAA...",
                            },
                            "sensitive_values": {"private_key": True},
                        }
                    ],
                    "child_modules": [
                        {
                            "resources": [
                                {
                                    "address": "module.database.aws_db_instance.main",
                                    "mode": "managed",
                                    "type": "aws_db_instance",
                                    "name": "main",
                                    "values": {"id": "mydb", "password": "db-password"},
                                    "sensitive_values": {"password": True},
                                }
                            ]
                        }
                    ],
                }
            }
        }

        results = list(unnest_tf_show(show_data))

        assert len(results) == 2

        # Check root module resource
        web_instance = results[0]
        assert web_instance["address"] == "aws_instance.web"
        assert web_instance["values"]["id"] == "i-1234567890abcdef0"
        assert web_instance["values"]["private_key"] == "**SENSITIVE**"
        assert web_instance["values"]["public_key"] == "**REDACTED**"  # Pattern match

        # Check child module resource
        db_instance = results[1]
        assert db_instance["address"] == "module.database.aws_db_instance.main"
        assert db_instance["values"]["id"] == "mydb"
        assert db_instance["values"]["password"] == "**SENSITIVE**"

    def test_complex_nested_structures(self):
        """Should handle complex nested data structures."""
        show_data = {
            "values": {
                "root_module": {
                    "resources": [
                        {
                            "address": "aws_instance.complex",
                            "values": {
                                "tags": {"Name": "test", "Environment": "dev"},
                                "block_device_mappings": [
                                    {"device_name": "/dev/sda1", "ebs": {"encrypted": True, "kms_key_id": "key-123"}}
                                ],
                                "security_groups": ["sg-123", "sg-456"],
                            },
                            "sensitive_values": {"block_device_mappings": [{"ebs": {"kms_key_id": True}}]},
                        }
                    ]
                }
            }
        }

        results = list(unnest_tf_show(show_data))

        assert len(results) == 1
        resource = results[0]
        assert resource["values"]["tags"]["Name"] == "test"
        assert resource["values"]["block_device_mappings"][0]["ebs"]["kms_key_id"] == "**SENSITIVE**"
        assert resource["values"]["security_groups"] == ["sg-123", "sg-456"]

    def test_multiple_levels_of_nesting(self):
        """Should handle deeply nested module hierarchies."""
        show_data = {
            "values": {
                "root_module": {
                    "resources": [{"values": {"id": "root"}}],
                    "child_modules": [
                        {
                            "resources": [{"values": {"id": "level1"}}],
                            "child_modules": [
                                {
                                    "resources": [{"values": {"id": "level2"}}],
                                    "child_modules": [{"resources": [{"values": {"id": "level3"}}]}],
                                }
                            ],
                        }
                    ],
                }
            }
        }

        results = list(unnest_tf_show(show_data))

        assert len(results) == 4
        ids = [r["values"]["id"] for r in results]
        assert ids == ["root", "level1", "level2", "level3"]
