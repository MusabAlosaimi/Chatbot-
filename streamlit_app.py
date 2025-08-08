import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import os
from datetime import datetime
import re

# Configure page
st.set_page_config(
    page_title="Sirar-DMO-Chatbot", 
    page_icon="🤖", 
    layout="wide"
)

# Initialize session state
if 'conversation_stage' not in st.session_state:
    st.session_state.conversation_stage = 'initial'
if 'user_department' not in st.session_state:
    st.session_state.user_department = ''
if 'collected_words' not in st.session_state:
    st.session_state.collected_words = []
if 'pending_classification' not in st.session_state:
    st.session_state.pending_classification = []
if 'classified_words' not in st.session_state:
    st.session_state.classified_words = []
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Prompt Template for Gemini
SYSTEM_PROMPT = """
You are Sirar-DMO-Chatbot, a specialized Document Management Organization assistant. 

YOUR ONLY PURPOSE is to:
1. Collect department information from employees
2. Collect commonly used words/terms in their work
3. Help classify those words as Internal, Public, or Confidential

STRICT RULES:
- DO NOT respond to any questions outside of keyword collection and classification
- DO NOT provide general information, advice, or assistance on other topics
- DO NOT engage in casual conversation
- If asked about anything else, respond ONLY with: "I'm sorry, I can only help with collecting and classifying workplace keywords for document management. Please tell me about the words you commonly use in your work."

ALLOWED TOPICS ONLY:
- Department identification
- Workplace terminology collection
- Word classification (Internal/Public/Confidential)
- File saving and data organization

Stay focused on your mission: collecting and classifying workplace keywords.
"""

# ==================== SECURE API KEY HANDLING ====================

def get_api_key():
    """Get API key from Streamlit secrets or manual input"""
    api_key = None
    
    # Method 1: Streamlit Secrets (RECOMMENDED)
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.sidebar.success("🔐 API Key loaded from Streamlit Secrets")
        return api_key
    except KeyError:
        st.sidebar.info("💡 No API key found in Streamlit Secrets")
    except Exception as e:
        st.sidebar.error(f"Error accessing secrets: {str(e)}")
    
    # Method 2: Environment Variables (for local development)
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key:
            st.sidebar.success("🔐 API Key loaded from Environment Variable")
            return api_key
    except:
        pass
    
    # Method 3: Manual input (fallback)
    st.sidebar.warning("⚠️ Please configure API key in Streamlit Secrets")
    with st.sidebar.expander("🔑 Manual API Key (Not Recommended)", expanded=False):
        api_key = st.text_input("Enter Gemini API Key:", type="password", help="This is not secure for production use")
        if api_key:
            st.warning("⚠️ Manual input is not secure. Use Streamlit Secrets instead.")
    
    return api_key

# Data storage functions
def save_to_excel(data):
    """Save classified words to Excel file"""
    try:
        df = pd.DataFrame(data)
        filename = f"sirar_dmo_keywords_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(filename, index=False)
        return filename
    except Exception as e:
        st.error(f"Error saving to Excel: {str(e)}")
        return None

def save_to_json(data):
    """Save classified words to JSON file"""
    try:
        filename = f"sirar_dmo_keywords_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return filename
    except Exception as e:
        st.error(f"Error saving to JSON: {str(e)}")
        return None

def is_off_topic(user_input):
    """Check if user input is off-topic"""
    off_topic_keywords = [
        'weather', 'news', 'joke', 'story', 'recipe', 'music', 'movie', 'game', 
        'sports', 'politics', 'religion', 'health', 'medical', 'code', 'programming',
        'math', 'calculate', 'translate', 'how to', 'what is', 'who is', 'when is',
        'where is', 'why is', 'help me', 'can you', 'tell me about', 'explain'
    ]
    
    work_keywords = ['work', 'job', 'office', 'document', 'word', 'term', 'memo', 'report', 'department']
    
    input_lower = user_input.lower()
    has_off_topic = any(keyword in input_lower for keyword in off_topic_keywords)
    has_work_context = any(keyword in input_lower for keyword in work_keywords)
    
    return has_off_topic and not has_work_context

# ==================== SIDEBAR CONFIGURATION ====================

st.sidebar.title("🔐 Secure Sirar-DMO-Chatbot")
st.sidebar.markdown("### API Configuration")

# Important restrictions notice
st.sidebar.error("🚫 **RESTRICTED BOT**\nThis chatbot ONLY helps with:\n• Department identification\n• Collecting work keywords\n• Classifying terms\n\nIt will NOT answer general questions!")

