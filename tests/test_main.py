"""Unit and integration tests for main module."""

import inspect
import logging
import subprocess
from unittest.mock import Mock, patch

import pytest
from cxm_iac_crawler.main import process_repository, process_show_output, select_essential_data

# Test defaults
TEST_REPOSITORY_URL = "https://github.com/test/repo"
TEST_PLATFORM = "github"


class TestSelectEssentialData:
    """Unit tests for select_essential_data function."""

    def test_extracts_base_keys(self):
        """Should extract base keys from resource."""
        resources = iter(
            [
                {
                    "address": "aws_instance.web",
                    "mode": "managed",
                    "type": "aws_instance",
                    "name": "web",
                    "provider_name": "aws",
                    "schema_version": 0,
                    "values": {
                        "arn": "arn:aws:ec2:us-east-1:123456789012:instance/i-123",
                        "id": "i-123",
                        "ami": "ami-123",
                        "instance_type": "t2.micro",
                    },
                    "extra_field": "should be ignored",
                }
            ]
        )

        result = list(select_essential_data(resources))

        assert len(result) == 1
        assert result[0]["address"] == "aws_instance.web"
        assert result[0]["mode"] == "managed"
        assert result[0]["type"] == "aws_instance"
        assert result[0]["name"] == "web"
        assert result[0]["provider_name"] == "aws"
        assert result[0]["schema_version"] == 0
        assert "extra_field" not in result[0]

    def test_extracts_values_keys(self):
        """Should extract specific keys from values field."""
        resources = iter(
            [
                {
                    "address": "aws_s3_bucket.data",
                    "values": {
                        "arn": "arn:aws:s3:::my-bucket",
                        "description": "My bucket",
                        "id": "my-bucket",
                        "name": "my-bucket",
                        "tags": {"Environment": "prod"},
                        "tags_all": {"Environment": "prod", "ManagedBy": "terraform"},
                        "versioning": {"enabled": True},  # Should be ignored
                    },
                }
            ]
        )

        result = list(select_essential_data(resources))

        assert len(result) == 1
        values = result[0]["values"]
        assert values["arn"] == "arn:aws:s3:::my-bucket"
        assert values["description"] == "My bucket"
        assert values["id"] == "my-bucket"
        assert values["name"] == "my-bucket"
        assert values["tags"] == {"Environment": "prod"}
        assert values["tags_all"] == {"Environment": "prod", "ManagedBy": "terraform"}
        assert "versioning" not in values

    def test_handles_missing_base_keys(self):
        """Should handle resources with missing base keys."""
        resources = iter([{"address": "aws_instance.web", "values": {"arn": "arn:aws:ec2:::i-123", "id": "i-123"}}])

        result = list(select_essential_data(resources))

        assert len(result) == 1
        assert result[0]["address"] == "aws_instance.web"
        assert "mode" not in result[0]
        assert "type" not in result[0]

    def test_handles_missing_values_keys(self):
        """Should handle resources with missing values keys (but arn is required)."""
        resources = iter([{"address": "aws_instance.web", "values": {"arn": "arn:aws:ec2:::i-123", "id": "i-123"}}])

        result = list(select_essential_data(resources))

        assert len(result) == 1
        values = result[0]["values"]
        assert values["arn"] == "arn:aws:ec2:::i-123"
        assert values["id"] == "i-123"
        assert "description" not in values

    def test_multiple_resources(self):
        """Should process multiple resources."""
        resources = iter(
            [
                {"address": "aws_instance.web1", "values": {"arn": "arn:aws:ec2:::i-123", "id": "i-123"}},
                {"address": "aws_instance.web2", "values": {"arn": "arn:aws:ec2:::i-456", "id": "i-456"}},
                {"address": "aws_instance.web3", "values": {"arn": "arn:aws:ec2:::i-789", "id": "i-789"}},
            ]
        )

        result = list(select_essential_data(resources))

        assert len(result) == 3
        assert result[0]["address"] == "aws_instance.web1"
        assert result[1]["address"] == "aws_instance.web2"
        assert result[2]["address"] == "aws_instance.web3"

    def test_empty_iterator(self):
        """Should handle empty iterator."""
        resources = iter([])
        result = list(select_essential_data(resources))
        assert len(result) == 0

    def test_returns_generator(self):
        """Should return a generator."""
        resources = iter([{"address": "test", "values": {"arn": "arn:aws:test"}}])
        result = select_essential_data(resources)

        assert hasattr(result, "__iter__")
        assert hasattr(result, "__next__")

    def test_skips_resource_without_address(self, caplog):
        """Should skip resources without 'address' field and log warning."""
        resources = iter([{"mode": "managed", "values": {"arn": "arn:aws:test", "id": "123"}}])

        with caplog.at_level(logging.WARNING):
            result = list(select_essential_data(resources))

        assert len(result) == 0
        assert "Skipping resource without 'address' field" in caplog.text

    def test_skips_resource_without_arn(self, caplog):
        """Should skip resources without 'arn' field in values and log warning."""
        resources = iter([{"address": "aws_instance.web", "values": {"id": "i-123"}}])

        with caplog.at_level(logging.WARNING):
            result = list(select_essential_data(resources))

        assert len(result) == 0
        assert "Skipping resource aws_instance.web without 'arn' field" in caplog.text

    def test_skips_resource_without_values(self, caplog):
        """Should skip resources without 'values' field and log warning."""
        resources = iter([{"address": "aws_instance.web", "mode": "managed"}])

        with caplog.at_level(logging.WARNING):
            result = list(select_essential_data(resources))

        assert len(result) == 0
        assert "Skipping resource aws_instance.web without 'arn' field" in caplog.text

    def test_processes_valid_and_skips_invalid_resources(self, caplog):
        """Should process valid resources and skip invalid ones."""
        resources = iter(
            [
                {"address": "aws_instance.valid1", "values": {"arn": "arn:aws:ec2:1", "id": "i-1"}},
                {"values": {"arn": "arn:aws:ec2:2", "id": "i-2"}},  # Missing address
                {"address": "aws_instance.no_arn", "values": {"id": "i-3"}},  # Missing arn
                {"address": "aws_instance.valid2", "values": {"arn": "arn:aws:ec2:4", "id": "i-4"}},
            ]
        )

        with caplog.at_level(logging.WARNING):
            result = list(select_essential_data(resources))

        # Should only return the 2 valid resources
        assert len(result) == 2
        assert result[0]["address"] == "aws_instance.valid1"
        assert result[1]["address"] == "aws_instance.valid2"

        # Should have logged 2 warnings
        assert caplog.text.count("Skipping resource") == 2


