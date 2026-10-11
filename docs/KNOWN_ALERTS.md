# Known Vulnerability Advisories Without Upstream Patches

The following 5 security advisories affecting project dependencies currently have no upstream patched version released (`first_patched_version: null`).

| Ecosystem | Package | Severity | Advisory ID | CVE | Summary | Status / Upstream Mitigation |
|---|---|---|---|---|---|---|
| npm | `extract-zip` | High | GHSA-7pqw-9j4j-h8q3 | CVE-2026-19693 | Arbitrary file writes through symlink archive entries | Transitive dependency of `@puppeteer/browsers` via `puppeteer` in `whatsapp-bridge`. No patched version exists upstream. Unused in production message processing paths. |
| npm | `extract-zip` | High | GHSA-jmr9-qjv8-65gv | CVE-2026-56876 | Unvalidated symlink path traversal | Transitive dependency of `@puppeteer/browsers` via `puppeteer` in `whatsapp-bridge`. No patched version exists upstream. Unused in production message processing paths. |
| pip | `torch` | Low | GHSA-x3gm-94wq-g975 | CVE-2025-2149 | Improper initialization via Quantized Sigmoid Module | Optional ML dependency quarantined to `requirements-ml.txt`. No patched version available. Not imported in base runtime. |
| pip | `torch` | Medium | GHSA-f4hp-rmr7-r7v8 | CVE-2025-2998 | Memory Consumption through pad_packed_sequence Function | Optional ML dependency quarantined to `requirements-ml.txt`. No patched version available. Not imported in base runtime. |
| pip | `torch` | Low | GHSA-c678-jfcj-6jmf | CVE-2025-2148 | Tuple Handler Vulnerable to Memory Corruption | Optional ML dependency quarantined to `requirements-ml.txt`. No patched version available. Not imported in base runtime. |
