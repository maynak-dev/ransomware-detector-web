import streamlit as st
import pandas as pd
import joblib
import tempfile
import os
import traceback

# --- Page Configuration (Must be first Streamlit command) ---
st.set_page_config(page_title="Ransomware Detector", layout="wide")
st.title("🛡️ Ransomware Detection System")
st.markdown("Upload a Windows executable (.exe) file for analysis using machine learning.")

# --- Session State Initialization (Preserves data across reruns) ---
# This prevents reloading the model every time the user interacts.
if 'model_loaded' not in st.session_state:
    st.session_state.model_loaded = False
    st.session_state.model = None
    st.session_state.scaler = None
    st.session_state.feature_columns = None

# --- Load ML Model (with Caching) ---
# This decorator ensures the model is loaded only once, even on page refresh.
@st.cache_resource
def load_model_artifacts():
    """Load the trained model, scaler, and feature list."""
    try:
        model = joblib.load('best_ransomware_model_UPDATED2.pkl')
        scaler = joblib.load('feature_scaler_UPDATED2.pkl')
        with open('feature_columns_UPDATED2.pkl', 'rb') as f:
            feature_columns = joblib.load(f)
        
        st.success("✅ ML Model loaded successfully!")
        st.info(f"**Model Type:** {type(model).__name__} | **Features Expected:** {len(feature_columns)}")
        return model, scaler, feature_columns
    except Exception as e:
        st.error(f"❌ Critical Error loading models: {e}")
        st.stop() # Stop the app if the model fails to load

# Load the model and store in session state
if not st.session_state.model_loaded:
    st.session_state.model, st.session_state.scaler, st.session_state.feature_columns = load_model_artifacts()
    st.session_state.model_loaded = True

# --- Feature Extraction Function (Your Logic) ---
def extract_features_from_pe(filepath):
    """
    Extract features from a PE file. This is YOUR CORE LOGIC.
    You MUST populate the dictionary with ALL features in 'feature_columns'.
    """
    features = {}
    try:
        import pefile
        pe = pefile.PE(filepath)
        
        # EXAMPLE EXTRACTION - YOU MUST COMPLETE THIS FOR ALL YOUR FEATURES
        features = {
            'Machine': pe.FILE_HEADER.Machine,
            'DebugSize': pe.OPTIONAL_HEADER.DATA_DIRECTORY[6].Size,
            'MajorOSVersion': pe.OPTIONAL_HEADER.MajorOperatingSystemVersion,
            'BitcoinAddresses': 0,  # TODO: Implement actual detection
            # CRITICAL: Add ALL other features your model expects here.
            # Use the list in 'st.session_state.feature_columns' as a guide.
        }
        pe.close()
        
        # Fill in any missing features with a default value (e.g., 0)
        for feat in st.session_state.feature_columns:
            if feat not in features:
                features[feat] = 0
        return features
        
    except Exception as e:
        st.error(f"Error parsing PE file: {e}")
        # If parsing fails, return a dictionary of zeros
        return {feat: 0 for feat in st.session_state.feature_columns}

# --- Main Application: File Upload Widget ---
uploaded_file = st.file_uploader("**Choose an executable (.exe) file**", type=['exe'])

if uploaded_file is not None:
    # Display file info
    st.write(f"**Filename:** `{uploaded_file.name}`")
    st.write(f"**Size:** {uploaded_file.size / (1024*1024):.2f} MB")
    
    # Create a temporary file for processing (same as Flask logic)
    with tempfile.NamedTemporaryFile(delete=False, suffix='.exe') as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        tmp_path = tmp_file.name
    
    # Create a placeholder for dynamic status updates
    status_placeholder = st.empty()
    
    try:
        # Step 1: Extract Features
        with st.spinner('🔍 Extracting features from the PE file...'):
            features = extract_features_from_pe(tmp_path)
        status_placeholder.success("✅ Features extracted.")
        
        # Step 2: Prepare DataFrame
        with st.spinner('🧮 Preparing data for the model...'):
            df = pd.DataFrame([features])
            # Ensure correct column order
            df = df[st.session_state.feature_columns]
        
        # Step 3: Scale Features and Predict
        with st.spinner('🤖 Making prediction with ML model...'):
            scaled = st.session_state.scaler.transform(df)
            prediction = st.session_state.model.predict(scaled)[0]
            probabilities = st.session_state.model.predict_proba(scaled)[0]
        
        status_placeholder.empty() # Clear the status spinner
        
        # --- Display Results ---
        st.markdown("---")
        st.subheader("📊 Analysis Result")
        
        # Create two columns for side-by-side display
        col1, col2 = st.columns(2)
        
        with col1:
            # Show a big, clear result
            if prediction == 1:
                st.error(f"## 🚨 MALICIOUS")
                st.metric(label="Ransomware Probability", value=f"{probabilities[1]*100:.1f}%")
            else:
                st.success(f"## ✅ BENIGN")
                st.metric(label="Safety Confidence", value=f"{probabilities[0]*100:.1f}%")
        
        with col2:
            # Show a detailed probability bar chart
            prob_df = pd.DataFrame({
                'Class': ['Benign', 'Malicious'],
                'Probability': [probabilities[0], probabilities[1]]
            })
            st.bar_chart(prob_df.set_index('Class'), use_container_width=True)
        
        # Show detailed probabilities in an expandable section
        with st.expander("📈 View detailed probabilities"):
            st.write(f"**Probability of being Benign:** `{probabilities[0]:.4f}`")
            st.write(f"**Probability of being Malicious/Ransomware:** `{probabilities[1]:.4f}`")
            
    except Exception as e:
        st.error(f"❌ An unexpected error occurred during analysis.")
        with st.expander("Click here to see technical error details (for debugging)"):
            st.code(traceback.format_exc())
    finally:
        # Clean up the temporary file
        try:
            os.unlink(tmp_path)
        except:
            pass

# --- Sidebar for additional info/controls (optional) ---
with st.sidebar:
    st.header("ℹ️ About")
    st.markdown("""
    This tool uses a machine learning model trained on PE file features to detect potential ransomware.
    
    **How it works:**
    1. Upload a Windows `.exe` file.
    2. The app extracts structural features (like header info).
    3. A pre-trained model evaluates these features.
    4. Results show the malware probability.
    
    **Note:** This is a demonstration for my B.Tech project. Always use multiple security tools for critical analysis.
    """)
    
    # Display loaded model info
    if st.session_state.model_loaded:
        st.divider()
        st.caption(f"Model: `{type(st.session_state.model).__name__}`")
        st.caption(f"Features: `{len(st.session_state.feature_columns)}`")
        if st.button("Clear Cache & Reload Model"):
            # Clears the cached model, forcing a reload on next run.
            st.cache_resource.clear()
            st.session_state.model_loaded = False
            st.rerun()

# Footer
st.markdown("---")
st.caption("Ransomware Detection System | Developed by Maynak Dey | B.Tech Final Year Project")