# Streamlit Secrets Instructions
with st.sidebar.expander("📖 How to Setup Streamlit Secrets", expanded=False):
    st.markdown("""
    **For Streamlit Cloud/Production:**
    1. Go to your app settings
    2. Click on "Secrets" tab
    3. Add this TOML format:
    ```toml
    GEMINI_API_KEY = "your_actual_api_key_here"
    ```
    
    **For Local Development:**
    1. Create `.streamlit/secrets.toml` file
    2. Add the same content above
    3. Never commit this file to git!
    
    **Alternative - Environment Variable:**
    ```bash
    export GEMINI_API_KEY="your_api_key"
    ```
    """)

# Get API key using secure methods
api_key = get_api_key()

# Configure Gemini if API key is available
model = None
if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        st.sidebar.success("✅ Gemini API configured successfully!")
    except Exception as e:
        st.sidebar.error(f"❌ Error configuring Gemini API: {str(e)}")
        model = None
else:
    st.sidebar.warning("⚠️ Please configure your API key")

# Classification options
st.sidebar.markdown("### Word Classifications")
classification_options = ["Internal", "Public", "Confidential"]

# ==================== MAIN INTERFACE ====================

st.title("🤖 Sirar-DMO-Chatbot")
st.markdown("### Document Management Organization - Keyword Collector")

# Security notice
st.info("🔐 **Secure Application**: API keys are handled securely using Streamlit Secrets")

# Important notice about chatbot restrictions
st.warning("⚠️ **Important**: This chatbot is specialized for collecting and classifying workplace keywords only. It will not respond to general questions, requests for information, or off-topic conversations.")

# Display current session info
if st.session_state.user_department:
    st.info(f"👤 Current Department: {st.session_state.user_department}")

# Chat interface
st.markdown("### 💬 Chat Interface")

# Display chat history
for message in st.session_state.chat_history:
    if message['role'] == 'assistant':
        with st.chat_message("assistant"):
            st.write(message['content'])
    else:
        with st.chat_message("user"):
            st.write(message['content'])

# User input
user_input = st.chat_input("Type your message here...")

if user_input and model:
    # Add user message to history
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    
    # Check for off-topic questions first
    if is_off_topic(user_input) and st.session_state.conversation_stage != 'initial':
        bot_response = "I'm sorry, I can only help with collecting and classifying workplace keywords for document management. Please tell me about the words you commonly use in your work."
    
    # Process based on conversation stage
    elif st.session_state.conversation_stage == 'initial':
        # Check if user is asking off-topic questions even at start
        if is_off_topic(user_input):
            bot_response = "I'm sorry, I can only help with collecting and classifying workplace keywords for document management. What department do you work in? (e.g., HR, Finance, IT, Marketing, etc.)"
        else:
            # Initial greeting and department collection
            st.session_state.user_department = user_input
            bot_response = f"Great! I see you work in {st.session_state.user_department}. As a {st.session_state.user_department} employee, what are some words or terms you often write or use in your work? For example: 'memo', 'report', 'evaluation', 'policy', etc. Please list them separated by commas."
            st.session_state.conversation_stage = 'collect_words'
        
    elif st.session_state.conversation_stage == 'collect_words':
        # Extract words from input
        words = [word.strip() for word in user_input.split(',')]
        words = [word for word in words if len(word) > 2]  # Filter short words
        
        if words and not is_off_topic(user_input):
            st.session_state.collected_words.extend(words)
            st.session_state.pending_classification = words.copy()
            st.session_state.conversation_stage = 'classify_words'
            
            # Start classification process
            current_word = st.session_state.pending_classification[0]
            bot_response = f"Thank you! I collected these words: {', '.join(words)}\n\nNow, let's classify them. How would you classify the word '{current_word}'? Please choose:\n\n1. **Internal** - Used within the organization only\n2. **Public** - Can be shared publicly\n3. **Confidential** - Sensitive information\n\nPlease type: Internal, Public, or Confidential"
        else:
            bot_response = "Please provide work-related words or terms you commonly use, separated by commas. For example: 'memo, report, evaluation, meeting'"
            
    elif st.session_state.conversation_stage == 'classify_words':
        # Classify the collected words
        if st.session_state.pending_classification:
            current_word = st.session_state.pending_classification[0]
            
            # Process classification
            classification = user_input.strip().title()
            if classification in classification_options:
                classified_word = {
                    'word': current_word,
                    'classification': classification,
                    'department': st.session_state.user_department,
                    'timestamp': datetime.now().isoformat()
                }
                st.session_state.classified_words.append(classified_word)
                st.session_state.pending_classification.pop(0)
                
                if st.session_state.pending_classification:
                    next_word = st.session_state.pending_classification[0]
                    bot_response = f"✅ '{current_word}' classified as {classification}.\n\nNext word: '{next_word}' - How would you classify this? (Internal/Public/Confidential)"
                else:
                    bot_response = "🎉 All words classified! Would you like to:\n\n1. Add more words\n2. Download the results\n3. Start over\n\nType 'more', 'download', or 'restart'"
                    st.session_state.conversation_stage = 'final_options'
            else:
                bot_response = f"Please choose a valid classification for '{current_word}': Internal, Public, or Confidential"
                
    elif st.session_state.conversation_stage == 'final_options':
        # Handle final options
        option = user_input.lower().strip()
        if 'more' in option:
            bot_response = "Please provide more words you commonly use, separated by commas:"
            st.session_state.conversation_stage = 'collect_words'
        elif 'download' in option:
            bot_response = "📁 Preparing your downloads...\n\nYour classified keywords are ready for download!"
            st.session_state.ready_for_download = True
        elif 'restart' in option:
            # Reset session
            for key in ['conversation_stage', 'user_department', 'collected_words', 'pending_classification', 'classified_words', 'chat_history']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        else:
            bot_response = "Please type 'more' to add more words, 'download' to get your results, or 'restart' to begin again."
    
    else:
        bot_response = "I'm sorry, I can only help with collecting and classifying workplace keywords for document management."
    
    # Add bot response to history
    st.session_state.chat_history.append({"role": "assistant", "content": bot_response})
    
    # Rerun to update chat display
    st.rerun()

