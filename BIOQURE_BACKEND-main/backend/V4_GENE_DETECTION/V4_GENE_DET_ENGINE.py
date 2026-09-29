import os

# --- 1. SETUP PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(BASE_DIR, ".."))
# IMPORTANT: Make sure this points to your actual CARD_DB.fasta file!
CARD_FASTA = os.path.join(project_root, 'Main_Model', 'CARD_DB.fasta')

# --- 2. BIOLOGICAL HEURISTICS ---
def classify_gene_type(gene_name):
    name = gene_name.lower()
    if any(x in name for x in ['bla', 'ndm', 'kpc', 'oxa', 'ctx', 'vim', 'shv', 'tem']): return "Beta-Lactamase / Carbapenemase"
    if any(x in name for x in ['tet', 'otr']): return "Tetracycline Resistance"
    if any(x in name for x in ['mec', 'pbp']): return "Methicillin Resistance"
    if any(x in name for x in ['sul', 'dfr']): return "Sulfonamide/Trimethoprim Resistance"
    if any(x in name for x in ['qnr', 'gyr', 'par']): return "Fluoroquinolone Resistance"
    if 'mcr' in name: return "Colistin Resistance"
    if any(x in name for x in ['erm', 'mef']): return "Macrolide Resistance"
    if any(x in name for x in ['aac', 'ant', 'aph', 'aad']): return "Aminoglycoside Resistance"
    if 'van' in name: return "Vancomycin Resistance"
    return "Acquired Resistance Mechanism"

# The "Reverse Complement" tool (Because DNA is double-stranded!)
def get_reverse_complement(seq):
    complement = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C'}
    # Reverse the string and swap the letters
    return "".join(complement.get(base, base) for base in reversed(seq))

# --- 3. FASTA PARSER ---
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
        print(f"❌ ERROR: Could not find {filepath}. Check your file name!")
        return None

# --- 4. EXECUTION ---
print("="*60)
print("🔬 ISOLATED V4 ENGINE TEST (CARD DB SCANNER)")
print("="*60)

patient_file = input("🧬 Drag Patient DNA (.fna) here: ").strip().strip('"').strip("'")

try:
    with open(patient_file, 'r', encoding='utf-8', errors='ignore') as f:
        sequence = "".join([line.strip() for line in f if not line.startswith(">")]).upper()
        print(f"✅ DNA Loaded. Length: {len(sequence):,} base pairs.")
except Exception as e:
    print(f"❌ Error reading DNA file: {e}")
    exit()

print("⏳ Loading McMaster CARD Database...")
card_db = load_card_database(CARD_FASTA)

if not card_db:
    exit()

print(f"✅ Loaded {len(card_db)} resistance signatures.")
print("🔍 Scanning genome (Checking Forward & Reverse strands)...")

detected_genes = []

for header, gene_sequence in card_db.items():
    if len(gene_sequence) > 60:
        # Take the first 60 bases as the signature
        forward_snippet = gene_sequence[:60]
        reverse_snippet = get_reverse_complement(forward_snippet)
        
        # Check both strands of the patient's DNA
        if forward_snippet in sequence or reverse_snippet in sequence:
            
            # Extract clean names from the messy FASTA header
            parts = header.split("|")
            gene_name = parts[-1] if len(parts) > 1 else header.replace(">", "")
            
            aro_id = "ARO:Unknown"
            for part in parts:
                if "ARO:" in part:
                    aro_id = part
                    break
            
            gene_class = classify_gene_type(gene_name)
            detected_genes.append((gene_name, aro_id, gene_class))

# --- 5. RESULTS ---
print("-" * 60)
if detected_genes:
    print(f"⚠️ CRITICAL: V4 aligned {len(detected_genes)} CARD resistance genes!")
    print("\n[ TOP 10 CONFIRMED HITS ]")
    
    unique_genes = {g[0]: g for g in detected_genes} 
    
    for name, data in list(unique_genes.items())[:10]: 
        gene_name, aro, g_type = data
        print(f" 🧬 [{aro}] {gene_name}")
        print(f"    └─ Mechanism: {g_type}")
else:
    print("✅ V4 Scan Clear: No known CARD resistance genes aligned.")
print("="*60)