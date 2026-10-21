---
name: sec-certs-schema
description: Structure of sec-certs CC and FIPS 140 certificate objects (CCCertificate, FIPSCertificate), their keyword dicts and text artifacts, the local dataset layout, and this project's manufacturer/category normalization conventions. Use when writing or debugging code that iterates CCDataset/FIPSDataset, reads pdf_data keywords, crypto_library mentions, certificate text files, or unifies manufacturer names.
user-invocable: false
---

# sec-certs data model for this thesis

Library: `sec-certs` (crocs-muni, installed from git in the Docker image). Analysis runs in
JupyterLab inside the `sec-certs-analysis-jupyter` container; `./notebooks` is mounted at
`/home/jovyan/work`, so notebook-relative paths like `./datasets/...` and `src/...` resolve there.

## Loading

```python
from pathlib import Path
from sec_certs.dataset.cc import CCDataset
from sec_certs.dataset.fips import FIPSDataset

cc_dataset = CCDataset.from_json("./datasets/CC_dataset.json")      # ~6.8k certs, ~200 MB
cc_dataset.root_dir = Path("./datasets")                            # needed for txt/pdf paths
fips_dataset = FIPSDataset.from_json("./datasets/FIPS_dataset.json") # ~5.5k certs, ~140 MB
fips_dataset.root_dir = Path("./datasets")
```

- Never call `from_web()` casually: it re-downloads everything (the FIPS artifacts tarball is ~5 GB).
- `notebooks/datasets/` is gitignored raw data. Read it; do not modify it.
- Loading takes a while. If a kernel already holds `cc_dataset` / `fips_dataset`, reuse them.
- Iterating a dataset yields certificate objects: `for cert in cc_dataset: ...`.
- For quick structure checks without sec-certs, the JSON can be read directly: top-level keys
  `_type, state, timestamp, name, description, n_certs, certs` (`certs` is a list of dicts).

## CCCertificate (Common Criteria)

| Attribute | Notes |
|---|---|
| `dgst` | 16-hex id; also the txt/pdf filename stem |
| `name`, `manufacturer`, `manufacturer_web` | `manufacturer` is a raw string; may contain several companies separated by commas |
| `category` | 15 CC portal categories, e.g. `"ICs, Smart Cards and Smart Card-Related Devices and Systems"`, `"Network and Network-Related Devices and Systems"` |
| `scheme` | country code (`"DE"`, `"US"`, `"KR"`, …) |
| `status` | `"active"` / `"archived"` |
| `security_level` | set of strings like `{"EAL5+", "ALC_DVS.2", "AVA_VAN.5"}`; empty for ~20% (mostly PP-based certs) |
| `not_valid_before`, `not_valid_after` | `datetime.date` (issue / sunset) |
| `heuristics.eal`, `heuristics.cert_id`, `heuristics.cert_lab`, `heuristics.extracted_versions`, `heuristics.related_cves`, `heuristics.st_references` / `report_references` | derived data |
| `pdf_data.report_keywords`, `pdf_data.st_keywords` | keyword dicts from the certification report and the security target. Either can be `None` (~30 reports, ~180 STs) |
| `state.report`, `state.st`, `state.cert` | document state: `download_ok`, `convert_ok`, `extract_ok`, `txt_path`, `pdf_path` |

## FIPSCertificate (FIPS 140)

| Attribute | Notes |
|---|---|
| `dgst`, `cert_id` (int, the NIST certificate number) | |
| `web_data.module_name`, `web_data.vendor`, `web_data.vendor_url` | vendor is the raw string. ~118 vendors contain "email" (CSRC obfuscation) and the project skips them |
| `web_data.standard` | `"FIPS 140-1"` / `"FIPS 140-2"` / `"FIPS 140-3"` |
| `web_data.level` | int 1–4 |
| `web_data.status` | `"active"` / `"historical"` / `"revoked"` |
| `web_data.module_type`, `web_data.embodiment`, `web_data.date_sunset`, `web_data.caveat`, `web_data.description` | |
| `web_data.validation_history` | list of entries with `.date`, `.validation_type`, `.lab`. `[0].date` is used as the issue date. Can be empty (rare) |
| `pdf_data.keywords` | keyword dict from the security policy (falsy for ~1 cert) |
| `pdf_data.module_algorithms`, `pdf_data.policy_algorithms`, `heuristics.algorithms` | sets of CAVP algorithm ids |
| `state.policy` | document state for the security-policy PDF/txt |

## Keyword dicts

Both CC (`report_keywords`, `st_keywords`) and FIPS (`keywords`) use the same two-level shape:
`category -> group -> matched string -> count`.

```python
kw["crypto_library"]  # {"OpenSSL": {"OpenSSL": 2}}
                      # {"Neslib": {"NesLib v2.0": 3, "NesLib 6.7": 1}}
```

- Group keys (outer) are normalized library names: `OpenSSL`, `BoringSSL`, `LibreSSL`, `NSS`,
  `libgcrypt`, `GnuTLS`, `wolfSSL`, `mbedTLS`, `BouncyCastle`, `Crypto++`, `Nettle`, `MatrixSSL`,
  `Neslib`, `Infineon`, `AT1`, `AtmelToolbox`, `Generic`.
