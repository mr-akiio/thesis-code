import argparse
import os

from sec_certs.dataset.cc import CCDataset
from sec_certs.dataset.fips import FIPSDataset

# Datasets live in notebooks/datasets, next to this src directory
script_dir = os.path.dirname(os.path.abspath(__file__))
DATASETS_DIR = os.path.join(os.path.dirname(script_dir), "datasets")

DATASETS = {
    "cc": ("CC", CCDataset, "CC_dataset.json"),
    "fips": ("FIPS 140", FIPSDataset, "FIPS_dataset.json"),
}


def download_dataset(key, force=False):
    label, dataset_cls, filename = DATASETS[key]
    output_file = os.path.join(DATASETS_DIR, filename)

    if os.path.exists(output_file) and not force:
        print(f"{output_file} already exists, skipping {label} (use --force to re-download)")
        return

    print(f"Downloading {label} dataset")
    dataset = dataset_cls.from_web(auxiliary_datasets=True, artifacts=True, path=DATASETS_DIR)
    print(f"Downloaded {len(dataset)} {label} certificates")

    dataset.to_json(output_file)
    print(f"Dataset saved to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download the sec-certs CC and FIPS 140 datasets with artifacts.")
    # No argparse choices here: older Pythons reject an empty list for nargs="*"
    parser.add_argument("datasets", nargs="*", help="Datasets to download: cc, fips (default: all)")
    parser.add_argument("--force", action="store_true", help="Re-download even if the dataset JSON already exists")
    args = parser.parse_args()

    unknown = [d for d in args.datasets if d not in DATASETS]
    if unknown:
        parser.error(f"unknown dataset(s): {', '.join(unknown)} (choose from {', '.join(DATASETS)})")

    os.makedirs(DATASETS_DIR, exist_ok=True)
    for key in args.datasets or DATASETS:
        download_dataset(key, force=args.force)
