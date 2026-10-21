# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Thesis analysis code studying mentions and usage of OpenSSL (and alternative crypto libraries) in Common Criteria (CC) and FIPS 140 certificates collected by [sec-certs](https://github.com/crocs-muni/sec-certs). This is a set of Jupyter notebooks plus a few helper modules, not an installable package. There are no tests, linters, or build steps beyond the Docker image.

## Running

```bash
docker-compose build --no-cache   # first time, or after changing docker/Dockerfile
docker-compose up                 # JupyterLab on http://127.0.0.1:8888 (no token)
```

- The container (`sec-certs-analysis-jupyter`) mounts `./notebooks` at `/home/jovyan/work`, which is the Jupyter root. Notebook-relative paths therefore resolve against `notebooks/`: `./datasets/...`, `./results/...`, and `from src.utils import ...`.
- `PYTHONPATH=/home/jovyan/src` maps the top-level `./src`, which is empty. The real helper modules live in `notebooks/src/` and are imported as the `src` package from the notebook directory.
- sec-certs, spaCy and the IJava kernel are only installed in the image. The host Python does not have `sec_certs`, so run analysis code inside the container (or through the `jupyter` MCP server in `.mcp.json`, which talks to the running JupyterLab).

## Notebooks

- `combined_cc_fips.ipynb` is the main notebook referenced by the README. It loads both datasets, builds per-library mention DataFrames via `src.utils`, and produces the figures saved to `notebooks/img/`.
- `openssl_api_detection.ipynb` (current branch work) finds certificates whose texts use OpenSSL API names (from `src/openssl_man3.json`, filtered by prefix such as `SSL_` or `EVP_`) without declaring OpenSSL in their keywords. Results are written to `notebooks/results/` as CSV and JSON.
- `openssl_cc.ipynb` / `openssl_fips.ipynb` are early exploratory stubs. Note that they use `../datasets/` paths, unlike the others.

## Data

- `notebooks/datasets/` (gitignored, several GB) holds `CC_dataset.json`, `FIPS_dataset.json`, the extracted PDF/txt artifacts, and auxiliary datasets. Load with `CCDataset.from_json(...)` / `FIPSDataset.from_json(...)` and set `.root_dir = Path("./datasets")` so artifact paths resolve. Avoid `from_web()` cells unless a fresh download is intended, because the FIPS artifacts alone are about 5 GB.
- Do not modify anything under `notebooks/datasets/`.
- The `sec-certs-schema` skill documents the certificate object model, keyword-dict shapes, the on-disk artifact layout, and pitfalls.

## Helper modules (`notebooks/src/`)

- `utils.py`: `get_cc_library_mentions` / `get_fips_library_mentions` turn a dataset plus a library name into a DataFrame of certificates mentioning that library. They also apply the project's category collapsing and skip obfuscated email manufacturers or vendors.
- Manufacturer unification is a pipeline: `manufacturer_cleanup.py` holds the logic, and `unification_dictionaries.py` holds the data (`comma_exceptions` → suffix stripping → exact `manufacturer_mapping` → substring `manufacturer_patterns`, first match wins). Fix vendor-name inconsistencies by editing the dictionaries, not by special-casing them in notebooks.
- `openssl_parser.py` regenerates `openssl_man3.json` by scraping the OpenSSL 3.3 man3 index.

Notebooks import these at kernel start, so edits to `notebooks/src/*.py` need a kernel restart (or `importlib.reload`) to take effect.
