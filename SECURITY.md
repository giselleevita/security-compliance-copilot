# Security Policy

## Reporting

Do not open public issues for suspected vulnerabilities. Report them privately through GitHub's security advisory feature.

## Dependency Audit

Run:

```bash
pip-audit -r requirements.txt --progress-spinner off
```

The current dependency graph includes `torch` through `sentence-transformers`. As of June 11, 2026, `pip-audit` reports `CVE-2025-3000` for the latest available Torch release and lists no fixed version. CI records this explicit exception while continuing to fail on any other known vulnerability.

Chroma is temporarily pinned to the unaffected `0.6.x` line because GitHub advisory `GHSA-f4j7-r4q5-qw2c` affects all available `1.x` releases through `1.5.9`. Upgrade only after a patched release is available and the full retrieval test suite passes.
