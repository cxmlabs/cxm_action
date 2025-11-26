"""Unit and integration tests for CLI module."""

import logging
from unittest.mock import patch

import pytest
from cxm_iac_crawler.cli import main


class TestMain:
    """Unit tests for main function."""

    @patch("cxm_iac_crawler.cli.process_repository")
    def test_successful_execution(self, mock_process, tmp_path):
        """Should execute successfully with valid repository."""
        with patch("sys.argv", ["cxm-iac-crawler", str(tmp_path)]):
            exit_code = main()

        assert exit_code == 0
        mock_process.assert_called_once()
        # Verify path was resolved
        call_args = mock_process.call_args.args[0]
        assert call_args == tmp_path.resolve()
        # Verify repository_url defaults to None
        assert mock_process.call_args.kwargs.get("repository_url") == "unknown"

    @patch("cxm_iac_crawler.cli.process_repository")
    def test_repository_url_argument(self, mock_process, tmp_path):
        """Should pass repository URL to process_repository when provided."""
        repository_url = "https://github.com/example/terraform-repo"
        with patch(
            "sys.argv",
            ["cxm-iac-crawler", "--repository-url", repository_url, str(tmp_path)],
        ):
            exit_code = main()

        assert exit_code == 0
        mock_process.assert_called_once()
        # Verify repository_url was passed
        assert mock_process.call_args.kwargs["repository_url"] == repository_url

    @patch("logging.basicConfig")
    @patch("cxm_iac_crawler.cli.process_repository")
    def test_verbose_flag(self, mock_process, mock_logging, tmp_path):
        """Should enable verbose logging with -v flag."""
        with patch("sys.argv", ["cxm-iac-crawler", str(tmp_path), "-v"]):
            exit_code = main()

        assert exit_code == 0
        # Check that DEBUG level was configured
        call_kwargs = mock_logging.call_args.kwargs
        assert call_kwargs["level"] == logging.DEBUG

    @patch("logging.basicConfig")
    @patch("cxm_iac_crawler.cli.process_repository")
    def test_verbose_long_flag(self, mock_process, mock_logging, tmp_path):
        """Should enable verbose logging with --verbose flag."""
        with patch("sys.argv", ["cxm-iac-crawler", str(tmp_path), "--verbose"]):
            exit_code = main()

        assert exit_code == 0
        # Check that DEBUG level was configured
        call_kwargs = mock_logging.call_args.kwargs
        assert call_kwargs["level"] == logging.DEBUG

    def test_nonexistent_path(self):
        """Should return error code for nonexistent path."""
        with patch("sys.argv", ["cxm-iac-crawler", "/nonexistent/path"]):
            exit_code = main()

        assert exit_code == 1

    def test_path_is_file_not_directory(self, tmp_path):
        """Should return error code if path is a file."""
        file_path = tmp_path / "file.txt"
        file_path.touch()

        with patch("sys.argv", ["cxm-iac-crawler", str(file_path)]):
            exit_code = main()

        assert exit_code == 1

    @patch("cxm_iac_crawler.cli.process_repository")
    def test_keyboard_interrupt(self, mock_process, tmp_path):
        """Should handle KeyboardInterrupt gracefully."""
        mock_process.side_effect = KeyboardInterrupt()

        with patch("sys.argv", ["cxm-iac-crawler", str(tmp_path)]):
            exit_code = main()

        assert exit_code == 130

    @patch("cxm_iac_crawler.cli.process_repository")
    def test_generic_exception(self, mock_process, tmp_path):
        """Should return error code on exceptions."""
        mock_process.side_effect = RuntimeError("Something went wrong")

        with patch("sys.argv", ["cxm-iac-crawler", str(tmp_path)]):
            exit_code = main()

        assert exit_code == 1

    @patch("cxm_iac_crawler.cli.process_repository")
    def test_resolves_relative_paths(self, mock_process, tmp_path):
        """Should resolve relative paths to absolute paths."""
        # Create a subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        with patch("sys.argv", ["cxm-iac-crawler", str(subdir)]):
            exit_code = main()

        assert exit_code == 0
        # Verify absolute path was used
        call_args = mock_process.call_args.args[0]
        assert call_args.is_absolute()


