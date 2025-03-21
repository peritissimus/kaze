#!/usr/bin/env python3
"""
Script to automate versioning and changelog generation based on conventional commits.
This script can be run to automatically update version numbers in pyproject.toml
and generate a CHANGELOG.md file based on git commit history.
"""

import argparse
import os
import re
import subprocess
from datetime import datetime
from typing import List, Optional

import toml  # pip install toml


class ConventionalVersioning:
    def __init__(self, project_root: str, config_file: str = "version.config.toml"):
        self.project_root = project_root
        self.config_path = os.path.join(project_root, config_file)
        self.config = self.load_config()
        self.pyproject_path = os.path.join(
            project_root, self.config.get("pyproject_path", "pyproject.toml")
        )
        self.changelog_path = os.path.join(
            project_root, self.config.get("changelog_path", "CHANGELOG.md")
        )
        self.commit_categories = self.config.get(
            "commit_categories",
            {
                "feat": "Features",
                "fix": "Bug Fixes",
                "perf": "Performance Improvements",
                "refactor": "Code Refactoring",
                "docs": "Documentation",
                "style": "Styles",
                "test": "Tests",
                "chore": "Chores",
                "ci": "CI",
                "build": "Build",
                "revert": "Reverts",
                "other": "Other",
            },
        )

    def load_config(self):
        """Load configuration from version.config.toml file."""
        try:
            with open(self.config_path, "r") as f:
                config = toml.load(f)
                print(f"Loaded configuration from {self.config_path}")
                return config
        except FileNotFoundError:
            print(f"Warning: {self.config_path} not found, using defaults.")
            return {}

    def get_current_version(self) -> str:
        """Extract the current version from pyproject.toml."""
        try:
            with open(self.pyproject_path, "r") as f:
                data = toml.load(f)
                return data["project"]["version"]
        except FileNotFoundError:
            raise FileNotFoundError(
                f"pyproject.toml not found at {self.pyproject_path}"
            )
        except KeyError:
            raise ValueError("Version not found in pyproject.toml")

    def update_version(self, new_version: str) -> None:
        """Update the version in pyproject.toml."""
        try:
            with open(self.pyproject_path, "r") as f:
                data = toml.load(f)

            data["project"]["version"] = new_version

            with open(self.pyproject_path, "w") as f:
                toml.dump(data, f)

            print(f"Updated version in pyproject.toml to {new_version}")

        except FileNotFoundError:
            raise FileNotFoundError(
                f"pyproject.toml not found at {self.pyproject_path}"
            )
        except Exception as e:
            raise Exception(f"Error updating pyproject.toml: {e}")

    def get_commit_history(self, since_tag: Optional[str] = None) -> List[str]:
        """Get the git commit history since the given tag."""
        cmd = ["git", "log", "--pretty=format:%s (%h)"]
        if since_tag:
            cmd.append(f"{since_tag}..HEAD")

        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=self.project_root
        )  # Important: set cwd
        if result.returncode != 0:
            print(f"Error running git log: {result.stderr}")
            return []  # or raise an exception

        return result.stdout.strip().split("\n")

    def categorize_commits(self, commits: List[str]) -> dict:
        """Categorize commits based on conventional commit types."""
        categories = {category: [] for category in self.commit_categories}
        categories["other"] = []

        for commit in commits:
            if not commit:
                continue

            match = re.match(r"^(\w+)(\([\w\-\.]+\))?!?:", commit)
            if match:
                commit_type = match.group(1)
                if commit_type in categories:
                    categories[commit_type].append(commit)
                else:
                    categories["other"].append(commit)
            else:
                categories["other"].append(commit)

        return categories

    def determine_bump_type(self, commits: List[str]) -> str:
        """Determine the type of version bump based on commit messages."""
        breaking_change = any(
            re.search(r"(BREAKING CHANGE:|!):", commit) for commit in commits
        )
        has_new_feature = any(
            re.match(r"^feat(\([\w\-\.]+\))?:", commit) for commit in commits
        )

        if breaking_change:
            return "major"
        elif has_new_feature:
            return "minor"
        else:
            return "patch"

    def bump_version(self, current_version: str, bump_type: str) -> str:
        """Bump the version number according to semver rules."""
        major, minor, patch = map(int, current_version.split("."))

        if bump_type == "major":
            return f"{major + 1}.0.0"
        elif bump_type == "minor":
            return f"{major}.{minor + 1}.0"
        elif bump_type == "patch":
            return f"{major}.{minor}.{patch + 1}"
        else:
            raise ValueError(f"Invalid bump type: {bump_type}")

    def update_changelog(self, new_version: str, categorized_commits: dict) -> None:
        """Update the CHANGELOG.md file with the new version and commits."""
        today = datetime.now().strftime("%Y-%m-%d")

        # Read existing changelog or create a new one
        try:
            with open(self.changelog_path, "r") as f:
                content = f.read()
        except FileNotFoundError:
            content = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n"

        # Check if this version entry already exists in the changelog
        version_header = f"## [{new_version}]"
        if version_header in content:
            print(f"Version {new_version} already exists in changelog, updating it")
            # Remove the existing entry for this version
            start_idx = content.find(version_header)
            next_header_idx = content.find("## [", start_idx + len(version_header))

            if next_header_idx != -1:
                # Remove until the next version header
                content = content[:start_idx] + content[next_header_idx:]
            else:
                # This is the last entry, remove until the end
                content = content[:start_idx]

            # Ensure we have proper spacing after removing the entry
            if not content.endswith("\n\n"):
                content = content.rstrip("\n") + "\n\n"

        # Create the new changelog entry
        new_entry = f"{version_header} - {today}\n\n"

        # Track which commits have been added to avoid duplicates
        processed_commits = set()

        # Add categorized commits
        for category, title in self.commit_categories.items():
            if categorized_commits[category]:
                new_entry += f"### {title}\n\n"
                for commit in categorized_commits[category]:
                    # Extract commit hash to use for deduplication
                    commit_hash = commit.split("(")[-1].rstrip(")")

                    # Skip if already processed
                    if commit_hash in processed_commits:
                        continue
                    processed_commits.add(commit_hash)

                    # Clean up the commit message for better readability
                    cleaned_commit = re.sub(r"^(\w+)(\([\w\-\.]+\))?!?:\s*", "", commit)
                    new_entry += f"- {cleaned_commit}\n"
                new_entry += "\n"

        # Process "other" category if there are any remaining commits
        other_commits = [
            c
            for c in categorized_commits["other"]
            if c.split("(")[-1].rstrip(")") not in processed_commits
        ]

        if other_commits:
            new_entry += "### Other\n\n"
            for commit in other_commits:
                commit_hash = commit.split("(")[-1].rstrip(")")
                processed_commits.add(commit_hash)

                cleaned_commit = re.sub(r"^(\w+)(\([\w\-\.]+\))?!?:\s*", "", commit)
                new_entry += f"- {cleaned_commit}\n"
            new_entry += "\n"

        # Insert the new entry after the header
        content_parts = content.split("\n\n", 1)
        if len(content_parts) > 1:
            updated_content = content_parts[0] + "\n\n" + new_entry + content_parts[1]
        else:
            updated_content = content + new_entry

        with open(self.changelog_path, "w") as f:
            f.write(updated_content)

        print(f"Updated CHANGELOG.md with version {new_version}")

    def commit_changes(self, version: str) -> bool:
        """Commit the version and changelog changes to git."""
        try:
            # Stage the changed files
            subprocess.run(
                ["git", "add", self.pyproject_path, self.changelog_path],
                check=True,
                cwd=self.project_root,
            )

            # Commit with the conventional commit message
            subprocess.run(
                ["git", "commit", "-m", f"chore: release {version} [skip ci]"],
                check=True,
                cwd=self.project_root,
            )

            print(f"Committed changes for version {version}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error committing changes: {e}")
            return False

    def get_latest_tag(self) -> Optional[str]:
        """Get the latest tag from git."""
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None

    def tag_version(self, version: str) -> bool:
        """Create a git tag for the new version."""
        try:
            # Check if tag already exists
            tag = f"v{version}"
            check_tag = subprocess.run(
                ["git", "tag", "-l", tag],
                check=True,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                text=True,
            )

            if tag in check_tag.stdout:
                print(f"Warning: Tag {tag} already exists!")

                # Ask if the tag should be deleted and recreated
                confirm = input(
                    f"Would you like to delete and recreate the tag {tag}? (y/N): "
                )
                if confirm.lower() != "y":
                    print("Skipping tag creation")
                    return False

                # Delete the existing tag
                subprocess.run(
                    ["git", "tag", "-d", tag], check=True, cwd=self.project_root
                )
                print(f"Deleted existing tag {tag}")

            # Create the tag
            subprocess.run(
                ["git", "tag", "-a", tag, "-m", f"Release {version}"],
                check=True,
                cwd=self.project_root,
            )
            print(f"Created annotated git tag {tag}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error creating git tag: {e}")
            return False

    def run(self, force_bump: Optional[str] = None, dry_run: bool = False) -> None:
        """Run the versioning process."""
        current_version = self.get_current_version()
        print(f"Current version: {current_version}")

        latest_tag = self.get_latest_tag()
        print(f"Latest tag: {latest_tag or 'None'}")

        commits = self.get_commit_history(latest_tag)
        if not commits or commits[0] == "":
            print("No new commits since last tag. Nothing to do.")
            return

        categorized_commits = self.categorize_commits(commits)

        if force_bump:
            bump_type = force_bump
        else:
            bump_type = self.determine_bump_type(commits)

        print(f"Determined bump type: {bump_type}")

        new_version = self.bump_version(current_version, bump_type)
        print(f"New version: {new_version}")

        if not dry_run:
            self.update_version(new_version)
            self.update_changelog(new_version, categorized_commits)

            # Commit changes before tagging
            if self.commit_changes(new_version):
                tag_created = self.tag_version(new_version)
                if not tag_created:
                    print("Skipping tag creation")
            else:
                print("Skipping tag creation due to commit failure")
        else:
            print("Dry run: No changes will be written.")

        print("Versioning complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Automate versioning and changelog generation."
    )
    parser.add_argument(
        "--force-bump",
        choices=["major", "minor", "patch"],
        help="Force a specific type of version bump.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without modifying files or creating tags.",
    )
    args = parser.parse_args()

    # Get the project root directory (adjust as needed)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    versioner = ConventionalVersioning(project_root)
    versioner.run(args.force_bump, args.dry_run)
