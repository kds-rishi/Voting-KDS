# streamlit_survey_app.py
# Streamlit app that handles all data through Google Sheets only

import streamlit as st
import pandas as pd
import json
from urllib.parse import urlparse
from typing import Optional

# ----------------------------
# Configuration
# ----------------------------
def get_config():
    """Get configuration from secrets or use defaults"""
    try:
        SHEET_URL = st.secrets["SHEET_URL"]
        SERVICE_ACCOUNT_INFO = st.secrets["SERVICE_ACCOUNT_INFO"]
    except KeyError as e:
        st.error(f"""
        Missing configuration in Streamlit secrets. Please add the following to `.streamlit/secrets.toml`:
        
        ```toml
        SHEET_URL = "your_google_sheets_url_here"
        
        [SERVICE_ACCOUNT_INFO]
        type = "service_account"
        project_id = "your_project_id"
        private_key_id = "your_private_key_id"
        private_key = "your_private_key"
        client_email = "your_client_email"
        client_id = "your_client_id"
        auth_uri = "https://accounts.google.com/o/oauth2/auth"
        token_uri = "https://oauth2.googleapis.com/token"
        auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
        client_x509_cert_url = "your_cert_url"
        ```
        
        Error: {str(e)}
        """)
        st.stop()
    return SHEET_URL, SERVICE_ACCOUNT_INFO

REQUIRED_DOMAIN = "@keydynamicssolutions"

# ----------------------------
# Google Sheets helpers
# ----------------------------

@st.cache_resource
def get_gspread_client():
    """Initialize and cache the Google Sheets client"""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        st.error("Missing required packages. Install with: pip install gspread google-auth")
        st.stop()
    
    try:
        _, service_account_info = get_config()
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Convert service account info to proper format
        creds = Credentials.from_service_account_info(
            dict(service_account_info), 
            scopes=scopes
        )
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Failed to connect to Google Sheets: {str(e)}")
        st.error("Please check your service account credentials in secrets.toml")
        st.stop()

def get_sheet(sheet_name: str):
    """Get a specific worksheet from the Google Sheet"""
    sheet_url, _ = get_config()
    client = get_gspread_client()
    
    if not sheet_url:
        st.error("SHEET_URL not configured")
        st.stop()
    
    sheet_id = extract_sheet_id(sheet_url)
    if not sheet_id:
        st.error("Invalid Google Sheets URL")
        st.stop()
    
    try:
        spreadsheet = client.open_by_key(sheet_id)
        return spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        st.error(f"Worksheet '{sheet_name}' not found. Please create the required worksheets.")
        st.stop()
    except Exception as e:
        st.error(f"Error accessing worksheet '{sheet_name}': {str(e)}")
        st.stop()

# ----------------------------
# Utility functions
# ----------------------------

def extract_sheet_id(sheet_url: str) -> Optional[str]:
    """Extract sheet ID from Google Sheets URL"""
    if not sheet_url:
        return None
    try:
        parts = urlparse(sheet_url).path.split("/")
        if "d" in parts:
            return parts[parts.index("d") + 1]
    except Exception:
        return None
    return None

