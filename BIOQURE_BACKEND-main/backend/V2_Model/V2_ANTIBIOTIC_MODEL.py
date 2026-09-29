import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib
import warnings

warnings.filterwarnings('ignore')

print("="*60)
print("🧠 V2.0 MULTI-INPUT AI TRAINING ENGINE")
print("="*60)

# ==========================================
# THE BULLETPROOF PATHING FIX
# ==========================================
script_dir = os.path.dirname(os.path.abspath(__file__))
# Tell Python: "Go up one folder, then look inside DATA"
data_folder = os.path.join(script_dir, 'DATASET')

# Ensure the DATA folder actually exists
os.makedirs(data_folder, exist_ok=True)

features_csv_path = os.path.join(data_folder, 'FINAL_FEATURES.csv')
labels_csv_path = os.path.join(data_folder, 'MASTER_TRAINING_LABELS.csv')

# 1. Load the Data
print("[1/5] Loading Genomic Features and Clinical Labels...")
try:
    features_df = pd.read_csv(features_csv_path, low_memory=False) 
    labels_df = pd.read_csv(labels_csv_path, low_memory=False)
    
    # Strip invisible spaces
    features_df.columns = features_df.columns.str.strip()
    labels_df.columns = labels_df.columns.str.strip()
except FileNotFoundError:
    print(f"❌ Error: Python cannot find the CSV files in {data_folder}")
    print("Please make sure FINAL_FEATURES.csv and MASTER_TRAINING_LABELS.csv are in that folder!")
    exit()

# Clean the Genome ID columns so they match perfectly for the merge
features_df['Genome ID'] = features_df['Genome ID'].astype(str)
labels_df['Genome ID'] = labels_df['Genome ID'].astype(str)

# --- THE PANDAS '_x / _y' FIX ---
cols_to_drop = [col for col in ['Antibiotic', 'Resistant Phenotype', 'Target'] if col in features_df.columns]
if cols_to_drop:
    features_df = features_df.drop(columns=cols_to_drop)

# 2. Merge DNA with Drug Data
print("[2/5] Fusing DNA Matrix with Antibiotic Profiles...")
merged_df = pd.merge(labels_df[['Genome ID', 'Antibiotic', 'Resistant Phenotype']], 
                     features_df, 
                     on='Genome ID', 
                     how='inner')

# Clean the target variable to strict binary
merged_df['Target'] = merged_df['Resistant Phenotype'].astype(str).str.lower().apply(
    lambda x: 1 if 'resist' in x else 0
)

# 3. Mathematical Encoding (The Secret Sauce)
print("[3/5] Encoding Chemical Drug Vectors...")
encoded_df = pd.get_dummies(merged_df, columns=['Antibiotic'], prefix='Drug', dtype=int)

y = encoded_df['Target']
X = encoded_df.drop(columns=['Genome ID', 'Resistant Phenotype', 'Target'], errors='ignore')

# THE AUTO-SCRUBBER FIX: Kick out ANY remaining column that contains text strings
X = X.select_dtypes(exclude=['object', 'string'])

# Save the exact column layout dynamically to the DATA folder
feature_columns = list(X.columns)
features_pkl_path = os.path.join(data_folder, 'v2_feature_columns.pkl')
joblib.dump(feature_columns, features_pkl_path)

print(f"      -> Final Matrix Shape: {len(X)} samples x {len(X.columns)} features.")

# 4. Train the Brain
print("[4/5] Training 500-Tree Multi-Input Random Forest...")
print("      (This will use your 32GB RAM heavily for a few minutes...)")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

rf_v2 = RandomForestClassifier(n_estimators=500, n_jobs=-1, random_state=42, class_weight='balanced')
rf_v2.fit(X_train, y_train)

# 5. Evaluate and Save
print("[5/5] Evaluating True Predictive Accuracy...")
predictions = rf_v2.predict(X_test)
accuracy = accuracy_score(y_test, predictions)

print("\n" + "="*60)
print(f"🏆 V2.0 SPECIFIC-DRUG PREDICTION ACCURACY: {accuracy * 100:.2f}%")
print("="*60)
print(classification_report(y_test, predictions, target_names=['Susceptible', 'Resistant']))

model_pkl_path = os.path.join(data_folder, 'v2_multi_input_model.pkl')
joblib.dump(rf_v2, model_pkl_path)
print(f"✅ V2.0 AI Brain saved successfully in: {data_folder}")