#!/usr/bin/env python3
"""
Script to create a GitHub release for the kaze project using UV.
This script:
1. Updates version using the versioning script
2. Builds the package using UV
3. Creates a GitHub release with the build artifacts
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, List


def check_requirements():
    """Check if required tools are installed."""
    requirements = ["git", "uv", "gh"]
    missing = []

    for req in requirements:
        try:
            subprocess.run(
                [req, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        except FileNotFoundError:
            missing.append(req)

    if missing:
        print(f"Error: Missing required tools: {', '.join(missing)}")
        print("Please install them and try again.")
        return False

    return True


def check_authorization() -> bool:
    """
    Check if the current user is authorized to create releases.
    Returns True if authorized, False otherwise.
    """
    # List of authorized GitHub usernames
    AUTHORIZED_USERS = ["peritissimus"]

    try:
        # Check Git username
        git_user_result = subprocess.run(
            ["git", "config", "user.name"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if git_user_result.returncode != 0:
            print("Error: Could not determine Git username.")
            return False

        git_username = git_user_result.stdout.strip()

        # Check GitHub username
        gh_user_result = subprocess.run(
            ["gh", "api", "user"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if gh_user_result.returncode != 0:
            print(
                "Error: Could not verify GitHub authentication. Make sure you're logged in with 'gh auth login'."
            )
            return False

        import json

        gh_user_data = json.loads(gh_user_result.stdout)
        gh_username = gh_user_data.get("login")

        if gh_username not in AUTHORIZED_USERS:
            print(
                f"Error: GitHub user '{gh_username}' is not authorized to create releases."
            )
            print(f"Authorized users: {', '.join(AUTHORIZED_USERS)}")
            return False

        # Optional: Check if commits are signed
        signed_check = subprocess.run(
            ["git", "log", "-1", "--show-signature"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if "gpg: Signature made" not in signed_check.stdout:
            print("Warning: Latest commit is not signed with a GPG key.")
            # You could make this a hard requirement by returning False here

        print(
            f"Authorization check passed: User '{gh_username}' is authorized to create releases."
        )
        return True

    except Exception as e:
        print(f"Error checking authorization: {e}")
        return False


def run_versioning(
    project_root: str, force_bump: Optional[str] = None
) -> Optional[str]:
    """Run the versioning script and return the new version number."""
    version_script = os.path.join(project_root, "scripts", "version.py")

    cmd = [sys.executable, version_script]
    if force_bump:
        cmd.extend(["--force-bump", force_bump])

    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if result.returncode != 0:
            print(f"Error running versioning script: {result.stderr}")
            return None

        # Extract the new version from the output
        for line in result.stdout.splitlines():
            if line.startswith("New version:"):
                return line.split(":", 1)[1].strip()

        print("Could not determine new version from versioning script output")
        return None
    except Exception as e:
        print(f"Error executing versioning script: {e}")
        return None


def build_with_uv(project_root: str, version: str) -> Optional[List[str]]:
    """Build the package using UV and return the paths to the built artifacts."""
    try:
        # Create a build directory
        build_dir = os.path.join(project_root, "dist")
        os.makedirs(build_dir, exist_ok=True)

        # Build the package using UV
        subprocess.run(
            ["uv", "build", "--wheel", "--sdist"], cwd=project_root, check=True
        )

        # Find the built wheel
        wheels = list(Path(build_dir).glob(f"*{version}*.whl"))
        sdists = list(Path(build_dir).glob(f"*{version}*.tar.gz"))

        if not wheels and not sdists:
            print("No build artifacts found")
            return None

        artifacts = []
        if wheels:
            artifacts.extend([str(wheel) for wheel in wheels])
        if sdists:
            artifacts.extend([str(sdist) for sdist in sdists])

        return artifacts
    except subprocess.CalledProcessError as e:
        print(f"Error building package with UV: {e}")
        return None
    except Exception as e:
        print(f"Error during build process: {e}")
        return None


def create_github_release(
    project_root: str, version: str, artifacts: List[str]
) -> bool:
    """Create a GitHub release using the gh CLI. Returns True if successful."""
    try:
        tag = f"v{version}"

        # Get the changelog content for this version
        changelog_path = os.path.join(project_root, "CHANGELOG.md")
        release_notes = extract_release_notes(changelog_path, version)

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp:
            temp.write(release_notes)
            notes_file = temp.name

        # Create the release with artifacts in a single command
        # Format: gh release create <tag> [<files>...] --notes-file <file> --title <title>
        cmd = ["gh", "release", "create", tag]

        # Add artifacts to the command
        for artifact in artifacts:
            cmd.append(artifact)

        # Add release options
        cmd.extend(["--notes-file", notes_file, "--title", f"Release {tag}"])

        print(f"Running command: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        os.unlink(notes_file)  # Clean up temp file

        if result.returncode != 0:
            print(f"Error creating GitHub release: {result.stderr}")
            return False

        print(f"Successfully created GitHub release {tag}")
        print(result.stdout)
        return True
    except Exception as e:
        print(f"Error creating GitHub release: {e}")
        return False


def extract_release_notes(changelog_path: str, version: str) -> str:
    """Extract release notes for the given version from the changelog. Returns a string with the notes."""
    try:
        with open(changelog_path, "r") as f:
            content = f.read()

        # Find the section for this version
        version_header = f"## [{version}]"
        next_section = "## ["

        start_idx = content.find(version_header)
        if start_idx == -1:
            return f"Release {version}"

        start_idx = content.find("\n", start_idx) + 1
        end_idx = content.find(next_section, start_idx)

        if end_idx == -1:
            notes = content[start_idx:]
        else:
            notes = content[start_idx:end_idx]

        return notes.strip()
    except Exception as e:
        print(f"Error extracting release notes: {e}")
        return f"Release {version}"


def push_changes(project_root: str, tag: str) -> bool:
    """Push changes and tags to the remote repository."""
    try:
        # Push the commit
        print("Pushing commits to remote...")
        push_result = subprocess.run(
            ["git", "push"],
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        print(f"Push result: {push_result.stdout}")

        # Push the tag
        print(f"Pushing tag {tag} to remote...")
        tag_result = subprocess.run(
            ["git", "push", "origin", tag],
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        print(f"Tag push result: {tag_result.stdout}")

        # Verify the tag was pushed
        verify_result = subprocess.run(
            ["git", "ls-remote", "--tags", "origin", tag],
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if tag in verify_result.stdout:
            print(f"Verified tag {tag} exists on remote")
        else:
            print(f"Warning: Could not verify tag {tag} on remote")
            print("Output:", verify_result.stdout)
            print("Error:", verify_result.stderr)

        print("Successfully pushed changes and tags to remote")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error pushing changes: {e}")
        print(
            f"Standard error: {e.stderr if hasattr(e, 'stderr') else 'No stderr available'}"
        )
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Create a GitHub release for the kaze project"
    )
    parser.add_argument(
        "--force-bump",
        choices=["major", "minor", "patch"],
        help="Force a specific type of version bump",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without creating actual release",
    )
    parser.add_argument(
        "--skip-push",
        action="store_true",
        help="Skip pushing changes to the remote repository",
    )

    args = parser.parse_args()

    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Check required tools
    if not check_requirements():
        sys.exit(1)

    # Check authorization
    if not check_authorization():
        print("Error: You are not authorized to create releases.")
        sys.exit(1)

    # Run versioning
    new_version = run_versioning(project_root, args.force_bump)
    if not new_version:
        sys.exit(1)

    print(f"Updated version to {new_version}")

    # Push changes if not skipped
    if not args.skip_push:
        if not push_changes(project_root, f"v{new_version}"):
            sys.exit(1)

    # Build the package
    artifacts = build_with_uv(project_root, new_version)
    if not artifacts:
        sys.exit(1)

    print(f"Built package artifacts: {artifacts}")

    # Create GitHub release
    if not args.dry_run:
        if not create_github_release(project_root, new_version, artifacts):
            sys.exit(1)

        print(f"Successfully created GitHub release v{new_version}")
    else:
        print(f"Dry run: Would create GitHub release v{new_version}")

    print("Release process completed successfully!")


if __name__ == "__main__":
    main()
