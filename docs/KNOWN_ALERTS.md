# Known Vulnerability Advisories

## 1. Advisories Without Upstream Patches

The following 5 security advisories affecting project dependencies currently have no upstream patched version released (`first_patched_version: null`).

| Ecosystem | Package | Severity | Advisory ID | CVE | Summary | Status / Upstream Mitigation |
|---|---|---|---|---|---|---|
| npm | `extract-zip` | High | GHSA-7pqw-9j4j-h8q3 | CVE-2026-19693 | Arbitrary file writes through symlink archive entries | Transitive dependency of `@puppeteer/browsers` via `puppeteer` in `whatsapp-bridge`. No patched version exists upstream. Unused in production message processing paths. |
| npm | `extract-zip` | High | GHSA-jmr9-qjv8-65gv | CVE-2026-56876 | Unvalidated symlink path traversal | Transitive dependency of `@puppeteer/browsers` via `puppeteer` in `whatsapp-bridge`. No patched version exists upstream. Unused in production message processing paths. |
| pip | `torch` | Low | GHSA-x3gm-94wq-g975 | CVE-2025-2149 | Improper initialization via Quantized Sigmoid Module | Optional ML dependency quarantined to `requirements-ml.txt`. No patched version available. Not imported in base runtime. |
| pip | `torch` | Medium | GHSA-f4hp-rmr7-r7v8 | CVE-2025-2998 | Memory Consumption through pad_packed_sequence Function | Optional ML dependency quarantined to `requirements-ml.txt`. No patched version available. Not imported in base runtime. |
| pip | `torch` | Low | GHSA-c678-jfcj-6jmf | CVE-2025-2148 | Tuple Handler Vulnerable to Memory Corruption | Optional ML dependency quarantined to `requirements-ml.txt`. No patched version available. Not imported in base runtime. |

## 2. Patched upstream but blocked by compatibility

- **`langgraph`**: Advisory GHSA-x55p-8v6g-vcmg (Path Traversal in LangGraph Studio).
  - First patched upstream version: `1.0.10`.
  - Blocked by compatibility: `langgraph>=1.0.10` requires `langgraph-prebuilt>=1.0.8`, which strictly depends on `langchain-core>=1.0.0`. Upgrading breaks compatibility with the 0.3 line (`langchain-core==0.3.85`).

## 3. Quarantined Optional Dependencies (`requirements-ml.txt`)

`requirements-ml.txt` pins packages with known open alerts and is **OPTIONAL, UNSUPPORTED, and NOT RECOMMENDED for v0.1**. Base installations do not require or install it.

Highest `first_patched_version` per package from open alerts:
- **`torch`**: pinned `2.4.1`. Highest first patched version in open advisories: `2.13.0` (also `2.10.0`, `2.9.1`).
- **`transformers`**: pinned `4.44.2`. Highest first patched version in open advisories: `5.10.0` (also `5.5.0`, `4.53.0`).
- **`faster-whisper`**: pinned `1.0.3` (depends transitively on ctranslate2/av).
