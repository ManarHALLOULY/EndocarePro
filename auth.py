import streamlit as st
from database import DatabaseManager

def check_authentication():
    """Check if user is authenticated"""
    return 'authenticated' in st.session_state and st.session_state.authenticated

def get_user_role():
    """Get current user role"""
    return st.session_state.get('user_role', None)

def get_username():
    """Get current username"""
    return st.session_state.get('username', None)

def login_form():
    """Display login form"""
    
    # Create two columns - left for login form, right for image
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        # Put everything in a container with border and make it taller
        with st.container(border=True):
            # Add top padding
            st.markdown("<br><br>", unsafe_allow_html=True)
            
            # Logo at the top of the form - centered
            try:
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.image('attached_assets/logo.webp', width=300)
            except Exception as e:
                st.error(f"Impossible de charger le logo : {e}")
            
            # Add more spacing
            
            # Title and subtitle
            st.markdown("<h2 style='text-align: center; margin-bottom: 30px;'>Bienvenue sur EndocarePro</h2>", unsafe_allow_html=True)
            
            # Add more spacing
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Login form
            with st.form("login_form"):
                username = st.text_input("**Nom d'utilisateur**")
                password = st.text_input("**Mot de passe**", type="password")
                
                # Add spacing before button
                st.markdown("<br><br>", unsafe_allow_html=True)
                
                submit = st.form_submit_button("Se connecter", use_container_width=True, type="primary")
                
                if submit:
                    if username and password:
                        db = DatabaseManager()
                        role = db.authenticate_user(username, password)
                        
                        if role:
                            st.session_state.authenticated = True
                            st.session_state.user_role = role
                            st.session_state.username = username
                            st.success(f"Connexion réussie! Bienvenue {username}.")
                            st.rerun()
                        else:
                            st.error("Nom d'utilisateur ou mot de passe incorrect")
                    else:
                        st.error("Veuillez remplir tous les champs")
            
            # Add bottom padding to make the box taller
            st.markdown("<br><br><br>", unsafe_allow_html=True)
    
    with col_right:
        # Add some top margin and display bigger image
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        
        try:
            st.image('assets/logo-hopital.jpg', use_container_width=True)
        except Exception as e:
            st.markdown("""
            <div style="height: 400px; background-color: #f0f2f6; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #666;">
                <h3>Logo Hôpital</h3>
            </div>
            """, unsafe_allow_html=True)


def logout():
    """Logout user"""
    for key in ['authenticated', 'user_role', 'username']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

def require_role(allowed_roles):
    """Decorator to require specific roles"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not check_authentication():
                st.error("Vous devez être connecté pour accéder à cette page")
                return
            
            user_role = get_user_role()
            if user_role not in allowed_roles:
                st.error(f"Accès refusé. Rôles autorisés: {', '.join(allowed_roles)}")
                return
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
