import streamlit as st
from typing import Optional
from models import User, UserRole
from database import db

def initialize_auth():
    """Initialize authentication session state"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None

def login_user(user: User):
    """Log in a user"""
    st.session_state.authenticated = True
    st.session_state.current_user = user

def logout_user():
    """Log out the current user"""
    st.session_state.authenticated = False
    st.session_state.current_user = None

def get_current_user() -> Optional[User]:
    """Get the current authenticated user"""
    return st.session_state.get('current_user')

def is_authenticated() -> bool:
    """Check if user is authenticated"""
    return st.session_state.get('authenticated', False)

def has_role(role: UserRole) -> bool:
    """Check if current user has specific role"""
    user = get_current_user()
    return user is not None and user.role == role

def require_auth():
    """Decorator-like function to require authentication"""
    if not is_authenticated():
        st.warning("Please log in to access this page.")
        st.stop()

def require_role(role: UserRole):
    """Decorator-like function to require specific role"""
    require_auth()
    if not has_role(role):
        st.error("You don't have permission to access this page.")
        st.stop()

def show_login_form():
    """Display login and signup form"""
    st.title("🏪 OmniTrack")
    
    # Demo login buttons
    st.subheader("Demo Accounts")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔧 Admin Demo", use_container_width=True):
            user = db.authenticate_user("admin", "admin123")
            if user:
                login_user(user)
                st.rerun()
    
    with col2:
        if st.button("👥 Staff Demo", use_container_width=True):
            user = db.authenticate_user("staff", "staff123")
            if user:
                login_user(user)
                st.rerun()
    
    with col3:
        if st.button("🛒 Customer Demo", use_container_width=True):
            user = db.authenticate_user("customer", "customer123")
            if user:
                login_user(user)
                st.rerun()
    
    st.divider()
    
    # Tabs for Login and Sign Up
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.subheader("Login to Your Account")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
            
            if submitted:
                if username and password:
                    user = db.authenticate_user(username, password)
                    if user:
                        login_user(user)
                        st.success("Logged in successfully!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                else:
                    st.error("Please enter both username and password")
    
    with tab2:
        st.subheader("Create New Account")
        with st.form("signup_form"):
            new_username = st.text_input("Choose Username")
            new_email = st.text_input("Email Address")
            new_password = st.text_input("Choose Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            st.info("New accounts are created as Customer accounts by default")
            
            signup_submitted = st.form_submit_button("Create Account", use_container_width=True)
            
            if signup_submitted:
                if not new_username or not new_password:
                    st.error("Username and password are required")
                elif len(new_username) < 3:
                    st.error("Username must be at least 3 characters long")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters long")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    existing_user = db.get_user_by_username(new_username)
                    if existing_user:
                        st.error("Username already exists. Please choose a different username.")
                    else:
                        try:
                            new_user = db.create_user(new_username, new_password, UserRole.CUSTOMER, new_email)
                            st.success("Account created successfully! You can now log in.")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Error creating account: {str(e)}")

def show_user_info():
    """Display current user information in sidebar"""
    user = get_current_user()
    if user:
        with st.sidebar:
            st.write(f"**Logged in as:** {user.username}")
            st.write(f"**Role:** {user.role.value.title()}")
            if st.button("Logout"):
                logout_user()
                st.rerun()