class TestCLIIntegration:
    """Integration tests for complete CLI workflow."""

    @patch("cxm_iac_crawler.cli.process_repository")
    def test_complete_cli_workflow(self, mock_process, tmp_path):
        """Should handle complete CLI workflow from argument parsing to execution."""
        # Create realistic directory structure
        terraform_dir = tmp_path / "terraform"
        terraform_dir.mkdir()

        with patch("sys.argv", ["cxm-iac-crawler", str(terraform_dir), "-v"]):
            exit_code = main()

        assert exit_code == 0
        mock_process.assert_called_once()

        # Verify correct path was passed
        call_args = mock_process.call_args.args[0]
        assert call_args == terraform_dir.resolve()

    def test_help_output(self):
        """Should display help message."""
        with patch("sys.argv", ["cxm-iac-crawler", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Help exits with 0
            assert exc_info.value.code == 0

    @patch("cxm_iac_crawler.cli.process_repository")
    def test_logging_output(self, mock_process, tmp_path, caplog):
        """Should log appropriate messages during execution."""
        with (
            caplog.at_level(logging.INFO),
            patch("sys.argv", ["cxm-iac-crawler", str(tmp_path)]),
        ):
            main()

        # Check that log messages were generated
        assert "Starting IAC scan" in caplog.text
        assert "IAC scan completed successfully" in caplog.text

    @patch("cxm_iac_crawler.cli.process_repository")
    def test_error_logging(self, mock_process, tmp_path, caplog):
        """Should log errors appropriately."""
        mock_process.side_effect = RuntimeError("Test error")

        with (
            caplog.at_level(logging.ERROR),
            patch("sys.argv", ["cxm-iac-crawler", str(tmp_path)]),
        ):
            main()

        assert "Fatal error during IAC scan" in caplog.text

    @patch("logging.basicConfig")
    @patch("cxm_iac_crawler.cli.process_repository")
    def test_verbose_logging_output(self, mock_process, mock_logging, tmp_path):
        """Should configure DEBUG level logging in verbose mode."""
        with patch("sys.argv", ["cxm-iac-crawler", str(tmp_path), "-v"]):
            main()

        # Verify DEBUG level was configured
        call_kwargs = mock_logging.call_args.kwargs
        assert call_kwargs["level"] == logging.DEBUG

    def test_multiple_invocations(self, tmp_path):
        """Should handle multiple invocations independently."""
        with (
            patch("cxm_iac_crawler.cli.process_repository") as mock1,
            patch("sys.argv", ["cxm-iac-crawler", str(tmp_path)]),
        ):
            exit_code1 = main()

        with (
            patch("cxm_iac_crawler.cli.process_repository") as mock2,
            patch("sys.argv", ["cxm-iac-crawler", str(tmp_path)]),
        ):
            exit_code2 = main()

        assert exit_code1 == 0
        assert exit_code2 == 0
        assert mock1.call_count == 1
        assert mock2.call_count == 1

    @patch("cxm_iac_crawler.cli.process_repository")
    def test_path_validation_before_processing(self, mock_process, tmp_path):
        """Should validate path exists and is directory before processing."""
        # Test with valid directory
        with patch("sys.argv", ["cxm-iac-crawler", str(tmp_path)]):
            exit_code = main()
            assert exit_code == 0
            assert mock_process.called

        # Test with nonexistent path
        mock_process.reset_mock()
        with patch("sys.argv", ["cxm-iac-crawler", "/does/not/exist"]):
            exit_code = main()
            assert exit_code == 1
            assert not mock_process.called

    @patch("cxm_iac_crawler.cli.process_repository")
    def test_handles_path_with_spaces(self, mock_process, tmp_path):
        """Should handle paths with spaces correctly."""
        dir_with_spaces = tmp_path / "my terraform configs"
        dir_with_spaces.mkdir()

        with patch("sys.argv", ["cxm-iac-crawler", str(dir_with_spaces)]):
            exit_code = main()

        assert exit_code == 0
        mock_process.assert_called_once()

    @patch("cxm_iac_crawler.cli.process_repository")
    def test_handles_symlinked_directory(self, mock_process, tmp_path):
        """Should handle symlinked directories."""
        actual_dir = tmp_path / "actual"
        actual_dir.mkdir()

        link_dir = tmp_path / "link"
        link_dir.symlink_to(actual_dir)

        with patch("sys.argv", ["cxm-iac-crawler", str(link_dir)]):
            exit_code = main()

        assert exit_code == 0
        mock_process.assert_called_once()

    @patch("cxm_iac_crawler.cli.process_repository")
    def test_tf_entrypoints_comma_separated(self, mock_process, tmp_path):
        """Should parse comma-separated Terraform entrypoints."""
        terraform_dir1 = tmp_path / "terraform" / "prod"
        terraform_dir2 = tmp_path / "terraform" / "dev"
        terraform_dir1.mkdir(parents=True)
        terraform_dir2.mkdir(parents=True)

        entrypoints = "terraform/prod,terraform/dev"
        with patch(
            "sys.argv",
            ["cxm-iac-crawler", str(tmp_path), "--tf-entrypoints", entrypoints],
        ):
            exit_code = main()

        assert exit_code == 0
        mock_process.assert_called_once()
        # Check that paths parameter was passed with correct paths
        paths_arg = mock_process.call_args.kwargs.get("paths")
        assert paths_arg is not None
        assert len(paths_arg) == 2
        assert terraform_dir1 in paths_arg
        assert terraform_dir2 in paths_arg

    @patch("cxm_iac_crawler.cli.process_repository")
    def test_tf_entrypoints_newline_separated(self, mock_process, tmp_path):
        """Should parse newline-separated Terraform entrypoints."""
        terraform_dir1 = tmp_path / "terraform" / "prod"
        terraform_dir2 = tmp_path / "terraform" / "dev"
        terraform_dir1.mkdir(parents=True)
        terraform_dir2.mkdir(parents=True)

        entrypoints = "terraform/prod\nterraform/dev"
        with patch(
            "sys.argv",
            ["cxm-iac-crawler", str(tmp_path), "--tf-entrypoints", entrypoints],
        ):
            exit_code = main()

        assert exit_code == 0
        mock_process.assert_called_once()
        # Check that paths parameter was passed with correct paths
        paths_arg = mock_process.call_args.kwargs.get("paths")
        assert paths_arg is not None
        assert len(paths_arg) == 2
        assert terraform_dir1 in paths_arg
        assert terraform_dir2 in paths_arg

    @patch("cxm_iac_crawler.cli.process_repository")
    def test_tf_entrypoints_mixed_separators(self, mock_process, tmp_path):
        """Should parse Terraform entrypoints with mixed comma and newline separators."""
        terraform_dir1 = tmp_path / "terraform" / "prod"
        terraform_dir2 = tmp_path / "terraform" / "dev"
        terraform_dir3 = tmp_path / "terraform" / "staging"
        terraform_dir1.mkdir(parents=True)
        terraform_dir2.mkdir(parents=True)
        terraform_dir3.mkdir(parents=True)

        entrypoints = "terraform/prod,terraform/dev\nterraform/staging"
        with patch(
            "sys.argv",
            ["cxm-iac-crawler", str(tmp_path), "--tf-entrypoints", entrypoints],
        ):
            exit_code = main()

        assert exit_code == 0
        mock_process.assert_called_once()
        # Check that paths parameter was passed with correct paths
        paths_arg = mock_process.call_args.kwargs.get("paths")
        assert paths_arg is not None
        assert len(paths_arg) == 3
        assert terraform_dir1 in paths_arg
        assert terraform_dir2 in paths_arg
        assert terraform_dir3 in paths_arg

    @patch("cxm_iac_crawler.cli.process_repository")
    def test_tf_entrypoints_with_whitespace(self, mock_process, tmp_path):
        """Should handle Terraform entrypoints with extra whitespace."""
        terraform_dir1 = tmp_path / "terraform" / "prod"
        terraform_dir2 = tmp_path / "terraform" / "dev"
        terraform_dir1.mkdir(parents=True)
        terraform_dir2.mkdir(parents=True)

        entrypoints = "  terraform/prod  ,  terraform/dev  "
        with patch(
            "sys.argv",
            ["cxm-iac-crawler", str(tmp_path), "--tf-entrypoints", entrypoints],
        ):
            exit_code = main()

        assert exit_code == 0
        mock_process.assert_called_once()
        # Check that paths parameter was passed with correct paths (whitespace stripped)
        paths_arg = mock_process.call_args.kwargs.get("paths")
        assert paths_arg is not None
        assert len(paths_arg) == 2
        assert terraform_dir1 in paths_arg
        assert terraform_dir2 in paths_arg
