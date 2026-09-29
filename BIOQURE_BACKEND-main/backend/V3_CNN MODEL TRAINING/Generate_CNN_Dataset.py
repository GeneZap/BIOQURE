import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(BASE_DIR, ".."))
DNA_DIR = os.path.join(project_root, "bacterial_dna") # Folder containing .fna files
DATASET_PATH = os.path.join(project_root, "DATASET") # CSV with Genome ID and Resistant Phenotype
CSV_PATH = os.path.join(DATASET_PATH, "MASTER_TRAINING_LABELS.csv") # CSV with Genome ID and Resistant Phenotype
OUTPUT_BASE = os.path.join(BASE_DIR, "CNN_CGR_DATASET")

os.makedirs(os.path.join(OUTPUT_BASE, "RESISTANT"), exist_ok=True)
os.makedirs(os.path.join(OUTPUT_BASE, "SUSCEPTIBLE"), exist_ok=True)

print("⚙️ Booting HD Dataset Generator...")

try:
    labels_df = pd.read_csv(CSV_PATH, low_memory=False)
    labels_df.columns = labels_df.columns.str.strip()
    label_map = dict(zip(labels_df['Genome ID'].astype(str), labels_df['Resistant Phenotype'].astype(str).str.lower()))
    print(f"✅ Loaded {len(label_map)} labels.")
except Exception as e:
    print(f"❌ Error reading CSV: {e}")
    exit()

def generate_hd_cgr(seq, save_path):
    coords = {'A': [0,0], 'T': [1,0], 'G': [1,1], 'C': [0,1]}
    pos = np.array([0.5, 0.5])
    points = []
    
    # 50,000 bases for a rich, dense fractal
    for base in seq[:50000]: 
        if base in coords:
            pos = (pos + np.array(coords[base])) / 2
            points.append(pos)
    points = np.array(points)
    
    # HD UPGRADE: 5x5 inches at 100 DPI = Crisp 500x500 pixels
    plt.figure(figsize=(5, 5), dpi=100, facecolor='black')
    plt.scatter(points[:, 0], points[:, 1], s=0.5, c='cyan', alpha=0.9, marker='.')
    plt.axis('off')
    plt.savefig(save_path, bbox_inches='tight', pad_inches=0, facecolor='black')
    plt.close()

print("🚀 Generating HD CGR Fractals...")
processed = 0

for filename in os.listdir(DNA_DIR):
    if filename.endswith(".fna"):
        genome_id = filename.replace(".fna", "")
        phenotype = label_map.get(genome_id, "unknown")
        
        if "resist" in phenotype:
            save_dir = os.path.join(OUTPUT_BASE, "RESISTANT")
        elif "suscept" in phenotype:
            save_dir = os.path.join(OUTPUT_BASE, "SUSCEPTIBLE")
        else:
            continue 
            
        save_path = os.path.join(save_dir, f"{genome_id}.png")
        
        with open(os.path.join(DNA_DIR, filename), 'r', encoding='utf-8', errors='ignore') as f:
            seq = "".join([line.strip() for line in f if not line.startswith(">")]).upper()
        
        generate_hd_cgr(seq, save_path)
        processed += 1
        if processed % 50 == 0: print(f"  ... Generated {processed} HD images ...")

print(f"✅ Done! {processed} HD training images saved to {OUTPUT_BASE}")