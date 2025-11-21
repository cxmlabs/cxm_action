"""Unit tests for find_entrypoints module."""

from pathlib import Path

import pytest
from cxm_iac_crawler.find_entrypoints import find_terraform_lock_files


class TestFindTerraformLockFiles:
    """Unit tests for find_terraform_lock_files function."""

    def test_finds_lock_file_in_root(self, tmp_path):
        """Should find .terraform.lock.hcl in root directory."""
        lock_file = tmp_path / ".terraform.lock.hcl"
        lock_file.touch()

        results = list(find_terraform_lock_files(tmp_path))

        assert len(results) == 1
        assert results[0] == lock_file

    def test_finds_nested_lock_files(self, tmp_path):
        """Should find .terraform.lock.hcl files in subdirectories."""
        # Create nested structure
        (tmp_path / "module1").mkdir()
        (tmp_path / "module1" / ".terraform.lock.hcl").touch()

        (tmp_path / "module2" / "submodule").mkdir(parents=True)
        (tmp_path / "module2" / "submodule" / ".terraform.lock.hcl").touch()

        results = list(find_terraform_lock_files(tmp_path))

        assert len(results) == 2
        paths = [r.relative_to(tmp_path) for r in results]
        assert Path("module1/.terraform.lock.hcl") in paths
        assert Path("module2/submodule/.terraform.lock.hcl") in paths

    def test_empty_directory(self, tmp_path):
        """Should return empty iterator for directory with no lock files."""
        results = list(find_terraform_lock_files(tmp_path))
        assert len(results) == 0

    def test_ignores_other_files(self, tmp_path):
        """Should only find .terraform.lock.hcl files."""
        # Create various files
        (tmp_path / "main.tf").touch()
        (tmp_path / "variables.tf").touch()
        (tmp_path / "terraform.tfstate").touch()
        (tmp_path / ".terraform.lock.hcl").touch()

        results = list(find_terraform_lock_files(tmp_path))

        assert len(results) == 1
        assert results[0].name == ".terraform.lock.hcl"

    def test_path_as_string(self, tmp_path):
        """Should accept path as string."""
        lock_file = tmp_path / ".terraform.lock.hcl"
        lock_file.touch()

        results = list(find_terraform_lock_files(str(tmp_path)))

        assert len(results) == 1
        assert results[0] == lock_file

    def test_path_as_pathlib(self, tmp_path):
        """Should accept path as Path object."""
        lock_file = tmp_path / ".terraform.lock.hcl"
        lock_file.touch()

        results = list(find_terraform_lock_files(tmp_path))

        assert len(results) == 1
        assert results[0] == lock_file

    def test_nonexistent_directory(self):
        """Should raise FileNotFoundError for nonexistent directory."""
        with pytest.raises(FileNotFoundError, match="Directory does not exist"):
            list(find_terraform_lock_files("/nonexistent/path"))

    def test_path_is_file_not_directory(self, tmp_path):
        """Should raise NotADirectoryError if path is a file."""
        file_path = tmp_path / "file.txt"
        file_path.touch()

        with pytest.raises(NotADirectoryError, match="Path is not a directory"):
            list(find_terraform_lock_files(file_path))

    def test_deeply_nested_structure(self, tmp_path):
        """Should find lock files at any depth."""
        deep_path = tmp_path / "a" / "b" / "c" / "d" / "e"
        deep_path.mkdir(parents=True)
        lock_file = deep_path / ".terraform.lock.hcl"
        lock_file.touch()

        results = list(find_terraform_lock_files(tmp_path))

        assert len(results) == 1
        assert results[0] == lock_file

    def test_multiple_lock_files_same_level(self, tmp_path):
        """Should find multiple lock files at the same directory level."""
        (tmp_path / "env1").mkdir()
        (tmp_path / "env1" / ".terraform.lock.hcl").touch()

        (tmp_path / "env2").mkdir()
        (tmp_path / "env2" / ".terraform.lock.hcl").touch()

        (tmp_path / "env3").mkdir()
        (tmp_path / "env3" / ".terraform.lock.hcl").touch()

        results = list(find_terraform_lock_files(tmp_path))

        assert len(results) == 3

    def test_returns_generator(self, tmp_path):
        """Should return a generator/iterator, not a list."""
        lock_file = tmp_path / ".terraform.lock.hcl"
        lock_file.touch()

        result = find_terraform_lock_files(tmp_path)

        # Check it's an iterator
        assert hasattr(result, "__iter__")
        assert hasattr(result, "__next__")

    def test_handles_symlinks(self, tmp_path):
        """Should find lock files in actual directories (symlinks are not followed by rglob by default)."""
        # Create actual directory with lock file
        actual_dir = tmp_path / "actual"
        actual_dir.mkdir()
        lock_file = actual_dir / ".terraform.lock.hcl"
        lock_file.touch()

        # Create symlink to the directory
        link_dir = tmp_path / "link"
        link_dir.symlink_to(actual_dir)

        results = list(find_terraform_lock_files(tmp_path))

        # Python's Path.rglob() does NOT follow symlinks by default
        # So we should only find the lock file in the actual directory, not via the symlink
        assert len(results) == 1, f"Expected 1 lock file (actual only, no symlink follow), found {len(results)}"

        # Verify the result is the actual file (not via symlink)
        assert results[0].name == ".terraform.lock.hcl"
        assert results[0].exists()
        assert results[0].parent.name == "actual"

        # Verify the symlink exists but wasn't followed
        assert link_dir.exists()
        assert link_dir.is_symlink()

    def test_finds_lock_files_in_hidden_directories(self, tmp_path):
        """Should find lock files even in hidden directories (directories starting with '.')."""
        # Create hidden directory with lock file
        hidden_dir = tmp_path / ".hidden"
        hidden_dir.mkdir()
        lock_file = hidden_dir / ".terraform.lock.hcl"
        lock_file.touch()

        results = list(find_terraform_lock_files(tmp_path))

        # Should find the lock file in the hidden directory
        assert len(results) == 1, f"Expected 1 lock file in hidden directory, found {len(results)}"
        assert results[0].name == ".terraform.lock.hcl"
        assert results[0].parent.name == ".hidden"
        assert results[0].exists()