- Inner keys are the literal matches. Version strings live there, e.g. `NesLib 6.7.4` or `v1.02.013`.
  For OpenSSL the inner key is almost always just `"OpenSSL"`, so **the keyword data carries no OpenSSL
  version**. Version detection needs the raw text.
- `kw["crypto_library"][name][name]` is what `utils.py` reads. This works for OpenSSL, BoringSSL, NSS,
  libgcrypt and BouncyCastle, where the inner key equals the group name. It **raises KeyError** for
  libraries whose inner keys are versioned strings (Neslib, Infineon, AT1, Generic). For those, use
  `sum(kw["crypto_library"].get(name, {}).values())`.
- Other categories: `symmetric_crypto`, `asymmetric_crypto`, `pq_crypto`, `hash_function`,
  `crypto_protocol`, `tls_cipher_suite`, `crypto_engine`, `randomness`, `cipher_mode`, `ecc_curve`,
  `vulnerability`, `side_channel_analysis`, `os_name`, `device_model`, `vendor`, `eval_facility`,
  `standard_id`, `javacard_*`, plus CC-only `cc_cert_id`, `cc_sar`, `cc_sfr`, `cc_security_level`,
  `cc_protection_profile_id`, `cc_claims`, `technical_report_id`, and FIPS-only `fips_cert_id`,
  `fips_security_level`, `fips_certlike`.
- Guard pattern: `if kw and "crypto_library" in kw and name in kw["crypto_library"]`.
  `kw` may be `None` or empty.

Approximate certificate counts with any OpenSSL mention: CC ~1.7k (report+ST combined), FIPS ~1k.

## Text artifacts on disk (`notebooks/datasets/`)

```
datasets/
  CC_dataset.json, FIPS_dataset.json      # the serialized datasets used by notebooks
  dataset.json                            # duplicate of FIPS_dataset.json
  certs/{reports,targets,certificates}/{pdf,txt,json}/<dgst>.{pdf,txt,json}
  certs/policies -> targets               # symlink so FIPS root_dir=./datasets finds policy txts
  fips/certs/targets/... , fips/certs/policies -> targets
  auxiliary_datasets/                     # cc_scheme, cpe, cve, protection_profiles, maintenances, algorithms
```

- CC ST text is at `certs/targets/txt/<dgst>.txt`, report text at `certs/reports/txt/<dgst>.txt`.
- `certs/targets/txt` also holds FIPS policy texts (both datasets share the folder through the symlink).
  The `dgst` values do not collide.
- `cert.state.st.txt_path` / `cert.state.policy.txt_path` can raise `ValueError` when no root_dir is set.
  `openssl_api_detection.ipynb` wraps this in `safe_get_txt_path()`.

## Project normalization conventions (`notebooks/src/`)

- `utils.get_cc_library_mentions(dataset, name)` builds a DataFrame with the columns `Library, Manufacturer,
  IssueDate, SunsetDate, <name>MentionedReport, <name>MentionedTarget, Country, Category`.
  - Categories are collapsed: anything containing `"Network"` becomes `"Network Devices and Systems"`,
    and anything containing `"Smart Card"` becomes `"Smart Cards"`.
  - It skips manufacturers that are `None` or the Cloudflare-obfuscated string `"[email protected]"`.
- `utils.get_fips_library_mentions(dataset, name)` builds a DataFrame with the columns `Library, ModuleName,
  IssueDate, Manufacturer, <name>Mentioned, SunsetDate, Standard, Status, Vendor_url, Level, ModuleType, Year`.
  It skips vendors containing "email".
- Manufacturer unification (`manufacturer_cleanup.py` + `unification_dictionaries.py`):
  1. `comma_exceptions`: exact raw strings that contain commas but are a single company.
  2. `pre_process_manufacturer`: split on commas, drop legal suffixes (`suffixes_to_remove`, e.g. "inc.",
     "ltd"), keep the first company.
  3. `unify_manufacturer`: an exact lowercase lookup in `manufacturer_mapping`, then a substring match
     against `manufacturer_patterns` (first hit wins, so **dict order matters**).
  - Add new vendor aliases to the dictionaries. Don't special-case them in notebooks.
- `openssl_man3.json` lists OpenSSL 3.3 man3 API names, scraped by `openssl_parser.py`. The
  OpenSSL API detection notebook filters it by prefix (`SSL_`, `EVP_`, `BIO_`, …) and token-matches the cert texts.

## Pitfalls

- A cert can mention OpenSSL in both its report and its ST. Count certificates, not mentions, unless you mean mentions.
- When combining CC and FIPS, the same product can appear in both datasets. Don't treat the union as unique products.
- Date columns built from cert attributes have object dtype. Run `pd.to_datetime` on them before using `.dt`,
  as `get_fips_library_mentions` does.
- Building DataFrames with `df.loc[len(df)] = ...` in loops is slow. Collect a list of dicts and construct the DataFrame once.
