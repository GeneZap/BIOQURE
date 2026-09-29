import os
import csv
from collections import Counter
import itertools

# --- CONFIG ---
dna_folder = "bacterial_dna"
metadata_file = "MASTER_TRAINING_LABELS.csv" 
output_csv = "FINAL_FEATURES.csv"
K = 6 

def get_kmers(sequence, k):
    return [sequence[i:i+k] for i in range(len(sequence) - k + 1)]

print("Step 2: Starting Memory-Safe Feature Extraction...")

# Load metadata
metadata = {}
try:
    with open(metadata_file, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            id_col = next((c for c in row.keys() if 'genome' in c.lower() and 'id' in c.lower()), None)
            if id_col:
                metadata[row[id_col]] = row
except Exception as e:
    print(f"Error reading metadata: {e}")
    exit()

dna_files = [f for f in os.listdir(dna_folder) if f.endswith(".fna")]

# Generate all possible 4,096 combinations of A,C,T,G for K=6
base_headers = list(next(iter(metadata.values())).keys())
all_possible_kmers = [''.join(p) for p in itertools.product('ACGT', repeat=K)]
headers = base_headers + all_possible_kmers

# Process and write iteratively (Saves RAM)
with open(output_csv, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()

    for i, filename in enumerate(dna_files):
        gid = filename.replace(".fna", "")
        if gid not in metadata: continue
        
        print(f"[{i+1}/{len(dna_files)}] Extracting 4,096 features from {gid}...", end="\r")
        
        try:
            with open(os.path.join(dna_folder, filename), 'r') as seq_file:
                sequence = "".join([line.strip() for line in seq_file if not line.startswith(">")]).upper()
                counts = Counter(get_kmers(sequence, K))
                row_data = metadata[gid].copy()
                
                # Fill K-mer frequencies
                for kmer in all_possible_kmers:
                    row_data[kmer] = counts.get(kmer, 0)
                    
                writer.writerow(row_data)
        except Exception as e:
            pass

print(f"\n✅ Feature Extraction Complete! Saved to '{output_csv}'.")