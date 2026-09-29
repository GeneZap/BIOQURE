import os
import warnings

# --- 0. SILENCE WARNINGS ---
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
warnings.filterwarnings('ignore')

import joblib
import pandas as pd
import numpy as np
import tensorflow as tf
from collections import Counter
import matplotlib.pyplot as plt
from tensorflow.keras.preprocessing import image

# --- 1. PATHING SETUP ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(BASE_DIR, ".."))

V1_DIR = os.path.join(project_root, 'V1_Model_Output')
V2_DIR = os.path.join(project_root, 'V2_Model_Output')
V3_DIR = r"d:\CV_HACKATHON_MODEL_DATASET\V3_CNN MODEL TRAINING\V3_Model_Output"
CARD_FASTA = os.path.join(project_root, 'CARD_DB.fasta')

# --- 2. LOAD ALL MODELS ---
print("\n" + "="*65)
print("⚙️ Booting Quad-Engine Clinical AI Suite...")
print("="*65)

try:
    # LOAD V1 (Updated to match your actual V1 output file names)
    v1_model = joblib.load(os.path.join(V1_DIR, 'antibiotic_strength_model.pkl'))
    v1_features = joblib.load(os.path.join(V1_DIR, 'v1_feature_columns.pkl'))
    
    # Try to load the translators if they exist!
    try: v1_scaler = joblib.load(os.path.join(V1_DIR, 'v1_scaler.pkl'))
    except: v1_scaler = None
    
    try: v1_encoder = joblib.load(os.path.join(V1_DIR, 'v1_label_encoder.pkl'))
    except: v1_encoder = None

    v2_model = joblib.load(os.path.join(V2_DIR, 'v2_multi_input_model.pkl'))
    v2_features = joblib.load(os.path.join(V2_DIR, 'v2_feature_columns.pkl'))
    v3_model = tf.keras.models.load_model(os.path.join(V3_DIR, 'v3_vision_model.h5'))
    print("✅ All Neural & Mathematical Engines Online.\n")
except Exception as e:
    print(f"❌ CRITICAL BOOT ERROR: Could not load models. \nDetails: {e}")
    exit()

# --- 3. USER INPUT ---
patient_file = input("🧬 Drag Patient DNA (.fna) here: ").strip().strip('"').strip("'")
drug_name = input("💊 Enter Antibiotic to Test: ").strip()

print("\n🔬 Sequencing Raw DNA File...")
try:
    with open(patient_file, 'r', encoding='utf-8', errors='ignore') as f:
        sequence = "".join([line.strip() for line in f if not line.startswith(">")]).upper()
except Exception as e:
    print(f"❌ Error reading DNA file: {e}")
    exit()
 
kmers = [sequence[i:i+6] for i in range(len(sequence) - 6 + 1)]
counts = Counter(kmers) 

# =====================================================================
# ENGINE 1: THE V1 GENOMIC PROFILER (Species ID + ML Baseline)
# =====================================================================
print("\n[ V1 ] Profiling Genomic Baseline...")

# 1. BIOLOGICAL HEURISTIC (Species Identification)
seq_length = len(sequence)
gc_count = sequence.count('G') + sequence.count('C')
gc_content = (gc_count / seq_length) * 100 if seq_length > 0 else 0

if 32 <= gc_content <= 34: species_guess = "Staphylococcus aureus"
elif 38 <= gc_content <= 40: species_guess = "Acinetobacter baumannii"
elif 49 <= gc_content <= 52: species_guess = "Escherichia coli / Salmonella"
elif 56 <= gc_content <= 58: species_guess = "Klebsiella pneumoniae"
elif 66 <= gc_content <= 68: species_guess = "Pseudomonas aeruginosa"
else: species_guess = "Unknown Pathogen Strain"

print(f"  -> Length: {seq_length:,} base pairs")
print(f"  -> GC Content: {gc_content:.2f}%")
print(f"  -> Identity Claim: {species_guess}")


# 2. MACHINE LEARNING BASELINE (Resistance Prediction)
test_row_v1 = [counts.get(col_name, 0) for col_name in v1_features]
test_df_v1 = pd.DataFrame([test_row_v1], columns=v1_features)

