# Security Policy

## Supported Versions

Security updates are provided for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |
| < 1.0   | :x:                |

We recommend running the latest release.

## Reporting a Vulnerability

If you believe you've found a security vulnerability in BTRFS RAID Manager, please report it responsibly.

**Do not open a public issue** for security-sensitive bugs.

1. **Report privately:** Go to the [Security](https://github.com/jaldertech/btrfs-raid-manager/security) tab of this repository and click **Report a vulnerability** (or use **Advisories → New draft**). That creates a private security advisory visible only to maintainers and you.

2. **What to include:** Describe the issue, steps to reproduce, and impact. If you have a suggested fix, you can mention it.

3. **What to expect:**
   - We will acknowledge your report as soon as we can.
   - We will try to confirm or triage within a few days and keep you updated.
   - If we accept the report, we will work on a fix and coordinate disclosure (e.g. release + advisory). We are happy to credit you in the advisory unless you prefer to stay anonymous.
   - If we decline (e.g. out of scope or not a vulnerability), we will explain why.

4. **Scope:** BTRFS RAID Manager runs filesystem commands via `sudo`. Reports about privilege escalation, command injection, or unsafe path handling are in scope. General hardening ideas are welcome as discussions or issues.

Thank you for helping keep BTRFS RAID Manager and its users safe.