class TestProcessShowOutput:
    """Unit tests for process_show_output function."""

    def test_is_real_function(self):
        """Verify we're testing the real function, not a mock."""
        assert inspect.isfunction(process_show_output)
        assert not isinstance(process_show_output, Mock)

    def test_processes_show_output(self):
        """Should unnest and select essential data from show output."""
        show_output = {
            "values": {
                "root_module": {
                    "resources": [
                        {
                            "address": "aws_instance.web",
                            "mode": "managed",
                            "type": "aws_instance",
                            "name": "web",
                            "provider_name": "aws",
                            "schema_version": 0,
                            "values": {
                                "id": "i-123",
                                "arn": "arn:aws:ec2:::instance/i-123",
                                "instance_type": "t2.micro",
                                "extra_field": "ignored",
                            },
                        }
                    ]
                }
            }
        }

        result = list(process_show_output(show_output))

        assert len(result) == 1
        assert result[0]["address"] == "aws_instance.web"
        assert result[0]["mode"] == "managed"
        assert result[0]["values"]["id"] == "i-123"
        assert result[0]["values"]["arn"] == "arn:aws:ec2:::instance/i-123"
        assert "extra_field" not in result[0]["values"]

    def test_returns_iterator(self):
        """Should return an iterator."""
        show_output = {"values": {"root_module": {"resources": []}}}
        result = process_show_output(show_output)

        assert hasattr(result, "__iter__")


