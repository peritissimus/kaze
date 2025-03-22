# Changelog

## [0.9.0] - 2025-03-22

### Features

- add sequential processing option and improve database handling (84509d0)
- add chunks command to CLI interface (90ae5ff)
- add CodeChunk model for representing code chunks (869aafe)
- add chunk management functionality for code embedding (a2bb43f)
- add CLI commands for managing and querying code chunks (322b155)
- add language parsers for Python, Java, JavaScript, TypeScript, and base parser (8966629)

### Bug Fixes

- resolve database error handling and improve chunk queries (9c800b3)

### Code Refactoring

- cleanup and improve code style across multiple files (ed6e658)

### Chores

- update .gitignore to exclude coder.sh file (b06210a)

### Other

- refactor(commands, core, languages): remove unused imports and delete Java parser (ebfa75a)

## [0.8.2] - 2025-03-22

### Code Refactoring

- update config file handling and improve changelog entry logic (6bbfd4e)

## [0.8.1] - 2025-03-22

### Other

- fix(scripts/release.py): simplify release creation command (e0d3540)

### Other

- fix(scripts/release.py): simplify release creation command (e0d3540)

## [0.8.0] - 2025-03-22

### Features

- add authorization check before creating releases (18891b3)

## [0.7.0] - 2025-03-22

### Features

- add script for creating GitHub releases with versioning and build artifacts (e4c1de2)

### Other

- chore(changelog, pyproject): update changelog and bump version to 0.6.0 (7472b71)

### Other

- chore(changelog, pyproject): update changelog and bump version to 0.6.0 (7472b71)

## [0.6.0] - 2025-03-22

### Features

- add usage instructions and command options for Kaze tool (b000a99)
- add default value for human_output flag in query command (c6fa696)
- release version 0.5.0 with new log output feature (8855809)
- add new log output to info command (a3cb49d)
- update changelog for version 0.4.0 release (84382b7)
- add verify option for embedding model in create command (4b4c73f)
- version bump to 0.2.0 with changelog and updates (c01ff58)
- add script for automated versioning and changelog generation (600f17d)
- add .gitignore, update Python version, and modify file size limit (f3deae7)
- add command-line interface for managing embeddings (a826dd3)
- initialize kaze project with core structure and CLI commands (d42fad9)

### Bug Fixes

- add tree-sitter dependencies for improved parsing capabilities (3ddd899)
- correct docstring formatting for list_collections function (794d211)

### Code Refactoring

- encapsulate collection listing functionality (f6c5abf)

## [0.5.0] - 2025-03-13

### Features

- add new log output to info command (a3cb49d)
- update changelog for version 0.4.0 release (84382b7)

## [0.4.0] - 2025-03-12

### Features

- add verify option for embedding model in create command (4b4c73f)
- version bump to 0.2.0 with changelog and updates (c01ff58)

### Bug Fixes

- correct docstring formatting for list_collections function (794d211)

### Code Refactoring

- encapsulate collection listing functionality (f6c5abf)

## [0.2.0] - 2025-03-10

### Features

- add script for automated versioning and changelog generation (600f17d)
- add .gitignore, update Python version, and modify file size limit (f3deae7)
- add command-line interface for managing embeddings (a826dd3)
- initialize kaze project with core structure and CLI commands (d42fad9)

All notable changes to this project will be documented in this file.

