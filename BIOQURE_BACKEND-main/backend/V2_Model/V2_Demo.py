import os
import pandas as pd
import numpy as np
import joblib
from collections import Counter
import warnings

warnings.filterwarnings('ignore')

print("\n" + "="*70)
print("🧬 V2.0 MULTI-MODAL PATHOGEN TRACKER (Live Inference)")
print("="*70)

# ==========================================
# THE BULLETPROOF PATHING FIX
# ==========================================
script_dir = os.path.dirname(os.path.abspath(__file__))
data_folder = os.path.join(script_dir, '..', 'V2_Model_Output')

model_path = os.path.join(data_folder, 'v2_multi_input_model.pkl')
features_path = os.path.join(data_folder, 'v2_feature_columns.pkl')

# ==========================================
# 1. LOAD THE BRAIN & FEATURES
# ==========================================
try:
    print("[System] Booting Neural Engine...")
    model = joblib.load(model_path)
    feature_columns = joblib.load(features_path)
    print("✅ AI Brain Online.")
except FileNotFoundError:
    print(f"❌ Error: Could not find the AI Brain at: {data_folder}")
    print("Please run the 'train_v2_multi_input.py' script first to generate the models!")
    exit()

# ==========================================
# 2. LOAD PATIENT DNA
# ==========================================
print("\n[Input Required]")
custom_path = input("Drag and drop the patient's raw .fna file here: ").strip().strip('"').strip("'")

if not os.path.exists(custom_path):
    print(f"❌ Error: File not found at {custom_path}")
    exit()

genome_id = os.path.basename(custom_path).replace('.fna', '')
print(f"✅ DNA Loaded: {genome_id}")

# ==========================================
# 3. REAL-TIME K-MER EXTRACTION
# ==========================================
print("[System] Sequencing Genome (Extracting K-mers)...")
def get_kmers(sequence, k=6):
    return [sequence[i:i+k] for i in range(len(sequence) - k + 1)]

# Read the raw file
with open(custom_path, 'r') as f:
    # Skip the first line (metadata) and join the DNA sequence
    seq = "".join([line.strip() for line in f if not line.startswith(">")]).upper()

# Count the 6-mers
kmer_counts = Counter(get_kmers(seq, 6))

# ==========================================
# 4. CLINICAL INPUT (THE DRUG)
# ==========================================
print("\n" + "-"*50)
print("💊 PHARMACOLOGY INTERFACE")
print("-"*50)
print("Available Drug Classes (Examples): Penicillin, Tetracycline, Meropenem, Ciprofloxacin, etc.")
chosen_drug = input("Enter the Antibiotic you wish to prescribe: ").strip()

# ==========================================
# 5. MATHEMATICAL FUSION & PREDICTION
# ==========================================
print("\n[System] Fusing DNA Topology with Chemical Footprint...")

# Create a blank slate with the exact shape the AI expects
inference_data = pd.DataFrame(0, index=[0], columns=feature_columns)

# Fill in the K-mer math
for kmer, count in kmer_counts.items():
    if kmer in inference_data.columns:
        inference_data.at[0, kmer] = count

# Fill in the Drug math (One-Hot Encoding matching)
drug_column = f"Drug_{chosen_drug}"
if drug_column in inference_data.columns:
    inference_data.at[0, drug_column] = 1
else:
    print(f"\n⚠️ WARNING: The AI has never seen the drug '{chosen_drug}' during training.")
    print("Attempting to predict based strictly on baseline DNA geometry...\n")

# Run the Prediction
prediction = model.predict(inference_data)[0]

# ==========================================
# 6. FINAL DIAGNOSIS
# ==========================================
print("\n" + "="*70)
print("🛑 CLINICAL DIAGNOSIS & PREDICTION")
print("="*70)
print(f"Patient ID:  {genome_id}")
print(f"Treatment:   {chosen_drug}")

if prediction == 1:
    print("\n🚨 AI VERDICT: RESISTANT")
    print(f"⚠️ DO NOT PRESCRIBE {chosen_drug.upper()}. The pathogen's genetic topology")
    print("   contains mechanisms to defeat this specific molecular structure.")
else:
    print("\n✅ AI VERDICT: SUSCEPTIBLE")
    print(f"🟢 SAFE TO PRESCRIBE {chosen_drug.upper()}. No topological resistance")
    print("   motifs detected against this drug class.")
print("="*70 + "\n")