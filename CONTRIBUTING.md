# Contributing to BTRFS RAID Manager

Thanks for your interest in contributing to BTRFS RAID Manager. This document gives a short guide to opening issues and submitting changes.

## Before you start

- Read the [README](README.md) to understand what this tool does and how it works.
- Check existing [issues](https://github.com/jaldertech/btrfs-raid-manager/issues) and [pull requests](https://github.com/jaldertech/btrfs-raid-manager/pulls) to avoid duplicates.

## Opening an issue

- **Bug reports:** Describe what you did, what you expected, and what happened. Include your environment (OS, kernel, Python version, BTRFS pool layout) and relevant config (redact secrets).
- **Feature ideas:** Explain the use case and how it fits with the project's goals (BTRFS RAID health management, capacity planning, scrub scheduling).
- **Questions:** Open an issue and use the "Question" label if you have it; otherwise a normal issue is fine.

## Submitting changes (pull requests)

1. **Fork the repo** and create a branch from `main` (e.g. `fix/thing` or `feature/thing`).
2. **Make your changes** in that branch. Keep the scope focused.
3. **Match existing style:** Python 3.9+, type hints where it helps, same logging and error-handling style as the rest of the codebase. No new runtime dependencies without discussion — this project deliberately uses only the Python standard library.
4. **Update docs** if you change behaviour or config: README, `config.yaml` comments, and/or docstrings.
5. **Test:** Run the test suite with `python3 -m unittest discover -s btrfs_raid_manager/tests -v`. Use `--dry-run` where relevant on a real pool.
6. **Open a PR** against `main` with a clear title and description of what changed and why. Reference any related issues.

## What we're looking for

- **Bug fixes** and **documentation** improvements are always welcome.
- **New features** (e.g. extra notification backends, new RAID profiles): open an issue first so we can align on design and scope.
- **Hardware reports:** If you test on a new drive configuration or hardware platform, we'd love to hear about it.

## Code of conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). Be respectful and constructive.

## Licence

By contributing, you agree that your contributions will be licenced under the same [MIT Licence](LICENCE) as the project.
