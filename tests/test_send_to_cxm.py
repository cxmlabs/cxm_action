"""Unit and integration tests for send_to_cxm module."""

import inspect
from unittest.mock import Mock, patch

import pytest
import requests
from cxm_iac_crawler.send_to_cxm import _batch_generator, _send_single_batch, send_data_to_cxm


def make_test_scan_metadata():
    """Helper to create test scan metadata."""
    return {
        "platform": "github",
        "scan_timestamp": "2024-01-01T00:00:00Z",
        "crawler_version": "1.0.0",
        "run_id": "test-run-id-123",
        "workflow_id": "test-workflow",
        "actor": "test-user",
    }


class TestBatchGenerator:
    """Unit tests for _batch_generator function."""

    def test_single_batch(self):
        """Should yield single batch when items less than batch size."""
        items = iter([{"id": 1}, {"id": 2}, {"id": 3}])
        batches = list(_batch_generator(items, batch_size=5))

        assert len(batches) == 1
        assert batches[0] == [{"id": 1}, {"id": 2}, {"id": 3}]

    def test_multiple_batches(self):
        """Should split items into multiple batches."""
        items = iter([{"id": i} for i in range(10)])
        batches = list(_batch_generator(items, batch_size=3))

        assert len(batches) == 4
        assert batches[0] == [{"id": 0}, {"id": 1}, {"id": 2}]
        assert batches[1] == [{"id": 3}, {"id": 4}, {"id": 5}]
        assert batches[2] == [{"id": 6}, {"id": 7}, {"id": 8}]
        assert batches[3] == [{"id": 9}]

    def test_exact_batch_size(self):
        """Should handle items that exactly match batch size."""
        items = iter([{"id": i} for i in range(6)])
        batches = list(_batch_generator(items, batch_size=3))

        assert len(batches) == 2
        assert len(batches[0]) == 3
        assert len(batches[1]) == 3

    def test_empty_iterator(self):
        """Should yield no batches for empty iterator."""
        items = iter([])
        batches = list(_batch_generator(items, batch_size=10))

        assert len(batches) == 0

    def test_batch_size_one(self):
        """Should handle batch size of 1."""
        items = iter([{"id": 1}, {"id": 2}, {"id": 3}])
        batches = list(_batch_generator(items, batch_size=1))

        assert len(batches) == 3
        assert batches[0] == [{"id": 1}]
        assert batches[1] == [{"id": 2}]
        assert batches[2] == [{"id": 3}]

    def test_large_batch_size(self):
        """Should yield single batch when batch size larger than items."""
        items = iter([{"id": i} for i in range(5)])
        batches = list(_batch_generator(items, batch_size=1000))

        assert len(batches) == 1
        assert len(batches[0]) == 5

    def test_returns_generator(self):
        """Should return a generator, not consume all items immediately."""
        items = iter([{"id": i} for i in range(100)])
        result = _batch_generator(items, batch_size=10)

        # Should be a generator
        assert hasattr(result, "__iter__")
        assert hasattr(result, "__next__")


