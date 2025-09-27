#!/usr/bin/env python3
"""
Vendor script for downloading and copying external library files.

This script checks for new versions of an external library and vendors
specific files into the current project.
"""

import argparse
import fnmatch
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
import yaml


class VendorManager:
    """Manages vendoring of external library files."""

    def __init__(self, config_path: str):
        """Initialize with configuration file."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.repo_info = self.config["vendor"]["repository"]
        self.files_to_vendor = self.config["vendor"].get("files", [])
        self.folders_to_vendor = self.config["vendor"].get("folders", [])
        self.destination = Path(self.config["vendor"]["destination"])

    def _load_config(self) -> Dict:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, "r") as f:
            return yaml.safe_load(f)

    def _get_latest_version(self) -> Tuple[str, str]:
        """Get the latest version information."""
        return self._get_latest_release()

    def _get_latest_release(self) -> Tuple[str, str]:
        """Get the latest release version and commit SHA."""
        url = f"https://api.github.com/repos/{self.repo_info['owner']}/{self.repo_info['repo']}/releases/latest"

        headers = {}
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        release_data = response.json()
        version = release_data["tag_name"]
        commit_sha = release_data["target_commitish"]

        return version, commit_sha

    def _get_current_version(self) -> Optional[str]:
        """Get the currently vendored version."""
        version_file = self.destination / ".vendor_version"
        if version_file.exists():
            with open(version_file, "r") as f:
                return f.read().strip()
        return None

    def _save_version_info(self, version: str, commit_sha: str):
        """Save version information to the destination directory."""
        self.destination.mkdir(parents=True, exist_ok=True)

        version_file = self.destination / ".vendor_version"
        with open(version_file, "w") as f:
            f.write(f"{version}\n")

        info_file = self.destination / ".vendor_info"
        info = {
            "version": version,
            "commit_sha": commit_sha,
            "vendored_at": datetime.now().isoformat(),
            "repository": f"{self.repo_info['owner']}/{self.repo_info['repo']}",
        }
        with open(info_file, "w") as f:
            json.dump(info, f, indent=2)

    def _clone_repository(self, commit_sha: str) -> Path:
        """Clone the repository to a temporary directory."""
        repo_url = (
            f"https://github.com/{self.repo_info['owner']}/{self.repo_info['repo']}.git"
        )

        temp_dir = tempfile.mkdtemp(prefix="vendor_")

        try:
            # Clone the repository
            subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, temp_dir],
                check=True,
                capture_output=True,
            )

            # Checkout specific commit
            subprocess.run(
                ["git", "checkout", commit_sha],
                cwd=temp_dir,
                check=True,
                capture_output=True,
            )

            return Path(temp_dir)
        except subprocess.CalledProcessError as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError(f"Failed to clone repository: {e}")

    def _vendor_folder(self, repo_path: Path, folder_config: Dict):
        """Vendor a folder with inclusion/exclusion patterns."""

        def _matches_pattern(file_path: str, patterns: List[str]) -> bool:
            """Check if a file path matches any of the given glob patterns."""
            if not patterns:
                return True

            for pattern in patterns:
                if fnmatch.fnmatch(file_path, pattern):
                    return True
            return False

        def _should_include_file(
            file_path: str, include_patterns: List[str], exclude_patterns: List[str]
        ) -> bool:
            """Determine if a file should be included based on include/exclude patterns."""
            # If no include patterns, include everything
            if not include_patterns:
                include_match = True
            else:
                include_match = _matches_pattern(file_path, include_patterns)

            # If no exclude patterns, exclude nothing
            if not exclude_patterns:
                exclude_match = False
            else:
                exclude_match = _matches_pattern(file_path, exclude_patterns)

            return include_match and not exclude_match

        folder_path = folder_config["path"]
        include_patterns = folder_config.get("include", [])
        exclude_patterns = folder_config.get("exclude", [])
        preserve_structure = folder_config.get("preserve_structure", True)

        src_folder = repo_path / folder_path

        if not src_folder.exists():
            print(f"Warning: Folder {folder_path} not found in repository")
            return

        if not src_folder.is_dir():
            print(f"Warning: {folder_path} is not a directory")
            return

        print(f"Vendoring folder: {folder_path}")

        # Create the folder as a subdirectory in the destination
        folder_name = Path(folder_path).name
        folder_destination = self.destination / folder_name

        # Walk through the folder recursively
        for root, dirs, files in os.walk(src_folder):
            root_path = Path(root)

            # Filter directories based on exclude patterns
            dirs[:] = [d for d in dirs if not _matches_pattern(d, exclude_patterns)]

            for file_name in files:
                file_path = root_path / file_name

                # Get relative path from the source folder
                rel_path = file_path.relative_to(src_folder)
                rel_path_str = str(rel_path)

                # Check if file should be included
                if not _should_include_file(
                    rel_path_str, include_patterns, exclude_patterns
                ):
                    continue

                # Determine destination path
                if preserve_structure:
                    dst_path = folder_destination / rel_path
                else:
                    # Flatten structure - just use filename
                    dst_path = folder_destination / file_name

                # Create destination directory if needed
                dst_path.parent.mkdir(parents=True, exist_ok=True)

                # Copy file
                shutil.copy2(file_path, dst_path)
                print(f"Vendored: {folder_path}/{rel_path_str} -> {dst_path}")

    def _vendor_files(self, repo_path: Path):
        """Copy specified files and folders from repository to destination."""
        self.destination.mkdir(parents=True, exist_ok=True)

        # Vendor individual files
        for file_path in self.files_to_vendor:
            src_path = repo_path / file_path
            dst_path = self.destination / Path(file_path).name

            if not src_path.exists():
                print(f"Warning: File {file_path} not found in repository")
                continue

            # Copy file
            shutil.copy2(src_path, dst_path)
            print(f"Vendored: {file_path} -> {dst_path}")

        # Vendor folders
        for folder_config in self.folders_to_vendor:
            self._vendor_folder(repo_path, folder_config)

    def check_and_update(self, force: bool = False) -> bool:
        """Check for updates and vendor files if needed."""
        print(
            f"Checking for updates to {self.repo_info['owner']}/{self.repo_info['repo']}"
        )

        try:
            version, commit_sha = self._get_latest_version()
            current_version = self._get_current_version()

            print(f"Latest version: {version} (commit: {commit_sha[:8]})")
            print(f"Current version: {current_version or 'None'}")

            if not force and current_version == version:
                print("No updates available")
                return False

            print(f"Updating to version {version}")

            # Clone repository
            repo_path = self._clone_repository(commit_sha)

            try:
                self._vendor_files(repo_path)
                self._save_version_info(version, commit_sha)
                print(f"Successfully vendored version {version}")
                return True

            finally:  # Clean up temporary directory
                shutil.rmtree(repo_path, ignore_errors=True)

        except Exception as e:
            print(f"Error during update: {e}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Vendor external library files")
    parser.add_argument(
        "--config",
        help="Path to configuration file",
        required=True,
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force update even if version hasn't changed",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check for updates, don't vendor files",
    )

    args = parser.parse_args()

    try:
        vendor_manager = VendorManager(args.config)

        if args.check_only:
            version, commit_sha = vendor_manager._get_latest_version()
            current_version = vendor_manager._get_current_version()
            print(f"Latest version: {version} (commit: {commit_sha[:8]})")
            print(f"Current version: {current_version or 'None'}")
            return 0

        updated = vendor_manager.check_and_update(args.force)
        # Always return 0 (success), but print the update status for the workflow
        if updated:
            print("VENDOR_UPDATED=true")
        else:
            print("VENDOR_UPDATED=false")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
