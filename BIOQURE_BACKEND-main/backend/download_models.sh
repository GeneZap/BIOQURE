#!/bin/bash
# Download AI model files from GitHub releases on Render startup
# Models are too large (~323MB) to commit to Git; stored in GitHub Releases

set -e

echo "🔄 Initializing AI models for GeneZap backend..."

# Get GitHub repo info from environment or use default
GITHUB_REPO="${GITHUB_REPO:-GeneZap/BV-BRC_Dataset}"
RELEASE_TAG="${RELEASE_TAG:-v1.0-models}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"  # Optional: for private repos

# Model file destinations (match CV_HACKATHON_MODEL_DATASET structure)
MODEL_V1_DIR="/app/CV_HACKATHON_MODEL_DATASET/V1_Model_Output"
MODEL_V2_DIR="/app/CV_HACKATHON_MODEL_DATASET/V2_Model_Output"
MODEL_V3_DIR="/app/CV_HACKATHON_MODEL_DATASET/V3_Model_Output"

# Create directories if they don't exist
mkdir -p "$MODEL_V1_DIR"
mkdir -p "$MODEL_V2_DIR"
mkdir -p "$MODEL_V3_DIR"

# Download URL base
RELEASE_URL="https://github.com/${GITHUB_REPO}/releases/download/${RELEASE_TAG}"

# Function to download a file with retry
download_model() {
    local filename=$1
    local destination=$2
    # GitHub Release stores files flat (no folder structure in URL)
    # Extract just the filename from the path
    local basename=$(basename "$filename")
    local url="${RELEASE_URL}/${basename}"
    
    if [ -f "$destination" ]; then
        echo "✅ $filename already exists, skipping download"
        return 0
    fi
    
    echo "📥 Downloading $filename..."
    
    # Try up to 3 times
    for attempt in 1 2 3; do
        if curl -L -f --progress-bar -o "$destination" "$url" 2>&1; then
            echo "✅ Downloaded $filename ($(du -h "$destination" | cut -f1))"
            return 0
        fi
        
        if [ $attempt -lt 3 ]; then
            echo "⚠️  Download attempt $attempt failed, retrying..."
            sleep 2
        fi
    done
    
    echo "❌ Failed to download $filename after 3 attempts"
    return 1
}

# Download models
echo "📦 Fetching AI model files from GitHub Release: ${RELEASE_TAG}"
echo "📊 Expected total: ~323 MB (may take 2-5 minutes on first startup)"

# ===== V1 Models =====
echo ""
echo "🔹 Downloading V1 (Pathogen Identification) models..."
download_model "V1_Model_Output/bacterial_id_model.pkl" "$MODEL_V1_DIR/bacterial_id_model.pkl" || true
download_model "V1_Model_Output/antibiotic_strength_model.pkl" "$MODEL_V1_DIR/antibiotic_strength_model.pkl" || true
download_model "V1_Model_Output/label_encoder_id.pkl" "$MODEL_V1_DIR/label_encoder_id.pkl" || true
download_model "V1_Model_Output/label_encoder_str.pkl" "$MODEL_V1_DIR/label_encoder_str.pkl" || true
download_model "V1_Model_Output/v1_feature_columns.pkl" "$MODEL_V1_DIR/v1_feature_columns.pkl" || true

# ===== V2 Models =====
echo ""
echo "🔹 Downloading V2 (Pharmacology) models..."
download_model "V2_Model_Output/v2_multi_input_model.pkl" "$MODEL_V2_DIR/v2_multi_input_model.pkl" || true
download_model "V2_Model_Output/v2_multi_input_model_FIXED.pkl" "$MODEL_V2_DIR/v2_multi_input_model_FIXED.pkl" || true
download_model "V2_Model_Output/v2_feature_columns.pkl" "$MODEL_V2_DIR/v2_feature_columns.pkl" || true
download_model "V2_Model_Output/v2_feature_columns_FIXED.pkl" "$MODEL_V2_DIR/v2_feature_columns_FIXED.pkl" || true
download_model "V2_Model_Output/v2_imputer_FIXED.pkl" "$MODEL_V2_DIR/v2_imputer_FIXED.pkl" || true

# ===== V3 Models (CNN/CGR) =====
echo ""
echo "🔹 Downloading V3 (CNN/CGR Visual Analysis) models..."
download_model "V3_Model_Output/v3_vision_model.h5" "$MODEL_V3_DIR/v3_vision_model.h5" || true
download_model "V3_Model_Output/best_v3_vision_model.h5" "$MODEL_V3_DIR/best_v3_vision_model.h5" || true

echo ""
echo "✅ Model initialization complete"
echo "🚀 Starting GeneZap API server..."
