import csv
import os
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

# --- CONFIG (paths relative to this package directory) ---
_BASE = Path(__file__).resolve().parent
csv_file = str(_BASE / "data" / "correct_BVBRC_genome_amr_1-200.csv")
output_folder = str(_BASE / "bacterial_dna")

os.makedirs(output_folder, exist_ok=True)

# --- DOWNLOADER ---
try:
    with open(csv_file, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        if "Genome ID" not in reader.fieldnames:
            print(f"Error: Could not find 'Genome ID' column. Found: {reader.fieldnames}")
            exit()

        genome_ids = {row["Genome ID"] for row in reader if row["Genome ID"]}
        print(f"Found {len(genome_ids)} unique genomes. Starting download...")

        for i, gid in enumerate(sorted(genome_ids)):
            save_path = os.path.join(output_folder, f"{gid}.fna")

            if os.path.exists(save_path):
                print(f"[{i + 1}/{len(genome_ids)}] Skipping {gid} (Already exists)")
                continue

            base_url = "https://bv-brc.org"
            params = {
                "eq": f"(genome_id,{gid})",
                "limit": "25000",
                "http_accept": "application/vnd.fasta",
            }

            try:
                print(f"[{i + 1}/{len(genome_ids)}] Downloading {gid}...", end=" ", flush=True)
                query = urlencode(params)
                url = f"{base_url}?{query}"
                with urlopen(url, timeout=60) as r:
                    text = r.read().decode("utf-8")

                if len(text) > 100:
                    with open(save_path, "w", encoding="utf-8") as out:
                        out.write(text)
                    print("SUCCESS")
                else:
                    print("FAILED (short response)")
            except Exception as e:
                print(f"ERROR: {e}")

            time.sleep(0.5)

except FileNotFoundError:
    print(f"Error: Could not find '{csv_file}'!")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

print("\nProcess finished! Check the 'bacterial_dna' folder.")
