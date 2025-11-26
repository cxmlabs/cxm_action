"""Unit tests for compute_terraform_show module."""

import json
import subprocess
from unittest.mock import patch

import pytest
from cxm_iac_crawler.compute_terraform_show import compute_terraform_show


class TestComputeTerraformShow:
    """Unit tests for compute_terraform_show function."""

    @patch("subprocess.run")
    def test_successful_execution(self, mock_run, tmp_path):
        """Should execute terraform show and return parsed JSON."""
        terraform_output = {
            "format_version": "1.0",
            "terraform_version": "1.5.0",
            "values": {"root_module": {"resources": []}},
        }

        # Mock returns different results for init and show
        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            if "init" in cmd:
                return subprocess.CompletedProcess(
                    args=cmd, returncode=0, stdout="", stderr=""
                )
            elif "show" in cmd:
                return subprocess.CompletedProcess(
                    args=cmd,
                    returncode=0,
                    stdout=json.dumps(terraform_output),
                    stderr="",
                )
            return subprocess.CompletedProcess(
                args=cmd, returncode=1, stdout="", stderr=""
            )

        mock_run.side_effect = mock_run_side_effect

        result = compute_terraform_show(tmp_path)

        assert result == terraform_output
        # Verify that show was called with correct parameters
        mock_run.assert_any_call(
            ["terraform", "show", "-json"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=300,
        )

    @patch("subprocess.run")
    def test_accepts_string_path(self, mock_run, tmp_path):
        """Should accept terraform_dir as string."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="{}", stderr=""
        )

        result = compute_terraform_show(str(tmp_path))

        assert result == {}
        assert mock_run.called

    @patch("subprocess.run")
    def test_accepts_pathlib_path(self, mock_run, tmp_path):
        """Should accept terraform_dir as Path object."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="{}", stderr=""
        )

        result = compute_terraform_show(tmp_path)

        assert result == {}
        assert mock_run.called

    def test_nonexistent_directory(self):
        """Should raise FileNotFoundError for nonexistent directory."""
        with pytest.raises(FileNotFoundError, match="Directory does not exist"):
            compute_terraform_show("/nonexistent/path")

    def test_path_is_file_not_directory(self, tmp_path):
        """Should raise NotADirectoryError if path is a file."""
        file_path = tmp_path / "file.txt"
        file_path.touch()

        with pytest.raises(NotADirectoryError, match="Path is not a directory"):
            compute_terraform_show(file_path)

    @patch("subprocess.run")
    def test_terraform_command_failure(self, mock_run, tmp_path):
        """Should raise CalledProcessError when terraform command fails."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["terraform", "show", "-json"],
            stderr="Error: No state file",
        )

        with pytest.raises(subprocess.CalledProcessError):
            compute_terraform_show(tmp_path)

    @patch("subprocess.run")
    def test_terraform_timeout(self, mock_run, tmp_path):
        """Should raise TimeoutExpired when terraform command times out."""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["terraform", "show", "-json"], timeout=300
        )

        with pytest.raises(subprocess.TimeoutExpired):
            compute_terraform_show(tmp_path)

    @patch("subprocess.run")
    def test_invalid_json_output(self, mock_run, tmp_path):
        """Should raise JSONDecodeError when terraform outputs invalid JSON."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="not valid json", stderr=""
        )

        with pytest.raises(json.JSONDecodeError):
            compute_terraform_show(tmp_path)

    @patch("subprocess.run")
    def test_empty_json_output(self, mock_run, tmp_path):
        """Should handle empty JSON object."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="{}", stderr=""
        )

        result = compute_terraform_show(tmp_path)

        assert result == {}

    @patch("subprocess.run")
    def test_uses_correct_timeout(self, mock_run, tmp_path, monkeypatch):
        """Should use TERRAFORM_SHOW_TIMEOUT environment variable."""
        monkeypatch.setenv("TERRAFORM_SHOW_TIMEOUT", "600")
        # Need to reload module to pick up new env var
        from importlib import reload

        from cxm_iac_crawler import compute_terraform_show as cts

        reload(cts)

        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="{}", stderr=""
        )

        cts.compute_terraform_show(tmp_path)

        # Check that timeout was passed correctly
        call_args = mock_run.call_args
        assert call_args.kwargs["timeout"] == 600

    @patch("subprocess.run")
    def test_capture_output_configuration(self, mock_run, tmp_path):
        """Should configure subprocess to capture output properly."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="{}", stderr=""
        )

        compute_terraform_show(tmp_path)

        call_args = mock_run.call_args
        assert call_args.kwargs["capture_output"] is True
        assert call_args.kwargs["text"] is True
        assert call_args.kwargs["check"] is True

    @patch("subprocess.run")
    def test_working_directory_set(self, mock_run, tmp_path):
        """Should set correct working directory for terraform command."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="{}", stderr=""
        )

        compute_terraform_show(tmp_path)

        call_args = mock_run.call_args
        assert call_args.kwargs["cwd"] == tmp_path

    @patch("subprocess.run")
    def test_terraform_show_json_flag(self, mock_run, tmp_path):
        """Should use -json flag for terraform show command."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="{}", stderr=""
        )

        compute_terraform_show(tmp_path)

        call_args = mock_run.call_args
        assert call_args.args[0] == ["terraform", "show", "-json"]
