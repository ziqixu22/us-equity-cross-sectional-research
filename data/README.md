# Data policy

This directory contains documentation and small, public metadata only.

- `metadata/`: commit a frozen ticker-universe CSV, field dictionary, and data-quality summaries.
- `raw/`, `interim/`, `processed/`: local only and gitignored.
- `manifests/`: local retrieval manifests unless they contain only non-sensitive aggregate metadata approved for publication.

Never commit API keys, cookies, commercial data, or raw Yahoo/WRDS/CRSP files. Every report must state the data adapter, universe snapshot date, extraction date, adjusted-price convention, and limitations.
