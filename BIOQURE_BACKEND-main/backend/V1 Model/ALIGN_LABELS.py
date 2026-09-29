import os
import pandas as pd

# --- CONFIG ---
dna_folder = "bacterial_dna"
raw_csv_file = "BVBRC_genome_amr.csv"
output_clean_csv = "MASTER_TRAINING_LABELS.csv"

# --- EXACT COLUMN NAMES FROM YOUR CSV ---
ID_COL = "Genome ID"
NAME_COL = "Genome Name"
DRUG_COL = "Antibiotic"
LABEL_COL = "Resistant Phenotype"

print("Step 1: Starting Data Alignment...")

# 1. Get successfully downloaded files
if not os.path.exists(dna_folder):
    print(f"Error: Folder '{dna_folder}' not found!")
    exit()

downloaded_files = [f for f in os.listdir(dna_folder) if f.endswith('.fna')]
# Remove .fna to get just the ID (e.g., '287.34659')
downloaded_ids = [f.replace('.fna', '') for f in downloaded_files]
print(f"Found {len(downloaded_ids)} downloaded DNA sequences in '{dna_folder}'.")

# 2. Load raw dataset safely
try:
    # Use low_memory=False to handle large hackathon datasets
    df_raw = pd.read_csv(raw_csv_file, dtype=str, low_memory=False)
except FileNotFoundError:
    print(f"Error: Could not find '{raw_csv_file}'. Please place it in this folder.")
    exit()

# 3. Filter for only the DNA files you actually have
# This ensures we don't try to train on missing files
df_aligned = df_raw[df_raw[ID_COL].isin(downloaded_ids)].copy()

# 4. Clean: Remove rows that are missing the Resistance Label
initial_count = len(df_aligned)
df_aligned = df_aligned.dropna(subset=[LABEL_COL])

print(f"Filtered {initial_count} matches down to {len(df_aligned)} labeled samples.")

# 5. Save the pristine dataset
df_aligned.to_csv(output_clean_csv, index=False)
print(f"✅ Alignment Complete! Saved to '{output_clean_csv}'.")