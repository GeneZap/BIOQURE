import os
import warnings

# Silence warnings for a clean terminal
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
warnings.filterwarnings('ignore')

import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing import image
import matplotlib.pyplot as plt

# --- PATHING ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))
# Make sure this path points exactly to where your new .h5 file is!
V3_PATH = os.path.join(project_root, 'V3_Model_Output', 'v3_vision_model.h5')

# --- LOAD VISION BRAIN ---
print("\n" + "="*50)
print("👁️ Booting V3 HD Vision Diagnostic Tool...")
print("="*50)
try:
    model = tf.keras.models.load_model(V3_PATH)
    print("✅ HD CNN Loaded Successfully.")
except Exception as e:
    print(f"❌ Error loading model: {e}")
    exit()

# --- TEST FUNCTION ---
def diagnose_dna_visually(fna_path):
    print(f"\n🔬 Scanning Topological Signature for: {os.path.basename(fna_path)}")
    
    # 1. Read DNA
    with open(fna_path, 'r', encoding='utf-8', errors='ignore') as f:
        seq = "".join([line.strip() for line in f if not line.startswith(">")]).upper()
    
    # 2. Generate the HD "Visual Fingerprint" (The CGR Fractal)
    coords = {'A': [0,0], 'T': [1,0], 'G': [1,1], 'C': [0,1]}
    pos = np.array([0.5, 0.5])
    points = []
    
    # Using 50,000 bases to match the training data density
    for base in seq[:50000]: 
        if base in coords:
            pos = (pos + np.array(coords[base])) / 2
            points.append(pos)
    points = np.array(points)
    
    # HD Settings: 500x500 pixels
    plt.figure(figsize=(5, 5), dpi=100, facecolor='black')
    plt.scatter(points[:, 0], points[:, 1], s=0.5, c='cyan', alpha=0.9, marker='.')
    plt.axis('off')
    
    temp_plot = "v3_hd_test_plot.png"
    plt.savefig(temp_plot, bbox_inches='tight', pad_inches=0, facecolor='black')
    
    # Optional: Show the judge what the AI is "seeing"
    # plt.show() 
    plt.close()
    
    # 3. Predict (Using the upgraded 256x256 resolution)
    img = image.load_img(temp_plot, target_size=(200, 200))
    img_array = image.img_to_array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    
    prediction_prob = model.predict(img_array, verbose=0)[0][0]
    
    print("\n" + "="*40)
    print(f"🔬 VISION ANALYSIS REPORT")
    print("="*40)
    
    # Class Mapping Check: RESISTANT is 0, so closer to 0 = Resistant
    if prediction_prob < 0.50:
        confidence = (1 - prediction_prob) * 100
        print(f"RESULT: 🚨 RESISTANT PATTERN DETECTED")
        print(f"CONFIDENCE: {confidence:.2f}%")
        print(f"MOTIF: Beta-Lactamase / Plasmid structural signature")
    else:
        confidence = prediction_prob * 100
        print(f"RESULT: 🟢 SUSCEPTIBLE PATTERN DETECTED")
        print(f"CONFIDENCE: {confidence:.2f}%")
        print(f"MOTIF: Standard chromosomal baseline")
    print("="*40)
    
    # Clean up
    if os.path.exists(temp_plot):
        os.remove(temp_plot)

# --- EXECUTION ---
test_file = input("\n🧬 Drag an .fna file here to test V3 Vision: ").strip().strip('"').strip("'")
if os.path.exists(test_file):
    diagnose_dna_visually(test_file)
else:
    print("❌ File not found!")