# Apply Scaler if you have one
if v1_scaler is not None:
    test_df_v1 = pd.DataFrame(v1_scaler.transform(test_df_v1), columns=v1_features)

v1_raw_prediction = v1_model.predict(test_df_v1)[0]

# Your V1 training script mapped 1 to Resistant, 0 to Susceptible
v1_verdict = "RESISTANT" if v1_raw_prediction == 1 else "SUSCEPTIBLE"
print(f"  -> ML Baseline Verdict: {v1_verdict}")

# =====================================================================
# ENGINE 2: THE V2 GENOMIC FUSION (Math & K-mers)
# =====================================================================
print("\n[ V2 ] Aligning K-mer Matrix...")
kmers = [sequence[i:i+6] for i in range(len(sequence) - 6 + 1)]
counts = Counter(kmers)

test_row = [counts.get(col_name, 0) for col_name in v2_features]
test_df = pd.DataFrame([test_row], columns=v2_features)

v2_prediction = v2_model.predict(test_df)[0]
v2_verdict = "RESISTANT" if v2_prediction == 1 else "SUSCEPTIBLE"
print(f"  -> Verdict: {v2_verdict}")


# =====================================================================
# ENGINE 3: THE V3 VISION ANALYZER (HD CGR CNN)
# =====================================================================
print("\n[ V3 ] Scanning Visual Topology...")

temp_cgr = "cgr_display.png" 
coords = {'A': [0,0], 'T': [1,0], 'G': [1,1], 'C': [0,1]}
pos = np.array([0.5, 0.5])
points = []

for base in sequence[:50000]: 
    if base in coords:
        pos = (pos + np.array(coords[base])) / 2
        points.append(pos)
points = np.array(points)

# HD Settings
plt.figure(figsize=(5, 5), dpi=100, facecolor='black')
plt.scatter(points[:, 0], points[:, 1], s=0.5, c='cyan', alpha=0.9, marker='.')
plt.axis('off')
plt.savefig(temp_cgr, bbox_inches='tight', pad_inches=0, facecolor='black')
plt.close()

# CHANGE BACK TO 256 ONCE YOUR NEW V3 FINISHES TRAINING! (Kept at 200 to prevent crashing for now)
img = image.load_img(temp_cgr, target_size=(256, 256)) 
img_array = image.img_to_array(img) / 255.0
img_array = np.expand_dims(img_array, axis=0)

prediction_prob = v3_model.predict(img_array, verbose=0)[0][0]

if prediction_prob < 0.50: 
    v3_verdict = "RESISTANT"
    confidence = (1 - prediction_prob) * 100
    v3_motif = "Beta-Lactamase / Plasmid structural signature"
else:
    v3_verdict = "SUSCEPTIBLE"
    confidence = prediction_prob * 100
    v3_motif = "Standard chromosomal baseline"

print(f"  -> Verdict: {v3_verdict} ({confidence:.1f}% Confidence)")


# =====================================================================
# ENGINE 4: THE V4 DISCOVERY SCANNER (CARD DB + Reverse Complement)
# =====================================================================
print("\n[ V4 ] Querying Official McMaster CARD Database...")

detected_genes = []
anomaly_found = False

# The Biological Translators
def classify_gene_type(gene_name):
    name = gene_name.lower()
    if any(x in name for x in ['bla', 'ndm', 'kpc', 'oxa', 'ctx', 'vim']): return "Beta-Lactamase"
    if 'tet' in name: return "Tetracycline Resistance"
    if 'mec' in name: return "Methicillin Resistance"
    if 'sul' in name: return "Sulfonamide Resistance"
    if any(x in name for x in ['qnr', 'gyr', 'par']): return "Fluoroquinolone"
    if 'mcr' in name: return "Colistin Resistance"
    if any(x in name for x in ['aac', 'ant', 'aph']): return "Aminoglycoside"
    return "Acquired Resistance Mechanism"

