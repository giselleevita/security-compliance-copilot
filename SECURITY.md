# Security Policy

## Reporting

Do not open public issues for suspected vulnerabilities. Report them privately through GitHub's security advisory feature.

## Dependency Audit

Run:

```bash
pip-audit -r requirements.txt --progress-spinner off
```

The current dependency graph includes `torch` through `sentence-transformers` and uses Chroma for vector storage. As of June 11, 2026, `pip-audit` reports `CVE-2025-3000` for the latest available Torch release and `CVE-2026-45829` for the latest available Chroma release, with no fixed version listed for either package. CI records these explicit exceptions while continuing to fail on any other known vulnerability.
