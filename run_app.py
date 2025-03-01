"""
Entry point for the Swoop AI Streamlit app.
Simply imports and runs the main app module.
"""

import os
import sys
import streamlit
import traceback

# Make sure the app directory is in the Python path
app_dir = os.path.dirname(os.path.abspath(__file__))
if app_dir not in sys.path:
    sys.path.append(app_dir)

if __name__ == "__main__":
    try:
        # Import and run the app
        from app.main import run_app
        run_app()
    except ImportError as e:
        # Provide helpful error message if import fails
        error_message = f"Error importing app modules: {str(e)}"
        
        # Check if we're running in the context of Streamlit
        is_streamlit = 'streamlit.runtime' in sys.modules
        
        if is_streamlit:
            # If in Streamlit, show a nice error message
            import streamlit as st
            st.error(error_message)
            st.error(traceback.format_exc())
            st.info("Make sure you've created all required app modules and installed dependencies.")
        else:
            # If running directly, print to console
            print(error_message)
            print(traceback.format_exc())
            print("Make sure you've created all required app modules and installed dependencies.")
    except Exception as e:
        # Handle other errors
        error_message = f"Error during application startup: {str(e)}"
        
        # Check if we're running in the context of Streamlit
        is_streamlit = 'streamlit.runtime' in sys.modules
        
        if is_streamlit:
            # If in Streamlit, show a nice error message
            import streamlit as st
            st.error(error_message)
            st.error(traceback.format_exc())
        else:
            # If running directly, print to console
            print(error_message)
            print(traceback.format_exc()) 