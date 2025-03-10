import os
import subprocess
import fnmatch


def get_file_list(project_dir, include_pattern=None, exclude_pattern=None):
    """
    Returns a list of files to process based on git repository, .gitignore file, and include/exclude patterns.
    """

    file_list = []
    print(f"getting file list with {project_dir}")

    if os.path.exists(os.path.join(project_dir, ".gitignore")) and os.path.isdir(
        os.path.join(project_dir, ".git")
    ):
        # Use git to list files (respects .gitignore automatically)
        print(
            "[blue]📋 Found [yellow].gitignore[/yellow] in git repository - will respect exclusion patterns[/blue]"
        )
        try:
            process = subprocess.Popen(
                ["git", "ls-files"],
                cwd=project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = process.communicate()
            files_from_git = stdout.decode("utf-8").splitlines()

            process = subprocess.Popen(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = process.communicate()
            files_from_git_others = stdout.decode("utf-8").splitlines()

            file_list = files_from_git + files_from_git_others

        except Exception as e:
            print(f"[yellow]⚠️ Error using git: {e}[/yellow]")
            return []

    else:
        # Use find command with basic exclusions
        print("[yellow]⚠️ No .gitignore found - using basic exclusions[/yellow]")
        exclude_patterns = [
            ".git",
            ".kaze",
            "node_modules",
            ".DS_Store",
            "build",
            "dist",
            "venv",
            "__pycache__",
            ".*cache",
        ]
        for root, dirs, files in os.walk(project_dir):
            dirs[:] = [
                d
                for d in dirs
                if not any(fnmatch.fnmatch(d, pattern) for pattern in exclude_patterns)
            ]
            for file in files:
                file_list.append(os.path.join(root, file))

    if include_pattern:
        print(
            f"[blue]🔍 Adding files matching pattern: [yellow]{include_pattern}[/yellow][/blue]"
        )
        additional_files = []
        for root, _, files in os.walk(project_dir):
            for file in files:
                if fnmatch.fnmatch(file, include_pattern):
                    additional_files.append(os.path.join(root, file))
        file_list.extend(additional_files)

    # Filter the list for processable files
    processable_files = []
    for file in file_list:
        if should_process_file(file):
            processable_files.append(file)

    return processable_files


def should_process_file(file_path, max_file_size_kb=8):
    """
    Checks if a file should be processed based on size and type.
    """
    if not os.path.isfile(file_path):
        return False

    if not os.access(file_path, os.R_OK):
        return False

    file_size_kb = os.path.getsize(file_path) / 1024
    if file_size_kb > max_file_size_kb:
        return False

    try:
        with open(file_path, "r", errors="ignore") as f:
            try:
                f.read(1)
                is_text_file = True
            except UnicodeDecodeError:
                is_text_file = False
    except Exception as e:
        print(f"Error determining if the file {file_path} is a text file, excluding")
        return False

    if not is_text_file:
        extension = os.path.splitext(file_path)[1].lower()
        text_extensions = [
            ".txt",
            ".md",
            ".js",
            ".py",
            ".html",
            ".css",
            ".json",
            ".yaml",
            ".yml",
            ".xml",
            ".csv",
            ".sh",
            ".bash",
            ".conf",
            ".cfg",
            ".ini",
            ".rs",
            ".go",
            ".java",
            ".c",
            ".cpp",
            ".h",
            ".hpp",
            ".jsx",
            ".tsx",
            ".vue",
            ".rb",
            ".php",
            ".sql",
            ".swift",
            ".kt",
            ".scala",
            ".ts",
        ]
        if extension not in text_extensions:
            return False

    return True


def get_file_size(file_path):
    """returns the size of the file in human readable format"""

    file_size = os.path.getsize(file_path)
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(file_size, 1024)))
    p = math.pow(1024, i)
    s = round(file_size / p, 2)
    return f"{s} {size_name[i]}"
