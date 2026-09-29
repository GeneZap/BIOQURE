import os
import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.preprocessing.image import ImageDataGenerator

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "CNN_CGR_DATASET")
OUTPUT_DIR = os.path.join(BASE_DIR, "V3_Model_Output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("⚙️ Initializing HD Vision Brain Training...")

datagen = ImageDataGenerator(rescale=1./255, validation_split=0.2)

# UPGRADED to 256x256
train_gen = datagen.flow_from_directory(
    DATASET_DIR,
    target_size=(256, 256), 
    batch_size=16,
    class_mode='binary',
    subset='training'
)

val_gen = datagen.flow_from_directory(
    DATASET_DIR,
    target_size=(256, 256), 
    batch_size=16,
    class_mode='binary',
    subset='validation'
)

print(f"🧠 Class Mapping Locked: {train_gen.class_indices}")
# NOTE: Check your terminal! If it prints {'RESISTANT': 0, 'SUSCEPTIBLE': 1}, 
# you know 0 means Resistant!

# UPGRADED Input Shape to (256, 256, 3)
model = models.Sequential([
    layers.Conv2D(32, (3, 3), activation='relu', input_shape=(256, 256, 3)),
    layers.MaxPooling2D(2, 2),
    layers.Conv2D(64, (3, 3), activation='relu'),
    layers.MaxPooling2D(2, 2),
    layers.Conv2D(128, (3, 3), activation='relu'),
    layers.MaxPooling2D(2, 2),
    layers.Flatten(),
    layers.Dense(128, activation='relu'),
    layers.Dropout(0.5), 
    layers.Dense(1, activation='sigmoid') 
])

model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

print("🚀 Training HD Model...")
history = model.fit(train_gen, validation_data=val_gen, epochs=10)

model_path = os.path.join(OUTPUT_DIR, "v3_vision_model.h5")
model.save(model_path)
print(f"✅ CORE FIXED: V3 HD Vision Brain saved to {model_path}")