class TestProcessRepository:
    """Integration tests for process_repository function."""

    def test_is_real_function(self):
        """Verify we're testing the real function, not a mock."""
        assert inspect.isfunction(process_repository)
        assert not isinstance(process_repository, Mock)

    @patch("cxm_iac_crawler.main.send_data_to_cxm")
    @patch("cxm_iac_crawler.main.compute_terraform_show")
    @patch("cxm_iac_crawler.main.find_terraform_lock_files")
    def test_processes_single_entrypoint(self, mock_find, mock_compute, mock_send, tmp_path):
        """Should process single terraform configuration."""
        # Setup: single lock file found
        lock_file = tmp_path / "terraform" / ".terraform.lock.hcl"
        lock_file.parent.mkdir()
        lock_file.touch()
        mock_find.return_value = iter([lock_file])

        # Setup: terraform show returns resources
        mock_compute.return_value = {
            "values": {
                "root_module": {"resources": [{"address": "aws_instance.web", "values": {"id": "i-123", "arn": "arn:aws:ec2:::i-123"}}]}
            }
        }

        process_repository(tmp_path, repository_url=TEST_REPOSITORY_URL, platform=TEST_PLATFORM)

        # Verify flow
        mock_find.assert_called_once_with(tmp_path)
        mock_compute.assert_called_once_with(lock_file.parent)
        assert mock_send.call_count == 1

        # Verify resources sent
        sent_resources = list(mock_send.call_args.args[0])
        assert len(sent_resources) == 1
        assert sent_resources[0]["address"] == "aws_instance.web"
        # Verify repository_url is passed
        assert mock_send.call_args.kwargs.get("repository_url") == TEST_REPOSITORY_URL

    @patch("cxm_iac_crawler.main.send_data_to_cxm")
    @patch("cxm_iac_crawler.main.compute_terraform_show")
    @patch("cxm_iac_crawler.main.find_terraform_lock_files")
    def test_processes_with_repository_url(self, mock_find, mock_compute, mock_send, tmp_path):
        """Should pass repository_url to send_data_to_cxm when provided."""
        # Setup: single lock file found
        lock_file = tmp_path / "terraform" / ".terraform.lock.hcl"
        lock_file.parent.mkdir()
        lock_file.touch()
        mock_find.return_value = iter([lock_file])

        # Setup: terraform show returns resources
        mock_compute.return_value = {
            "values": {
                "root_module": {"resources": [{"address": "aws_instance.web", "values": {"id": "i-123", "arn": "arn:aws:ec2:::i-123"}}]}
            }
        }

        repository_url = "https://github.com/example/terraform-config"
        process_repository(tmp_path, repository_url=repository_url, platform=TEST_PLATFORM)

        # Verify flow
        mock_find.assert_called_once_with(tmp_path)
        mock_compute.assert_called_once_with(lock_file.parent)
        assert mock_send.call_count == 1

        # Verify repository_url is passed
        assert mock_send.call_args.kwargs["repository_url"] == repository_url

    @patch("cxm_iac_crawler.main.send_data_to_cxm")
    @patch("cxm_iac_crawler.main.compute_terraform_show")
    @patch("cxm_iac_crawler.main.find_terraform_lock_files")
    def test_processes_multiple_entrypoints(self, mock_find, mock_compute, mock_send, tmp_path):
        """Should process multiple terraform configurations."""
        # Setup: three lock files
        lock_files = [tmp_path / f"module{i}" / ".terraform.lock.hcl" for i in range(3)]
        for lf in lock_files:
            lf.parent.mkdir()
            lf.touch()
        mock_find.return_value = iter(lock_files)

        # Setup: each returns a resource
        mock_compute.side_effect = [
            {"values": {"root_module": {"resources": [{"address": f"aws_instance.web{i}", "values": {"id": f"i-{i}"}}]}}} for i in range(3)
        ]

        process_repository(tmp_path, repository_url=TEST_REPOSITORY_URL, platform=TEST_PLATFORM)

        assert mock_compute.call_count == 3
        assert mock_send.call_count == 3

    @patch("cxm_iac_crawler.main.send_data_to_cxm")
    @patch("cxm_iac_crawler.main.compute_terraform_show")
    @patch("cxm_iac_crawler.main.find_terraform_lock_files")
    def test_handles_no_entrypoints(self, mock_find, mock_compute, mock_send, tmp_path):
        """Should handle repository with no terraform configurations."""
        mock_find.return_value = iter([])

        process_repository(tmp_path, repository_url=TEST_REPOSITORY_URL, platform=TEST_PLATFORM)

        mock_compute.assert_not_called()
        mock_send.assert_not_called()

    @patch("cxm_iac_crawler.main.send_data_to_cxm")
    @patch("cxm_iac_crawler.main.compute_terraform_show")
    @patch("cxm_iac_crawler.main.find_terraform_lock_files")
    def test_continues_on_non_fatal_errors(self, mock_find, mock_compute, mock_send, tmp_path):
        """Should continue processing after non-terraform errors."""
        # Setup: three lock files
        lock_files = [tmp_path / f"module{i}" / ".terraform.lock.hcl" for i in range(3)]
        for lf in lock_files:
            lf.parent.mkdir()
            lf.touch()
        mock_find.return_value = iter(lock_files)

        # First succeeds, second fails with generic error, third succeeds
        mock_compute.side_effect = [
            {"values": {"root_module": {"resources": [{"address": "aws_instance.web1", "values": {"id": "i-1"}}]}}},
            ValueError("Some processing error"),
            {"values": {"root_module": {"resources": [{"address": "aws_instance.web3", "values": {"id": "i-3"}}]}}},
        ]

        # Should not raise, but continue processing
        process_repository(tmp_path, repository_url=TEST_REPOSITORY_URL, platform=TEST_PLATFORM)

        assert mock_compute.call_count == 3
        # Only 2 successful sends (1st and 3rd)
        assert mock_send.call_count == 2

    @patch("cxm_iac_crawler.main.send_data_to_cxm")
    @patch("cxm_iac_crawler.main.compute_terraform_show")
    @patch("cxm_iac_crawler.main.find_terraform_lock_files")
    def test_aborts_on_terraform_failure(self, mock_find, mock_compute, mock_send, tmp_path):
        """Should abort scan when terraform show fails."""
        # Setup: single lock file
        lock_file = tmp_path / ".terraform.lock.hcl"
        lock_file.touch()
        mock_find.return_value = iter([lock_file])

        # Terraform command fails
        mock_compute.side_effect = subprocess.CalledProcessError(returncode=1, cmd=["terraform", "show", "-json"])

        with pytest.raises(subprocess.CalledProcessError):
            process_repository(tmp_path, repository_url=TEST_REPOSITORY_URL, platform=TEST_PLATFORM)

        mock_send.assert_not_called()

    @patch("cxm_iac_crawler.main.send_data_to_cxm")
    @patch("cxm_iac_crawler.main.compute_terraform_show")
    @patch("cxm_iac_crawler.main.find_terraform_lock_files")
    def test_integration_full_workflow(self, mock_find, mock_compute, mock_send, tmp_path):
        """Should handle complete end-to-end workflow."""
        # Create realistic directory structure
        modules = ["dev", "staging", "prod"]
        lock_files = []
        for module in modules:
            module_path = tmp_path / module
            module_path.mkdir()
            lock_file = module_path / ".terraform.lock.hcl"
            lock_file.touch()
            lock_files.append(lock_file)

        mock_find.return_value = iter(lock_files)

        # Return realistic terraform show output
        def make_show_output(env):
            return {
                "values": {
                    "root_module": {
                        "resources": [
                            {
                                "address": f"aws_instance.web_{env}",
                                "mode": "managed",
                                "type": "aws_instance",
                                "name": f"web_{env}",
                                "provider_name": "aws",
                                "schema_version": 0,
                                "values": {
                                    "id": f"i-{env}",
                                    "arn": f"arn:aws:ec2:us-east-1:123456789012:instance/i-{env}",
                                    "tags": {"Environment": env},
                                    "instance_type": "t2.micro",
                                },
                            }
                        ]
                    }
                }
            }

        mock_compute.side_effect = [make_show_output(env) for env in modules]

        process_repository(tmp_path, repository_url=TEST_REPOSITORY_URL, platform=TEST_PLATFORM)

        # Verify all modules processed
        assert mock_compute.call_count == 3
        assert mock_send.call_count == 3

        # Verify data sent for each environment
        for idx, env in enumerate(modules):
            sent_resources = list(mock_send.call_args_list[idx].args[0])
            assert len(sent_resources) == 1
            assert sent_resources[0]["address"] == f"aws_instance.web_{env}"
            assert sent_resources[0]["values"]["arn"] == f"arn:aws:ec2:us-east-1:123456789012:instance/i-{env}"
            assert sent_resources[0]["values"]["tags"] == {"Environment": env}
            # Check that only essential values fields are included
            assert "instance_type" not in sent_resources[0]["values"]
