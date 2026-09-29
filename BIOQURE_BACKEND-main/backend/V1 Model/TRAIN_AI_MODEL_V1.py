import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib
import warnings
import os

warnings.filterwarnings('ignore')

# ==========================================
# 0. PATHING ENGINE (The Fix)
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
project_root = os.path.abspath(os.path.join(BASE_DIR, ".."))
DATA_DIR = os.path.join(project_root, 'DATASET')
# Define where the DATA is and where the OUTPUT goes
DATA_FOLDER = DATA_DIR # Assuming CSVs are in the root
OUTPUT_FOLDER = os.path.join(project_root, 'V1_Model_Output')

# Create the output folder if it doesn't exist
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)
    print(f"📁 Created Output Directory: {OUTPUT_FOLDER}")

print("="*60)
print("🧠 V1.0 GENERIC RESISTANCE AI (Baseline Model)")
print("="*60)

# ==========================================
# 1. LOAD DATA
# ==========================================
print(f"[1/4] Loading Genomic Features from {DATA_FOLDER}...")
try:
    # Use absolute paths for the CSVs
    features_path = os.path.join(DATA_FOLDER, "FINAL_FEATURES.csv")
    labels_path = os.path.join(DATA_FOLDER, "MASTER_TRAINING_LABELS.csv")
    
    features_df = pd.read_csv(features_path, low_memory=False) 
    labels_df = pd.read_csv(labels_path, low_memory=False)
except FileNotFoundError as e:
    print(f"❌ Error: CSV files not found in {DATA_FOLDER}")
    print(f"Actual error: {e}")
    exit()

# Cleanup column names
features_df.columns = features_df.columns.str.strip()
labels_df.columns = labels_df.columns.str.strip()

# ==========================================
# 2. FUSE & CLEAN
# ==========================================
print("[2/4] Fusing Matrix...")
# Drop duplicates if they exist in features
if 'Resistant Phenotype' in features_df.columns:
    features_df = features_df.drop(columns=['Resistant Phenotype'])

merged_df = pd.merge(labels_df[['Genome ID', 'Resistant Phenotype']], 
                     features_df, on='Genome ID', how='inner')

# Binary classification: 1 for Resistance, 0 for Susceptible
merged_df['Target'] = merged_df['Resistant Phenotype'].astype(str).str.lower().apply(
    lambda x: 1 if 'resist' in x else 0
)

y = merged_df['Target']
X = merged_df.drop(columns=['Genome ID', 'Resistant Phenotype', 'Target'], errors='ignore')

# Ensure we only have numeric K-mer counts
X = X.select_dtypes(exclude=['object', 'string'])

# CRITICAL: Save feature columns so the Dashboard knows the EXACT order
feature_cols_path = os.path.join(OUTPUT_FOLDER, 'v1_feature_columns.pkl')
joblib.dump(list(X.columns), feature_cols_path)

# ==========================================
# 3. TRAIN
# ==========================================
print(f"[3/4] Training Random Forest on {len(X)} samples...")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

rf_v1 = RandomForestClassifier(
    n_estimators=500, 
    n_jobs=-1, 
    random_state=42, 
    class_weight='balanced' # Handles imbalanced "Resistant" vs "Susceptible" data
)
rf_v1.fit(X_train, y_train)

# ==========================================
# 4. EVALUATE & SAVE
# ==========================================
print("[4/4] Evaluating...")
predictions = rf_v1.predict(X_test)
print(f"\n🏆 V1.0 ACCURACY: {accuracy_score(y_test, predictions) * 100:.2f}%")

# Save the model into the dedicated Output folder
model_save_path = os.path.join(OUTPUT_FOLDER, 'antibiotic_strength_model.pkl')
joblib.dump(rf_v1, model_save_path)

print(f"\n✅ All V1 Assets Saved to: {OUTPUT_FOLDER}")
print(f"   - Model: antibiotic_strength_model.pkl")
print(f"   - Columns: v1_feature_columns.pkl")
print("="*60)