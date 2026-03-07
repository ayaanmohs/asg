---
name: Bug report
about: Report a bug or unexpected behaviour
title: ''
labels: bug
assignees: ''
---

## Describe the bug

A clear and concise description of what the bug is.

## To reproduce

Steps to reproduce the behaviour:

1. Run `asg ...`
2. With pool layout: ...
3. See error

## Expected behaviour

A clear and concise description of what you expected to happen.

## Logs

Paste any relevant output from `asg` or your cron log.

```
<paste logs here>
```

## Environment

- **OS:** [e.g. Debian Bookworm, Ubuntu 24.04]
- **Hardware:** [e.g. Raspberry Pi 5, Intel N100]
- **Kernel:** [output of `uname -r`]
- **Python:** [output of `python3 --version`]
- **btrfs-progs:** [output of `btrfs --version`]
- **Pool layout:** [output of `sudo btrfs filesystem show <mount>`]
- **RAID profile:** [e.g. RAID1, RAID1C3]

## Config

Paste your `config.yaml` (redact any webhook URLs or secrets).

```yaml
<paste config here>
```

## Additional context

Add any other context about the problem here.
