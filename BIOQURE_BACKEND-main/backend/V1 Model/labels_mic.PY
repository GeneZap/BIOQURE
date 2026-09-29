import csv
import requests
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIG ---
csv_file = "BVBRC_genome_amr.csv"  
output_folder = "bacterial_dna"
MAX_THREADS = 5  # DO NOT set this higher than 10 to avoid an IP ban

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# --- THE WORKER (Downloads a single file) ---
def download_genome(gid):
    save_path = os.path.join(output_folder, f"{gid}.fna")
    
    # 1. Instant Skip if already downloaded
    if os.path.exists(save_path):
        return f"⏭️ SKIPPED: {gid} (Already exists)"

    url = f"https://www.bv-brc.org/api/genome_sequence/?eq(genome_id,{gid})&limit(25000)&http_accept=application/dna+fasta"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/dna+fasta'
    }
    
    # 2. Network Resilience (Retry up to 3 times if it fails)
    for attempt in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=60)
            
            # If server says "Too Many Requests", wait 5 seconds and retry
            if r.status_code == 429:
                time.sleep(5)
                continue
                
            if r.status_code == 200 and r.text.strip().startswith(">"):
                with open(save_path, "w", encoding="utf-8") as out:
                    out.write(r.text)
                return f"✅ SUCCESS: {gid}"
            else:
                return f"❌ FAILED: {gid} (Status {r.status_code})"
                
        except Exception as e:
            time.sleep(2) # Brief pause before retry on network hiccup
            
    return f"❌ FAILED: {gid} (Network timeout after 3 attempts)"

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    try:
        with open(csv_file, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            id_col = next((c for c in reader.fieldnames if 'genome' in c.lower() and 'id' in c.lower()), None)
            
            if not id_col:
                print(f"Error: Could not find 'Genome ID' column.")
                exit()

            genome_ids = list(set(row[id_col].strip() for row in reader if row[id_col]))
            print(f"Found {len(genome_ids)} total genomes to process.")
            print(f"Initiating Hyper-Drive with {MAX_THREADS} simultaneous threads...\n")

            # 3. The Thread Pool Manager
            success_count = 0
            with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                # Submit all tasks to the pool
                future_to_gid = {executor.submit(download_genome, gid): gid for gid in genome_ids}
                
                # Process results as they finish, regardless of order
                for i, future in enumerate(as_completed(future_to_gid)):
                    result = future.result()
                    print(f"[{i+1}/{len(genome_ids)}] {result}")
                    if "SUCCESS" in result or "SKIPPED" in result:
                        success_count += 1

            print(f"\n🚀 Process Complete! {success_count}/{len(genome_ids)} files are ready in '{output_folder}'.")

    except FileNotFoundError:
        print(f"Error: Could not find '{csv_file}'")