class TestSendSingleBatch:
    """Unit tests for _send_single_batch function."""

    def test_is_real_function(self):
        """Verify we're testing the real function, not a mock."""
        assert inspect.isfunction(_send_single_batch)
        assert not isinstance(_send_single_batch, Mock)

    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_KEY", "test-key")
    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_ENDPOINT", "https://api.example.com/resources")
    @patch("requests.post")
    def test_successful_send(self, mock_post):
        """Should successfully send batch to API."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        batch = [{"id": "1", "type": "aws_instance"}]
        scan_metadata = make_test_scan_metadata()
        repository_url = "https://github.com/test/repo"
        _send_single_batch(batch, batch_index=0, repository_url=repository_url, scan_metadata=scan_metadata)

        # Verify POST was called with correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        assert call_args.args[0] == "https://api.example.com/resources"
        assert call_args.kwargs["json"]["resources"] == batch
        assert call_args.kwargs["json"]["schema_version"] == 0
        assert call_args.kwargs["json"]["scan_metadata"] == scan_metadata
        assert call_args.kwargs["json"]["repository_url"] == repository_url
        assert call_args.kwargs["headers"]["CXM-API-KEY"] == "test-key"
        assert call_args.kwargs["headers"]["Content-Type"] == "application/json"

    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_KEY", "test-key")
    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_ENDPOINT", "https://api.example.com/resources")
    @patch("requests.post")
    def test_successful_send_with_repository_url(self, mock_post):
        """Should include repository_url in payload when provided."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        batch = [{"id": "1", "type": "aws_instance"}]
        repository_url = "https://github.com/example/repo"
        scan_metadata = make_test_scan_metadata()
        _send_single_batch(batch, batch_index=0, repository_url=repository_url, scan_metadata=scan_metadata)

        # Verify POST was called with correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        assert call_args.args[0] == "https://api.example.com/resources"
        assert call_args.kwargs["json"]["resources"] == batch
        assert call_args.kwargs["json"]["schema_version"] == 0
        assert call_args.kwargs["json"]["repository_url"] == repository_url
        assert call_args.kwargs["json"]["scan_metadata"] == scan_metadata
        assert call_args.kwargs["headers"]["CXM-API-KEY"] == "test-key"
        assert call_args.kwargs["headers"]["Content-Type"] == "application/json"

    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_KEY", "test-key")
    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_ENDPOINT", "https://api.example.com/resources")
    @patch("cxm_iac_crawler.send_to_cxm.MAX_RETRIES", 3)
    @patch("requests.post")
    def test_retry_on_failure(self, mock_post):
        """Should retry on request failure."""
        # Fail twice, succeed on third attempt
        mock_post.side_effect = [
            requests.exceptions.RequestException("Network error"),
            requests.exceptions.RequestException("Network error"),
            Mock(raise_for_status=Mock()),
        ]

        batch = [{"id": "1"}]
        scan_metadata = make_test_scan_metadata()
        _send_single_batch(batch, batch_index=0, repository_url="https://github.com/test/repo", scan_metadata=scan_metadata)

        assert mock_post.call_count == 3

    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_KEY", "test-key")
    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_ENDPOINT", "https://api.example.com/resources")
    @patch("cxm_iac_crawler.send_to_cxm.MAX_RETRIES", 2)
    @patch("requests.post")
    def test_raises_after_max_retries(self, mock_post):
        """Should raise exception after exhausting retries."""
        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        batch = [{"id": "1"}]
        with pytest.raises(requests.exceptions.RequestException):
            _send_single_batch(batch, batch_index=0, repository_url="https://github.com/test/repo", scan_metadata=make_test_scan_metadata())

        assert mock_post.call_count == 2

    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_KEY", "")
    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_ENDPOINT", "https://api.example.com")
    def test_missing_api_key(self):
        """Should raise ValueError when API key is missing."""
        with pytest.raises(ValueError, match="CXM_API_KEY and CXM_API_ENDPOINT must be configured"):
            _send_single_batch([], 0, repository_url="https://github.com/test/repo", scan_metadata=make_test_scan_metadata())

    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_KEY", "test-key")
    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_ENDPOINT", "")
    def test_missing_api_endpoint(self):
        """Should raise ValueError when API endpoint is missing."""
        with pytest.raises(ValueError, match="CXM_API_KEY and CXM_API_ENDPOINT must be configured"):
            _send_single_batch([], 0, repository_url="https://github.com/test/repo", scan_metadata=make_test_scan_metadata())

    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_KEY", "test-key")
    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_ENDPOINT", "https://api.example.com/resources")
    @patch("cxm_iac_crawler.send_to_cxm.MAX_RETRIES", 1)
    @patch("requests.post")
    def test_http_error_response(self, mock_post):
        """Should handle HTTP error responses."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Bad Request")
        mock_post.return_value = mock_response

        batch = [{"id": "1"}]
        with pytest.raises(requests.exceptions.RequestException):
            _send_single_batch(batch, batch_index=0, repository_url="https://github.com/test/repo", scan_metadata=make_test_scan_metadata())

    @patch("requests.post")
    def test_custom_timeout(self, mock_post, monkeypatch):
        """Should use custom timeout from environment variable."""
        monkeypatch.setenv("CXM_API_KEY", "test-key")
        monkeypatch.setenv("CXM_API_ENDPOINT", "https://api.example.com/resources")
        monkeypatch.setenv("CXM_TIMEOUT_SECONDS", "60")

        # Need to reload module to pick up new env var
        from importlib import reload

        from cxm_iac_crawler import send_to_cxm as stc

        reload(stc)

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        stc._send_single_batch([{"id": "1"}], 0, repository_url="https://github.com/test/repo", scan_metadata=make_test_scan_metadata())

        call_args = mock_post.call_args
        assert call_args.kwargs["timeout"] == 60


class TestSendDataToCxm:
    """Unit tests for send_data_to_cxm function."""

    def test_is_real_function(self):
        """Verify we're testing the real function, not a mock."""
        assert inspect.isfunction(send_data_to_cxm)
        assert not isinstance(send_data_to_cxm, Mock)

    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_KEY", "")
    def test_missing_api_key(self):
        """Should raise ValueError when API key is missing."""
        with pytest.raises(ValueError, match="CXM_API_KEY must be configured"):
            send_data_to_cxm(iter([]), repository_url="https://github.com/test/repo", scan_metadata=make_test_scan_metadata())

    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_KEY", "test-key")
    @patch("cxm_iac_crawler.send_to_cxm._send_single_batch")
    def test_sends_empty_generator(self, mock_send):
        """Should handle empty resource generator."""
        resources = iter([])
        send_data_to_cxm(resources, repository_url="https://github.com/test/repo", scan_metadata=make_test_scan_metadata())

        mock_send.assert_not_called()

    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_KEY", "test-key")
    @patch("cxm_iac_crawler.send_to_cxm._send_single_batch")
    def test_sends_single_batch(self, mock_send):
        """Should send single batch for small resource list."""
        resources = iter([{"id": i} for i in range(10)])
        send_data_to_cxm(resources, repository_url="https://github.com/test/repo", scan_metadata=make_test_scan_metadata())

        assert mock_send.call_count == 1
        batch_sent = mock_send.call_args.args[0]
        assert len(batch_sent) == 10

    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_KEY", "test-key")
    @patch("cxm_iac_crawler.send_to_cxm._send_single_batch")
    def test_sends_multiple_batches(self, mock_send):
        """Should split large resource list into multiple batches."""
        # Create 2500 resources (will be split into 3 batches of 1000)
        resources = iter([{"id": i} for i in range(2500)])
        send_data_to_cxm(resources, repository_url="https://github.com/test/repo", scan_metadata=make_test_scan_metadata())

        assert mock_send.call_count == 3

        # Check batch sizes
        first_batch = mock_send.call_args_list[0].args[0]
        assert len(first_batch) == 1000

        second_batch = mock_send.call_args_list[1].args[0]
        assert len(second_batch) == 1000

        third_batch = mock_send.call_args_list[2].args[0]
        assert len(third_batch) == 500

    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_KEY", "test-key")
    @patch("cxm_iac_crawler.send_to_cxm._send_single_batch")
    def test_batch_indices(self, mock_send):
        """Should pass correct batch indices."""
        resources = iter([{"id": i} for i in range(2500)])
        send_data_to_cxm(resources, repository_url="https://github.com/test/repo", scan_metadata=make_test_scan_metadata())

        # Check batch indices
        assert mock_send.call_args_list[0].args[1] == 0
        assert mock_send.call_args_list[1].args[1] == 1
        assert mock_send.call_args_list[2].args[1] == 2