def initialize_sheets():
    """Initialize Google Sheets with required worksheets and headers"""
    client = get_gspread_client()
    sheet_url, _ = get_config()
    sheet_id = extract_sheet_id(sheet_url)
    
    try:
        spreadsheet = client.open_by_key(sheet_id)
        
        # Check and create employee_details worksheet
        try:
            employee_ws = spreadsheet.worksheet("employee_details")
        except gspread.WorksheetNotFound:
            employee_ws = spreadsheet.add_worksheet("employee_details", rows=100, cols=10)
            employee_ws.append_row(["name", "email", "status"])
            # Add sample data
            sample_employees = [
                ["Jane Doe", "jane.doe@keydynamicssolutions", "no"],
                ["John Smith", "john.smith@keydynamicssolutions", "no"]
            ]
            employee_ws.append_rows(sample_employees)
        
        # Check and create questions worksheet
        try:
            questions_ws = spreadsheet.worksheet("questions")
        except gspread.WorksheetNotFound:
            questions_ws = spreadsheet.add_worksheet("questions", rows=100, cols=10)
            questions_ws.append_row(["question_id", "question"])
            # Add sample questions
            sample_questions = [
                [1, "Who is the most collaborative person on the team?"],
                [2, "Who provides the most constructive feedback?"],
                [3, "Who displays the best leadership?"],
                [4, "Who is the most punctual?"],
                [5, "Who is the best at mentoring others?"],
                [6, "Who has the most positive attitude?"]
            ]
            questions_ws.append_rows(sample_questions)
        
        # Check and create employee_responses worksheet
        try:
            responses_ws = spreadsheet.worksheet("employee_responses")
        except gspread.WorksheetNotFound:
            responses_ws = spreadsheet.add_worksheet("employee_responses", rows=1000, cols=10)
            responses_ws.append_row(["email", "name", "question_id", "name_of_person_in_response"])
            
    except Exception as e:
        st.error(f"Error initializing sheets: {str(e)}")
        st.stop()

# ----------------------------
# Data access functions
# ----------------------------

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_employees():
    """Fetch employee data from Google Sheets"""
    try:
        ws = get_sheet("employee_details")
        rows = ws.get_all_records()
        return rows
    except Exception as e:
        st.error(f"Failed to fetch employees: {str(e)}")
        return []

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_questions():
    """Fetch questions from Google Sheets"""
    try:
        ws = get_sheet("questions")
        rows = ws.get_all_records()
        return rows
    except Exception as e:
        st.error(f"Failed to fetch questions: {str(e)}")
        return []

def fetch_responses():
    """Fetch responses from Google Sheets"""
    try:
        ws = get_sheet("employee_responses")
        rows = ws.get_all_records()
        return rows
    except Exception as e:
        st.warning(f"Failed to fetch responses: {str(e)}")
        return []

def append_responses(responses: list):
    """Append new responses to Google Sheets"""
    try:
        ws = get_sheet("employee_responses")
        rows = [[r['email'], r['name'], r['question_id'], r['name_of_person_in_response']] for r in responses]
        ws.append_rows(rows)
        st.cache_data.clear()  # Clear cache to refresh data
        return True
    except Exception as e:
        st.error(f"Failed to save responses: {str(e)}")
        return False

def update_employee_status(email: str):
    """Update employee status to 'yes' after survey completion"""
    try:
        ws = get_sheet("employee_details")
        data = ws.get_all_records()
        
        for idx, row in enumerate(data, start=2):  # header row is 1, data starts at 2
            if row.get('email', '').strip().lower() == email.strip().lower():
                ws.update_cell(idx, 3, 'yes')  # 3rd column = status
                st.cache_data.clear()  # Clear cache to refresh data
                return True
        
        st.error(f"Employee with email {email} not found for status update")
        return False
        
    except Exception as e:
        st.error(f"Failed to update employee status: {str(e)}")
        return False

# ----------------------------
# Admin Functions
# ----------------------------

