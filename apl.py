import streamlit as st
import pandas as pd
from PIL import Image
import os

# Define the paths to your local files
images_folder = "Chunk1"  # Path to your images folder (update as needed)
csv_file_path = "chunk_1.csv"  # Path to your CSV file (update as needed)

# Load metadata (GT_Pneumothorax.csv)
try:
    GT_Pneumothorax = pd.read_csv(csv_file_path)
except Exception as e:
    st.error(f"Failed to load metadata: {e}")
    st.stop()

# App title
st.title("Pneumothorax Grading and Image Viewer")

# Initialize session state for the current index
if "current_index" not in st.session_state:
    st.session_state.current_index = 0

# Loop to skip labeled images automatically
while st.session_state.current_index < len(GT_Pneumothorax):
    row = GT_Pneumothorax.iloc[st.session_state.current_index]
    if row["Label_Flag"] == 1:
        st.session_state.current_index += 1  # Skip labeled images
    else:
        break

# Ensure there are still images left to process
if st.session_state.current_index >= len(GT_Pneumothorax):
    st.success("All images have been labeled! No more images to process.")
    st.stop()

# Get the current row (image and metadata)
row = GT_Pneumothorax.iloc[st.session_state.current_index]

# Get the current image path (based on Image_Name)
image_path = os.path.join(images_folder, row["Image_Name"])

# Check if the image file exists and display it
if os.path.exists(image_path):
    img = Image.open(image_path)
    st.image(
        img,
        caption=f"Image index: {row['Index']} | Image Name: {row['Image_Name']}",
        use_column_width=True
    )
else:
    st.error(f"Image {row['Image_Name']} not found in {images_folder}.")
    st.stop()

# Handling user input for Pneumothorax type and measurements
drop_checkbox = st.button("Drop")
pneumothorax_type = st.selectbox("Pneumothorax Type", ["Simple", "Tension"], index=0)
pneumothorax_Size = st.selectbox("Pneumothorax Size", ["Small", "Large"], index=0)
Affected_Side = st.selectbox("Affected Side", ["Right", "Left"], index=0)

# Checkbox to save changes
save_changes = st.button("Save Changes")
if drop_checkbox:
    GT_Pneumothorax.at[st.session_state.current_index, "Label_Flag"] = 1
    GT_Pneumothorax.at[st.session_state.current_index, "Drop"] = drop_checkbox
    try:
        GT_Pneumothorax.to_csv(csv_file_path, index=False)
        st.success(f"Changes saved for Image {row['Image_Name']}!")
    except Exception as e:
        st.error(f"Failed to save changes: {e}")
# Mark as labeled
elif save_changes:
    # Update the metadata locally
    GT_Pneumothorax.at[st.session_state.current_index, "Pneumothorax_Type"] = pneumothorax_type
    GT_Pneumothorax.at[st.session_state.current_index, "Pneumothorax_Size"] = pneumothorax_Size
    GT_Pneumothorax.at[st.session_state.current_index, "Affected_Side"] = Affected_Side
    GT_Pneumothorax.at[st.session_state.current_index, "Label_Flag"] = 1  # Mark as labeled
    GT_Pneumothorax.at[st.session_state.current_index, "Drop"] = "False"

    # Save the updated CSV locally
    try:
        GT_Pneumothorax.to_csv(csv_file_path, index=False)
        st.success(f"Changes saved for Image {row['Image_Name']}!")
    except Exception as e:
        st.error(f"Failed to save changes: {e}")

# Navigation buttons (Previous / Next)
col1, col2 = st.columns(2)
if col1.button("Previous") and st.session_state.current_index > 0:
    st.session_state.current_index -= 1
if col2.button("Next") and st.session_state.current_index < len(GT_Pneumothorax) - 1:
    st.session_state.current_index += 1
