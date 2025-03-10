#!/usr/bin/env python
"""
Script to automate versioning and changelog generation based on conventional commits.
This script can be run to automatically update version numbers in pyproject.toml
and generate a CHANGELOG.md file based on git commit history.
"""

import os
import re
import subprocess
import sys
from datetime import datetime
from typing import List, Optional, Tuple


class ConventionalVersioning:
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.pyproject_path = os.path.join(project_root, "pyproject.toml")
        self.changelog_path = os.path.join(project_root, "CHANGELOG.md")

    def get_current_version(self) -> str:
        """Extract the current version from pyproject.toml."""
        with open(self.pyproject_path, "r") as f:
            content = f.read()
            match = re.search(r'version\s*=\s*"([^"]+)"', content)
            if match:
                return match.group(1)
            else:
                raise ValueError("Version not found in pyproject.toml")

    def update_version(self, new_version: str) -> None:
        """Update the version in pyproject.toml."""
        with open(self.pyproject_path, "r") as f:
            content = f.read()

        updated_content = re.sub(
            r'(version\s*=\s*)"([^"]+)"', rf'\1"{new_version}"', content
        )

        with open(self.pyproject_path, "w") as f:
            f.write(updated_content)

        print(f"Updated version in pyproject.toml to {new_version}")

    def get_commit_history(self, since_tag: Optional[str] = None) -> List[str]:
        """Get the git commit history since the given tag."""
        cmd = ["git", "log", "--pretty=format:%s (%h)"]
        if since_tag:
            cmd.append(f"{since_tag}..HEAD")

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip().split("\n")

    def categorize_commits(self, commits: List[str]) -> dict:
        """Categorize commits based on conventional commit types."""
        categories = {
            "feat": [],
            "fix": [],
            "perf": [],
            "refactor": [],
            "docs": [],
            "style": [],
            "test": [],
            "chore": [],
            "ci": [],
            "build": [],
            "revert": [],
            "other": [],
        }

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

        # Create the new changelog entry
        new_entry = f"## [{new_version}] - {today}\n\n"

        # Add categorized commits
        category_titles = {
            "feat": "### Features",
            "fix": "### Bug Fixes",
            "perf": "### Performance Improvements",
            "refactor": "### Code Refactoring",
            "docs": "### Documentation",
            "style": "### Styles",
            "test": "### Tests",
            "chore": "### Chores",
            "ci": "### CI",
            "build": "### Build",
            "revert": "### Reverts",
        }

        for category, title in category_titles.items():
            if categorized_commits[category]:
                new_entry += f"{title}\n\n"
                for commit in categorized_commits[category]:
                    # Clean up the commit message for better readability
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

    def get_latest_tag(self) -> Optional[str]:
        """Get the latest tag from git."""
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"], capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None

    def tag_version(self, version: str) -> None:
        """Create a git tag for the new version."""
        subprocess.run(["git", "tag", f"v{version}"])
        print(f"Created git tag v{version}")

    def run(self, force_bump: Optional[str] = None) -> None:
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

        self.update_version(new_version)
        self.update_changelog(new_version, categorized_commits)
        self.tag_version(new_version)

        print("Versioning complete!")


if __name__ == "__main__":
    # Get the project root directory (adjust as needed)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    force_bump = None
    if len(sys.argv) > 1:
        if sys.argv[1] in ["major", "minor", "patch"]:
            force_bump = sys.argv[1]

    versioner = ConventionalVersioning(project_root)
    versioner.run(force_bump)