def admin_dashboard():
    st.title("🔧 Admin Dashboard")
    
    tab1, tab2 = st.tabs(["📊 Report", "👥 Status"])
    
    with tab1:
        st.header("Survey Results Report")
        questions = fetch_questions()
        responses = fetch_responses()
        
        if not responses:
            st.info("No responses submitted yet.")
            return
        
        # Group responses by question
        for q in questions[:6]:  # Only first 6 questions
            st.subheader(f"Q{q['question_id']}: {q['question']}")
            
            # Filter responses for this question
            q_responses = [r for r in responses if r['question_id'] == q['question_id']]
            
            if q_responses:
                # Count votes for each person
                vote_counts = {}
                for r in q_responses:
                    name = r['name_of_person_in_response']
                    vote_counts[name] = vote_counts.get(name, 0) + 1
                
                # Sort by vote count
                sorted_votes = sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)
                
                for name, count in sorted_votes:
                    st.write(f"• **{name}**: {count} vote(s)")
            else:
                st.write("No responses for this question yet.")
            st.markdown("---")
    
    with tab2:
        st.header("Employee Status")
        employees = fetch_employees()
        
        for emp in employees:
            status = "✅ Completed" if emp.get('status', '').lower() == 'yes' else "❌ Pending"
            st.write(f"**{emp['name']}** ({emp['email']}): {status}")
    
    if st.button("🚪 Logout", type="primary"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# ----------------------------
# Streamlit UI Pages
# ----------------------------

def apply_custom_css():
    st.markdown(
        """
        <style>
        .app-container { 
            display: flex; 
            flex-direction: column; 
            gap: 16px; 
            max-width: 900px; 
            margin: 0 auto; 
            padding: 16px; 
        }
        .login-box { 
            display: flex; 
            flex-direction: column; 
            gap: 8px; 
            padding: 16px; 
            border-radius: 10px; 
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        } 
        @media (min-width: 800px) { 
            .form-row { 
                display: flex; 
                gap: 12px; 
                align-items: center; 
            } 
        }
        .success-message {
            padding: 20px;
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 5px;
            color: #155724;
            margin: 10px 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def login_page():
    st.title("🏢 Key Dynamics Solutions")
    st.write("Please login using your company email to start the survey.")
    
    with st.form("login_form"):
        email = st.text_input("Email Address", placeholder="your.name@keydynamicssolutions")
        submitted = st.form_submit_button("Login", use_container_width=True)
    
    if submitted:
        if not email:
            st.error("Please enter your email address.")
            return
            
        if REQUIRED_DOMAIN not in email:
            st.error(f"Invalid domain. Only employees with {REQUIRED_DOMAIN} emails can log in.")
            return
        
        with st.spinner("Verifying your credentials..."):
            employees = fetch_employees()
            
        # Find employee by email
        found = None
        for e in employees:
            if e.get('email', '').strip().lower() == email.strip().lower():
                found = e
                break
        
        if not found:
            st.error("Email not found in employee database. Please contact your administrator.")
            return
        
        if found.get('status', '').lower() == 'yes':
            st.error("You have already completed the survey and cannot participate again.")
            return
        
        # Success - store in session state
        st.success(f"Welcome, {found.get('name')}! Redirecting to survey...")
        st.session_state['user_email'] = found.get('email')
        st.session_state['user_name'] = found.get('name')
        st.session_state['page'] = 'questions'
        st.rerun()

def questions_page():
    st.header("📋 Employee Feedback Survey")
    
    user_email = st.session_state.get('user_email')
    user_name = st.session_state.get('user_name')
    
    if not user_email:
        st.error("Session expired. Please login again.")
        if st.button("Go to Login"):
            st.session_state['page'] = 'login'
            st.rerun()
        return
    
    with st.spinner("Loading survey questions..."):
        questions = fetch_questions()
        employees = fetch_employees()
    
    if not questions:
        st.error("No questions available. Please contact your administrator.")
        return
    
    # Limit to first 6 questions
    questions = questions[:6]
    
    # Get names of other employees (exclude current user)
    names = []
    for e in employees:
        if e.get('email', '').strip().lower() != user_email.strip().lower():
            names.append(e['name'])
    
    names = sorted(list(set(names)))  # Remove duplicates and sort
    
    if not names:
        st.error("No other employees found for selection.")
        return
    
    st.info(f"👤 Logged in as: **{user_name}** ({user_email})")
    st.markdown("---")
    
    # Initialize selections in session state
    if 'selections' not in st.session_state:
        st.session_state['selections'] = {str(q['question_id']): None for q in questions}
    
    # Display questions with selectboxes
    for i, q in enumerate(questions, 1):
        qid = str(q['question_id'])
        
        st.subheader(f"Question {i} of {len(questions)}")
        st.write(q.get('question'))
        
        # Get current selection index
        current_selection = st.session_state['selections'].get(qid)
        if current_selection and current_selection in names:
            current_index = names.index(current_selection) + 1  # +1 for "-- Select --"
        else:
            current_index = 0
        
        choice = st.selectbox(
            "Select a person:",
            options=["-- Select a person --"] + names,
            index=current_index,
            key=f"sel_{qid}"
        )
        
        if choice == "-- Select a person --":
            st.session_state['selections'][qid] = None
        else:
            st.session_state['selections'][qid] = choice
        
        st.markdown("---")
    
    # Check if all questions are answered
    all_selected = all(v is not None for v in st.session_state['selections'].values())
    unanswered_count = sum(1 for v in st.session_state['selections'].values() if v is None)
    
    if not all_selected:
        st.warning(f"⚠️ Please answer all questions to continue. {unanswered_count} question(s) remaining.")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🔙 Back to Login", use_container_width=True):
            # Clear selections but keep user info for potential return
            if 'selections' in st.session_state:
                del st.session_state['selections']
            st.session_state['page'] = 'login'
            st.rerun()
    
    with col2:
        submit_button = st.button(
            "✅ Submit Survey", 
            disabled=not all_selected, 
            use_container_width=True,
            type="primary"
        )
    
    if submit_button and all_selected:
        with st.spinner("Submitting your responses..."):
            # Build responses
            responses = []
            for q in questions:
                qid = q['question_id']
                selected_name = st.session_state['selections'].get(str(qid))
                responses.append({
                    "email": user_email,
                    "name": user_name,
                    "question_id": qid,
                    "name_of_person_in_response": selected_name
                })
            
            # Save responses
            response_saved = append_responses(responses)
            
            if not response_saved:
                st.error("❌ Failed to save your responses. Please try again.")
                return
            
            # Update employee status
            status_updated = update_employee_status(user_email)
            
            if not status_updated:
                st.warning("⚠️ Responses saved but status update failed. Please contact admin if needed.")
            
            # Navigate to success page
            st.session_state['page'] = 'success'
            st.rerun()

def success_page():
    st.balloons()
    
    st.markdown("""
    <div class="success-message">
        <h2>🎉 Survey Submitted Successfully!</h2>
        <p>Thank you for your valuable feedback. Your responses have been recorded.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("**What happens next:**")
    st.write("• Your responses are now part of the feedback analysis")
    st.write("• Results will be compiled and shared with management")
    st.write("• Your individual responses remain confidential")
    
    if st.button("🏠 Return to Login", use_container_width=True, type="primary"):
        # Clear all session state for fresh start
        keys_to_clear = ['user_email', 'user_name', 'selections']
        for k in keys_to_clear:
            if k in st.session_state:
                del st.session_state[k]
        st.session_state['page'] = 'login'
        st.rerun()

# ----------------------------
# App main
# ----------------------------

def main():
    st.set_page_config(
        page_title="KDS Employee Survey", 
        page_icon="📋", 
        layout='centered',
        initial_sidebar_state="collapsed"
    )
    
    apply_custom_css()
    
    # Initialize Google Sheets on first run
    if 'sheets_initialized' not in st.session_state:
        with st.spinner("Initializing application..."):
            initialize_sheets()
        st.session_state['sheets_initialized'] = True
    
    # Initialize page state
    if 'page' not in st.session_state:
        st.session_state['page'] = 'login'
    
    st.markdown('<div class="app-container">', unsafe_allow_html=True)
    
    # Route to appropriate page
    if st.session_state['page'] == 'login':
        login_page()
    elif st.session_state['page'] == 'questions':
        questions_page()
    elif st.session_state['page'] == 'success':
        success_page()
    else:
        st.error('Unknown page state. Resetting to login.')
        st.session_state['page'] = 'login'
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == '__main__':
    main()