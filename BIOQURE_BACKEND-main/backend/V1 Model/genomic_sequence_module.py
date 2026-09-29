import numpy as np
import matplotlib.pyplot as plt
import os

def generate_dna_chaos_game(fasta_path, output_image_path):
    with open(fasta_path, 'r') as f:
        # Get DNA string, skip header
        seq = "".join([line.strip() for line in f if not line.startswith(">")]).upper()
    
    # Coordinates for A, T, G, C
    coords = {
        'A': np.array([0, 0]),
        'T': np.array([1, 0]),
        'G': np.array([1, 1]),
        'C': np.array([0, 1])
    }
    
    pos = np.array([0.5, 0.5])
    points = []
    
    # Process first 10,000 bases for the "Visual Fingerprint"
    for base in seq[:10000]:
        if base in coords:
            pos = (pos + coords[base]) / 2
            points.append(pos)
            
    points = np.array(points)
    
    # Create the CV Input Image
    plt.figure(figsize=(5, 5), dpi=64) # 320x320 image
    plt.scatter(points[:, 0], points[:, 1], s=0.1, c='blue', alpha=0.5)
    plt.axis('off')
    plt.savefig(output_image_path, bbox_inches='tight', pad_inches=0)
    plt.close()

# Example Usage for your Demo:
# generate_dna_chaos_game("bacterial_dna/sample.fna", "dna_cv_fingerprint.png")