# ==================== SIDEBAR PROGRESS & DOWNLOADS ====================

st.sidebar.markdown("### 📊 Progress")
if st.session_state.classified_words:
    st.sidebar.markdown(f"**Classified Words:** {len(st.session_state.classified_words)}")
    st.sidebar.markdown(f"**Pending:** {len(st.session_state.pending_classification)}")
    
    # Show classified words summary
    if st.sidebar.checkbox("Show classified words"):
        for word_data in st.session_state.classified_words:
            st.sidebar.write(f"• {word_data['word']} → {word_data['classification']}")

# Download section
if st.session_state.classified_words:
    st.sidebar.markdown("### 📁 Download Results")
    
    if st.sidebar.button("💾 Generate Downloads"):
        with st.sidebar:
            with st.spinner("Generating files..."):
                # Save to Excel
                excel_file = save_to_excel(st.session_state.classified_words)
                
                # Save to JSON
                json_data = {
                    'department': st.session_state.user_department,
                    'collection_date': datetime.now().isoformat(),
                    'classified_words': st.session_state.classified_words
                }
                json_file = save_to_json(json_data)
                
                if excel_file and json_file:
                    st.success("✅ Files generated successfully!")
                    st.info(f"📊 Excel: {excel_file}")
                    st.info(f"📄 JSON: {json_file}")
                else:
                    st.error("❌ Error generating files")

# Initial greeting
if not st.session_state.chat_history and model:
    initial_message = "👋 Hello! I'm Sirar-DMO-Chatbot, your specialized Document Management Organization assistant. \n\n⚠️ **Please note**: I can ONLY help with collecting and classifying workplace keywords. I cannot answer general questions or provide other assistance.\n\nTo get started: What department do you work in? (e.g., HR, Finance, IT, Marketing, etc.)"
    st.session_state.chat_history.append({"role": "assistant", "content": initial_message})
    st.rerun()

# ==================== FOOTER ====================

st.markdown("---")
st.markdown("**Sirar-DMO-Chatbot** - Document Management Organization Keyword Collector | Built with Streamlit & Gemini AI")

# Display sample data structure in expander
with st.expander("📋 Sample Data Structure"):
    sample_data = {
        "word": "memo",
        "classification": "Internal",
        "department": "HR",
        "timestamp": "2024-01-15T10:30:00"
    }
    st.json(sample_data)

# Security information
with st.expander("🔐 Security Information"):
    st.markdown("""
    **API Key Security:**
    - ✅ Streamlit Secrets (Recommended)
    - ✅ Environment Variables (Local dev)
    - ⚠️ Manual input (Not recommended for production)
    
    **Data Security:**
    - All conversations are session-based
    - No data is stored permanently unless downloaded
    - Files are generated locally
    """)
