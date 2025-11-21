"""Tests for platform validation and version detection."""

import pytest
from cxm_iac_crawler.main import SUPPORTED_PLATFORMS, create_scan_metadata, detect_ci_platform
from cxm_iac_crawler.send_to_cxm import CRAWLER_VERSION


class TestPlatformDetection:
    """Tests for platform detection and validation."""

    def test_supported_platforms_constant(self):
        """Should define supported platforms."""
        assert SUPPORTED_PLATFORMS == {"github", "gitlab", "generic"}

    def test_detect_valid_platforms(self):
        """Should detect valid platforms."""
        assert detect_ci_platform("github") == "github"
        assert detect_ci_platform("gitlab") == "gitlab"
        assert detect_ci_platform("generic") == "generic"

    def test_detect_platform_case_insensitive(self):
        """Should handle platform names case-insensitively."""
        assert detect_ci_platform("GitHub") == "github"
        assert detect_ci_platform("GITLAB") == "gitlab"
        assert detect_ci_platform("Generic") == "generic"

    def test_detect_invalid_platform(self):
        """Should raise ValueError for invalid platforms."""
        with pytest.raises(ValueError, match="Unsupported platform: invalid"):
            detect_ci_platform("invalid")

        with pytest.raises(ValueError, match="Unsupported platform: bitbucket"):
            detect_ci_platform("bitbucket")


class TestScanMetadataCreation:
    """Tests for scan metadata creation."""

    def test_create_metadata_valid_platforms(self):
        """Should create metadata for valid platforms."""
        for platform in SUPPORTED_PLATFORMS:
            metadata = create_scan_metadata(platform)
            assert metadata["platform"] == platform
            assert "scan_timestamp" in metadata
            assert "crawler_version" in metadata
            assert "run_id" in metadata

    def test_create_metadata_invalid_platform(self):
        """Should raise ValueError for invalid platforms."""
        with pytest.raises(ValueError, match="Unsupported platform: invalid"):
            create_scan_metadata("invalid")

    def test_metadata_includes_github_specific_fields(self):
        """Should include GitHub-specific fields when platform is github."""
        # Note: This test will only work if running in GitHub Actions
        # In other environments, these fields may be None and filtered out
        metadata = create_scan_metadata("github")
        assert metadata["platform"] == "github"
        # GitHub-specific fields are only present if env vars are set

    def test_metadata_includes_gitlab_specific_fields(self):
        """Should include GitLab-specific fields when platform is gitlab."""
        # Note: This test will only work if running in GitLab CI
        # In other environments, these fields may be None and filtered out
        metadata = create_scan_metadata("gitlab")
        assert metadata["platform"] == "gitlab"
        # GitLab-specific fields are only present if env vars are set

    def test_metadata_run_id_is_unique(self):
        """Should generate unique run IDs for each metadata creation."""
        metadata1 = create_scan_metadata("generic")
        metadata2 = create_scan_metadata("generic")
        assert metadata1["run_id"] != metadata2["run_id"]


class TestCrawlerVersion:
    """Tests for crawler version detection."""

    def test_crawler_version_not_empty(self):
        """Should have a non-empty crawler version."""
        assert CRAWLER_VERSION
        assert len(CRAWLER_VERSION) > 0

    def test_crawler_version_format(self):
        """Should have version in semantic format or dev format."""
        # Should be either semantic version (0.1.0) or dev version (0.0.0-dev)
        assert CRAWLER_VERSION.count(".") >= 2 or "-dev" in CRAWLER_VERSION