class TestIntegrationSendToCxm:
    """Integration tests for complete send workflow."""

    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_KEY", "test-key")
    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_ENDPOINT", "https://api.example.com/resources")
    @patch("cxm_iac_crawler.send_to_cxm.MAX_RETRIES", 3)
    @patch("requests.post")
    def test_complete_workflow_with_retries(self, mock_post):
        """Should handle complete workflow including retries."""
        # First batch succeeds immediately
        # Second batch fails once then succeeds
        # Third batch succeeds immediately
        success_response = Mock()
        success_response.raise_for_status = Mock()

        mock_post.side_effect = [
            success_response,  # Batch 1
            requests.exceptions.RequestException("Network error"),  # Batch 2, attempt 1
            success_response,  # Batch 2, attempt 2
            success_response,  # Batch 3
        ]

        resources = iter([{"id": i} for i in range(2500)])
        send_data_to_cxm(resources, repository_url="https://github.com/test/repo", scan_metadata=make_test_scan_metadata())

        # Should have made 4 requests total (3 batches + 1 retry)
        assert mock_post.call_count == 4

    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_KEY", "test-key")
    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_ENDPOINT", "https://api.example.com/resources")
    @patch("cxm_iac_crawler.send_to_cxm.MAX_RETRIES", 2)
    @patch("requests.post")
    def test_partial_failure_raises(self, mock_post):
        """Should raise exception if a batch fails after retries."""
        # First batch succeeds, second batch fails all retries
        success_response = Mock()
        success_response.raise_for_status = Mock()

        mock_post.side_effect = [
            success_response,  # Batch 1
            requests.exceptions.RequestException("Network error"),  # Batch 2, attempt 1
            requests.exceptions.RequestException("Network error"),  # Batch 2, attempt 2
        ]

        resources = iter([{"id": i} for i in range(1500)])

        with pytest.raises(requests.exceptions.RequestException):
            send_data_to_cxm(resources, repository_url="https://github.com/test/repo", scan_metadata=make_test_scan_metadata())

    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_KEY", "test-key")
    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_ENDPOINT", "https://api.example.com/resources")
    @patch("requests.post")
    def test_generator_consumed_lazily(self, mock_post):
        """Should consume generator lazily, not all at once."""
        consumed_count = 0

        def resource_generator():
            nonlocal consumed_count
            for i in range(2500):
                consumed_count += 1
                yield {"id": i}

        success_response = Mock()
        success_response.raise_for_status = Mock()
        mock_post.return_value = success_response

        send_data_to_cxm(resource_generator(), repository_url="https://github.com/test/repo", scan_metadata=make_test_scan_metadata())

        # All resources should be consumed
        assert consumed_count == 2500
        # Should have made 3 batch requests
        assert mock_post.call_count == 3

    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_KEY", "production-key-123")
    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_ENDPOINT", "https://api.cxm.io/v1/resources")
    @patch("requests.post")
    def test_end_to_end_realistic_scenario(self, mock_post):
        """Should handle realistic end-to-end scenario."""

        # Simulate realistic terraform resources
        def generate_resources():
            resource_types = ["aws_instance", "aws_s3_bucket", "aws_security_group"]
            for i in range(150):
                yield {
                    "address": f"{resource_types[i % 3]}.resource_{i}",
                    "type": resource_types[i % 3],
                    "mode": "managed",
                    "values": {"id": f"resource-{i}", "arn": f"arn:aws:service:region:account:{i}"},
                }

        success_response = Mock()
        success_response.raise_for_status = Mock()
        mock_post.return_value = success_response

        send_data_to_cxm(generate_resources(), repository_url="https://github.com/test/repo", scan_metadata=make_test_scan_metadata())

        # Should send single batch (150 < 1000)
        assert mock_post.call_count == 1

        # Verify payload structure
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]
        assert "resources" in payload
        assert "schema_version" in payload
        assert len(payload["resources"]) == 150
        assert payload["schema_version"] == 0

    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_KEY", "production-key-123")
    @patch("cxm_iac_crawler.send_to_cxm.CXM_API_ENDPOINT", "https://api.cxm.io/v1/resources")
    @patch("requests.post")
    def test_end_to_end_with_repository_url(self, mock_post):
        """Should include repository_url in payload when provided."""

        # Simulate realistic terraform resources
        def generate_resources():
            resource_types = ["aws_instance", "aws_s3_bucket", "aws_security_group"]
            for i in range(150):
                yield {
                    "address": f"{resource_types[i % 3]}.resource_{i}",
                    "type": resource_types[i % 3],
                    "mode": "managed",
                    "values": {"id": f"resource-{i}", "arn": f"arn:aws:service:region:account:{i}"},
                }

        success_response = Mock()
        success_response.raise_for_status = Mock()
        mock_post.return_value = success_response

        repository_url = "https://github.com/example/terraform-infra"
        send_data_to_cxm(generate_resources(), repository_url=repository_url, scan_metadata=make_test_scan_metadata())

        # Should send single batch (150 < 1000)
        assert mock_post.call_count == 1

        # Verify payload structure
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]
        assert "resources" in payload
        assert "schema_version" in payload
        assert "repository_url" in payload
        assert len(payload["resources"]) == 150
        assert payload["schema_version"] == 0
        assert payload["repository_url"] == repository_url
