"""
Styling utilities for the Streamlit UI.
Contains CSS styles and UI enhancement functions.
"""

def get_custom_css():
    """
    Returns the custom CSS for the Streamlit app.
    """
    return """
<style>
    /* Import Google Fonts similar to Swoop website */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap');
    
    /* Overall styling with Swoop Golf colors */
    .main {
        background-color: #ffffff;
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Header styling to match Swoop branding */
    h1, h2, h3 {
        color: #FF8B00;
        font-weight: 600;
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Swoop primary orange */
    .stButton>button {
        background-color: #FF8B00;
        color: white;
        font-family: 'Montserrat', sans-serif;
        font-weight: 500;
    }
    
    /* Chat message styling */
    .stChatMessage {
        border-radius: 12px;
        padding: 0.5rem;
        margin-bottom: 1rem;
        font-family: 'Montserrat', sans-serif;
    }
    
    /* User icon styling */
    .stChatMessageContent[data-testid="stChatMessageContent"] {
        background-color: #f9f9f9;
    }
    
    /* Status message styling */
    .stAlert {
        border-radius: 8px;
        font-family: 'Montserrat', sans-serif;
    }
    
    /* SQL query expander styling */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #FF8B00;
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Add shadow to containers */
    [data-testid="stVerticalBlock"] div:has(> [data-testid="stChatMessage"]) {
        box-shadow: 0 3px 8px rgba(0, 0, 0, 0.1);
    }
    
    /* Sidebar styling */
    .css-1d391kg, .css-12oz5g7 {
        background-color: #f9f9f9;
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Sidebar title styling */
    .css-10oheav {
        color: #FF8B00;
        font-family: 'Montserrat', sans-serif;
        font-weight: 600;
    }
    
    /* Chat input styling */
    .stChatInputContainer {
        border-top: 1px solid #e6e6e6;
        padding-top: 1rem;
    }
    
    /* Status indicators */
    .stStatus {
        background-color: #fff9f0;
        border-left: 3px solid #FF8B00;
    }
    
    /* Success messages */
    .stSuccess {
        background-color: #eaf7ee;
        border-left: 3px solid #FF8B00;
    }

    /* Text styling */
    p, li, div {
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Code blocks */
    code {
        font-family: 'Consolas', 'Monaco', monospace;
    }
    
    /* Chat input text */
    .stChatInput {
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Make links orange */
    a {
        color: #FF8B00 !important;
    }
    
    /* Sidebar headers */
    .css-16idsys p {
        font-family: 'Montserrat', sans-serif;
        font-weight: 500;
    }
    
    /* Reset the assistant avatar completely */
    [data-testid="stChatMessageAvatar"][aria-label="assistant"],
    div[data-testid="stChatMessageAvatarAssistant"] {
        /* Clear any previous background or SVG */
        background-image: none !important;
        background-color: transparent !important;
        position: relative !important;
    }

    /* Use ::before to insert a clean Swoop logo */
    [data-testid="stChatMessageAvatar"][aria-label="assistant"]::before,
    div[data-testid="stChatMessageAvatarAssistant"]::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: url('data:image/svg+xml;base64,PHN2ZyBpZD0iTGF5ZXJfMSIgZGF0YS1uYW1lPSJMYXllciAxIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNzguOTEgMjM5LjY0Ij48ZGVmcz48c3R5bGU+LmNscy0xLCAuY2xzLTIge2ZpbGw6ICNmZmY7fS5jbHMtMSB7ZmlsbC1ydWxlOiBldmVub2RkO308L3N0eWxlPjwvZGVmcz48Zz48cGF0aCBjbGFzcz0iY2xzLTEiIGQ9Ik0yODgsNjVsLTUuNTctMi4wOGMtMzYuNTktMTMuNjgtNDIuMzYtMTUuMzMtNDMuODYtMTUuNTNhNDAuNzEsNDAuNzEsMCwwLDAtNzAuNTEsNC4yOGMtLjg1LS4wNi0xLjctLjExLTIuNTYtLjEzaC0uOTRjLS41NiwwLTEuMTEsMC0xLjY2LDBhNTguOTIsNTguOTIsMCwwLDAtMjIuOCw1QTU4LjExLDU4LjExLDAsMCwwLDExOC40NSw3Mi43TDkuMDksMTc4LjQybDk1LjIyLTUuMTEtMS43Myw5NS4zM0wyMDcuMDksMTUxLjI5YTU5LjYzLDU5LjYzLDAsMCwwLDE1LjY4LTM4LjFjMC0uMTEsMC0uMjMsMC0uMzQsMC0uNjAwLTEuMjAwLTEuOGMwLTEsMC0xLjQ1YzAtLjI0LDAtLjQ5LDAtLjc0LDAtLjg1LS4wNy0xLjY5LS4xNC0yLjU0YTQxLDQxLDAsMCwwLDIxLTI0LjgyLDE1LjU2LDE1LjU2LDAsMCwwLDMuNTctMVpNMjA1LjM4LDc1LjMzYzEsMS4xNSwxLjg5LDIuMzYsMi43NywzLjYuMTcuMjYuMzYuNS41NC43Ni44LDEuMTgsMS41NSwyLjQsMi4yNywzLjY1bC42NywxLjE5Yy42MywxLjE1LDEuMjEsMi4zNCwxLjc1LDMuNTRhNTUuNzEsNTUuNzEsMCwwLDEsNC40NiwxNS41QTM2LjI0LDM2LjI0LDAsMCwxLDE3MC43OSw1Ni41QTU0LjI1LDU0LjI1LDAsMCwxLDIwNSw3NC45M1ptMTIuOTIsMzcuNDN2LjExQTU0LjgyLDU0LjgyLDAsMCwxLDE4NS41NiwxNjFhNTQsNTQsMCwwLDEtMTkuODgsNC41NGwtNTYuNzksMywxLTUyLjY5di0uMTJhNTQuNTYsNTQuNTYsMCwwLDEsNTQtNTkuNzhjLjc4LDAsMS41Ny4wNywyLjM1LjExYTQwLjY4LDQwLjY4LDAsMCwwLDUyLjEsNTIuMWwwLC43YzAsLjI5LDAsLjU4LDAsLjg3czAsLjc3LDAsMS4xNUMyMTguMzIsMTExLjUyLDIxOC4zMiwxMTIuMTQsMjE4LjMsMTEyLjc2Wk0yMC44NywxNzMuMjksMTEwLjE4LDg3Yy0uMzMuNzQtLjcsMS40Ni0xLDIuMjNhNTguODgsNTguODgsMCwwLDAtMy44MywyNi44N2wtLjk1LDUyLjc2Wm04Ny45NC0uMjJMMTY1Ljg4LDE3MGE1OC41Niw1OC41NiwwLDAsMCwyMS40OC00LjkxYy44Mi0uMzYsMS42My0uNzQsMi40Mi0xLjEzTDEwNy4zLDI1Ni42Wm0xMTMuMzEtNzEuNTFhNTkuNTEsNTkuNTEsMCwwLDAtNC4yMi0xNC40N2MtLjE0LS4zMy0uMzMtLjY0LS40OC0xYy0uNTUtMS4yMS0xLjEzLTIuNC0xLjc2LTMuNTdjLS4yOS0uNTItLjU4LTEtLjg4LTEuNTVjLS43NC0xLjI5LTEuNTEtMi41NS0yLjM1LTMuNzhjLS4yMy0uMzQtLjQ3LS42Ni0uNzEtMWMtLjkxLTEuMjgtMS44Ni0yLjUzLTIuODctMy43NGwtLjUxLS41OHEtMS42OS0yLTMuNTctMy44MWwtLjEtLjA5YTU4LjM0LDU4LjM0LDAsMCwwLTE5LjE4LTEyLjM4LDU4LjkzLDU4LjkzLDAsMCwwLTEyLjY3LTMuNDQsMzYuMjksMzYuMjksMCwxLDEsNDkuMyw0OS4zOFptMjIuNi0yNWEzOS43OSwzOS43OSwwLDAsMC0zLjExLTIzLjc4YzQuNDUsMS40NSwxMy45MSw0Ljc5LDMzLjY3LDEyLjE1TDI0NS41NCw3Ni4zNkMyNDUuMjgsNzYuNDcsMjQ1LDc2LjUyLDI0NC43Miw3Ni42MVoiIHRyYW5zZm9ybT0idHJhbnNsYXRlKC05LjA5IC0yOSkiLz48ZWxsaXBzZSBjbGFzcz0iY2xzLTIiIGN4PSIxNTAuMTgiIGN5PSI4NC44o-miniCIgcng9IjE2LjQ0IiByeT0iMTYuNTMiLz48L2c+PC9zdmc+');
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
        z-index: 10;
    }

    /* Hide any original SVG inside the avatar */
    [data-testid="stChatMessageAvatar"][aria-label="assistant"] svg,
    div[data-testid="stChatMessageAvatarAssistant"] svg {
        opacity: 0 !important;
        visibility: hidden !important;
    }
    
    /* Hide status messages in the sidebar */
    div[data-testid="stSidebar"] .stSuccess, 
    div[data-testid="stSidebar"] .stInfo, 
    div[data-testid="stSidebar"] .stWarning {
        display: none !important;
    }
    
    /* Fix any CSS that might be visible in the UI */
    .main p,
    .main div:not([class]) {
        min-height: 0 !important;
    }
    
    /* Hide any text that looks like CSS or code */
    *:not(style):not(script):not(pre):not(code) {
        white-space: normal !important;
    }
</style>
"""

def get_anti_leak_css():
    """
    Returns CSS to prevent code/styling leaks in the UI
    """
    return """
<style>
/* This CSS will ensure no CSS code is visible in the main UI */
.main pre,
.main code {
    display: none;
}

/* Reset any leaked CSS content */
.stApp .main-content > *:not(.element-container):not(.stVerticalBlock) {
    display: none !important;
}

/* Make sure all style tags are hidden */
.stApp style {
    display: none !important;
}

/* Hide any text that contains CSS syntax */
.stApp .main-content *:contains('{') {
    display: none !important;
}
</style>
"""

def apply_styling(st):
    """
    Apply custom styling to the Streamlit app
    
    Args:
        st: Streamlit module
    """
    st.markdown(get_custom_css(), unsafe_allow_html=True)
    st.markdown(get_anti_leak_css(), unsafe_allow_html=True) 