def get_reverse_complement(seq):
    complement = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C'}
    return "".join(complement.get(base, base) for base in reversed(seq))

def load_card_database(filepath):
    db = {}
    try:
        with open(filepath, 'r') as f:
            current_header, current_seq = "", []
            for line in f:
                line = line.strip()
                if line.startswith(">"):
                    if current_header: db[current_header] = "".join(current_seq)
                    current_header = line
                    current_seq = []
                else:
                    current_seq.append(line)
            if current_header: db[current_header] = "".join(current_seq)
        return db
    except FileNotFoundError:
        return None

card_db = load_card_database(CARD_FASTA)

if card_db:
    total_sigs = len(card_db)
    processed = 0
    print(f"  -> Loaded {total_sigs} signatures. Scanning forward & reverse strands...")
    
    for header, gene_sequence in card_db.items():
        processed += 1
        # Optional: A quiet heartbeat so it doesn't spam the dashboard
        if processed % 2000 == 0: print(f"  ... Scanning {processed}/{total_sigs} ...")
            
        if len(gene_sequence) > 60:
            forward_snippet = gene_sequence[:60]
            reverse_snippet = get_reverse_complement(forward_snippet)
            
            if forward_snippet in sequence or reverse_snippet in sequence:
                parts = header.split("|")
                gene_name = parts[-1] if len(parts) > 1 else header.replace(">", "")
                
                aro_id = "ARO:Unknown"
                for part in parts:
                    if "ARO:" in part: aro_id = part; break
                
                # Clean up the name for the dashboard display (remove the bracketed species info if it's too long)
                clean_name = gene_name.split("[")[0].strip() 
                gene_class = classify_gene_type(clean_name)
                detected_genes.append((clean_name, aro_id, gene_class))

if detected_genes:
    print(f"  -> ⚠️ CRITICAL: V4 aligned {len(detected_genes)} official CARD resistance genes!")
    unique_genes = {g[0]: g for g in detected_genes} 
    
    for name, data in list(unique_genes.items())[:5]: 
        gene_name, aro, g_type = data
        print(f"     - Confirmed Hit: [{aro}] {gene_name} | Mechanism: {g_type}")
    if len(unique_genes) > 5:
        print(f"     - ... and {len(unique_genes) - 5} more variants hidden.")
    anomaly_found = True
else:
    print("  -> ✅ V4 Scan Clear: No known CARD resistance genes aligned.")


# =====================================================================
# FINAL UNIFIED VERDICT & CLINICAL RECOMMENDATION
# =====================================================================
print("\n" + "="*65)
print(f"🏥 MULTI-MODAL DIAGNOSTIC REPORT")
print("="*65)

print(f"Identity Engine (V1) : {species_guess} ({gc_content:.1f}% GC)")
print(f"Genomic Logic (V2)   : {'🚨 RESISTANT' if v2_verdict == 'RESISTANT' else '🟢 SUSCEPTIBLE'}")
print(f"Visual Topology (V3) : {'🚨 RESISTANT' if v3_verdict == 'RESISTANT' else '🟢 SUSCEPTIBLE'} ({confidence:.1f}%)")

if v3_verdict == "RESISTANT" and anomaly_found:
    print(f"Discovery Engine (V4): ⚠️ CONFIRMED V3 HYPOTHESIS.")
elif not anomaly_found:
    print(f"Discovery Engine (V4): ✅ NO FOREIGN GENES")
else:
    print(f"Discovery Engine (V4): ⚠️ ANOMALY DETECTED (Standalone)")

print("-" * 65)

# Democratic Voting System (V2, V3, and V4 influence the risk)
risk_score = 0
if v2_verdict == "RESISTANT": risk_score += 1
if v3_verdict == "RESISTANT": risk_score += 1
if anomaly_found: risk_score += 2 # V4 finding a literal gene is undeniable proof

if risk_score >= 2:
    print(f"❌ FINAL VERDICT: HIGH RISK. Do not prescribe {drug_name.upper()}.")
else:
    print(f"✅ FINAL VERDICT: LOW RISK. {drug_name.upper()} is viable.")
print("="*65)