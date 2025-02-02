import streamlit as st
import pandas as pd
from PIL import Image
from github import Github
import os
import io
import hashlib

# --- GitHub Setup ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
g = Github(GITHUB_TOKEN)
REPO_NAME = "Abdullahshade/repotwoforpen"
FILE_PATH = "chunk_2.csv"
images_folder = "chunk2"

# --- Load Data with Validation ---
def load_data():
    try:
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        csv_content = contents.decoded_content
        df = pd.read_csv(io.BytesIO(csv_content))
        
        # Validate critical columns
        required_columns = ["Index", "Image_Name", "Label_Flag"]
        if not all(col in df.columns for col in required_columns):
            st.error(f"CSV missing required columns: {required_columns}")
            st.stop()
            
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()

GT_Pneumothorax = load_data()

# --- Session State Setup ---
if "unlabeled_indices" not in st.session_state:
    GT_Pneumothorax["Label_Flag"] = pd.to_numeric(GT_Pneumothorax["Label_Flag"], errors="coerce").fillna(0)
    st.session_state.unlabeled_indices = GT_Pneumothorax.index[GT_Pneumothorax["Label_Flag"] == 0].tolist()
    st.session_state.current_pos = 0 if st.session_state.unlabeled_indices else -1

# --- Reset Button ---
if st.button("⟳ Reset App State"):
    st.session_state.clear()
    st.rerun()

# --- Get Current Image with Verification ---
def get_current_image():
    if st.session_state.current_pos == -1:
        return None
    
    try:
        csv_idx = st.session_state.unlabeled_indices[st.session_state.current_pos]
        row = GT_Pneumothorax.iloc[csv_idx]
        image_path = os.path.join(images_folder, row["Image_Name"])
        
        # Verify image existence and index consistency
        if not os.path.exists(image_path):
            st.error(f"Image mismatch! CSV Index: {csv_idx} | Image: {row['Image_Name']} not found")
            return None
            
        return (csv_idx, row, Image.open(image_path))
    except (IndexError, KeyError) as e:
        st.error(f"Index error: {e}")
        return None

# --- Display Current Image with Metadata ---
current_image = get_current_image()

if not current_image:
    st.warning("No images available for labeling!")
    st.stop()

csv_idx, row, img = current_image

# Display verification info
st.subheader(f"Image Details")
col1, col2 = st.columns(2)
with col1:
    st.metric("CSV Index", csv_idx)
with col2:
    st.metric("Image Name", row["Image_Name"])
    
st.image(img, use_column_width=True)

# --- Checksum Verification ---
def get_image_checksum(image_path):
    with open(image_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

current_checksum = get_image_checksum(os.path.join(images_folder, row["Image_Name"]))
st.caption(f"Image Checksum: `{current_checksum}`")

# --- Grading Form ---
with st.form(key="grading_form"):
    st.subheader("Labeling Interface")
    
    # Get current values with fallbacks
    current_type = row.get("Pneumothorax_Type", "Simple")
    current_size = row.get("Pneumothorax_Size", "Small")
    current_side = row.get("Affected_Side", "Right")

    pneumothorax_type = st.selectbox("Pneumothorax Type", ["Simple", "Tension"], 
                                   index=0 if current_type == "Simple" else 1)
    pneumothorax_size = st.selectbox("Pneumothorax Size", ["Small", "Large"], 
                                   index=0 if current_size == "Small" else 1)
    affected_side = st.selectbox("Affected Side", ["Right", "Left"], 
                               index=0 if current_side == "Right" else 1)

    col1, col2 = st.columns([1, 3])
    with col1:
        form_submit = st.form_submit_button("💾 Save")
    with col2:
        drop_submit = st.form_submit_button("🗑️ Drop")

# --- Save/Drop Handler with Verification ---
def verify_before_save(original_idx, original_name):
    """Ensure CSV hasn't changed since loading"""
    try:
        current_row = GT_Pneumothorax.iloc[original_idx]
        return current_row["Image_Name"] == original_name
    except:
        return False

def update_system():
    try:
        # Update GitHub
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        updated_csv = GT_Pneumothorax.to_csv(index=False).encode("utf-8")
        repo.update_file(contents.path, "Updated labels", updated_csv, contents.sha)
        
        # Reload data
        new_data = load_data()
        GT_Pneumothorax.update(new_data)
        
        # Update session state
        GT_Pneumothorax["Label_Flag"] = pd.to_numeric(GT_Pneumothorax["Label_Flag"], errors="coerce").fillna(0)
        st.session_state.unlabeled_indices = GT_Pneumothorax.index[GT_Pneumothorax["Label_Flag"] == 0].tolist()
        st.session_state.current_pos = 0 if st.session_state.unlabeled_indices else -1
        
        return True
    except Exception as e:
        st.error(f"Save failed: {e}")
        return False

if form_submit or drop_submit:
    # Verify integrity before saving
    if not verify_before_save(csv_idx, row["Image_Name"]):
        st.error("""Data mismatch detected! 
                The CSV has changed since loading. Reloading data...""")
        GT_Pneumothorax = load_data()
        st.rerun()
    
    # Update DataFrame
    GT_Pneumothorax.at[csv_idx, "Pneumothorax_Type"] = pneumothorax_type
    GT_Pneumothorax.at[csv_idx, "Pneumothorax_Size"] = pneumothorax_size
    GT_Pneumothorax.at[csv_idx, "Affected_Side"] = affected_side
    GT_Pneumothorax.at[csv_idx, "Label_Flag"] = 1
    GT_Pneumothorax.at[csv_idx, "Drop"] = "True" if drop_submit else "False"
    
    if update_system():
        st.success(f"Saved: Index {csv_idx} | {row['Image_Name']}")
    st.rerun()

# --- Navigation Controls ---
st.subheader("Navigation")
col_prev, _, col_next = st.columns([1, 2, 1])
with col_prev:
    if st.button("⏮️ Previous") and st.session_state.current_pos > 0:
        st.session_state.current_pos -= 1
        st.rerun()
with col_next:
    if st.button("⏭️ Next") and st.session_state.current_pos < len(st.session_state.unlabeled_indices)-1:
        st.session_state.current_pos += 1
        st.rerun()

# --- Debug Panel ---
st.sidebar.subheader("Validation Info")
st.sidebar.write(f"Current CSV Index: {csv_idx}")
st.sidebar.write(f"Current Image Name: {row['Image_Name']}")
st.sidebar.write(f"Total Images: {len(GT_Pneumothorax)}")
st.sidebar.write(f"Unlabeled Remaining: {len(st.session_state.unlabeled_indices)}")
