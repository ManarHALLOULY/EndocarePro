import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io

from database import DatabaseManager
from auth import check_authentication, login_form, logout, get_user_role, get_username, require_role
from email_alerts import EmailAlertManager

# Page configuration
st.set_page_config(
    page_title="EndoTrace - Système de Traçabilité",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
@st.cache_resource
def init_database():
    return DatabaseManager()

db = init_database()

def print_record_html(data, title):
    """Generate HTML for printing records"""
    html = f"""
    <html>
    <head>
        <title>{title}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #1f4e79; text-align: center; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .record {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; }}
            .field {{ margin: 5px 0; }}
            .label {{ font-weight: bold; }}
            .timestamp {{ text-align: right; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🏥 EndoTrace</h1>
            <h2>{title}</h2>
            <p>Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}</p>
        </div>
        {data}
    </body>
    </html>
    """
    return html

def main():
    # Check authentication
    if not check_authentication():
        login_form()
        return
    
    # Sidebar navigation
    st.sidebar.title(f"👋 Bonjour {get_username()}")
    st.sidebar.write(f"**Rôle:** {get_user_role()}")
    
    # Navigation menu based on role
    user_role = get_user_role()
    
    if user_role == 'admin':
        menu_options = ["Dashboard", "Gestion des Utilisateurs", "Archives"]
    elif user_role == 'biomedical':
        menu_options = ["Dashboard", "Gestion Inventaire", "Archives"]
    elif user_role == 'sterilisation':
        menu_options = ["Dashboard", "Rapports d'Usage", "Archives"]
    else:
        menu_options = ["Dashboard"]
    
    selected_page = st.sidebar.selectbox("Navigation", menu_options)
    
    if st.sidebar.button("🚪 Déconnexion"):
        logout()
    
    # Main content based on selected page
    if selected_page == "Dashboard":
        show_dashboard()
    elif selected_page == "Gestion des Utilisateurs":
        show_admin_interface()
    elif selected_page == "Gestion Inventaire":
        show_biomedical_interface()
    elif selected_page == "Rapports d'Usage":
        show_sterilization_interface()
    elif selected_page == "Archives":
        show_archives_interface()

def show_dashboard():
    """Display dashboard with analytics"""
    st.title("📊 Tableau de Bord")
    
    # Get statistics
    stats = db.get_dashboard_stats()
    malfunction_percentage, broken_count, total_count = db.get_malfunction_percentage()
    
    # Check for email alert
    if malfunction_percentage > 50:
        st.error(f"🚨 **ALERTE CRITIQUE**: {malfunction_percentage:.1f}% des endoscopes sont en panne!")
        
        # Try to send email alert
        email_manager = EmailAlertManager()
        if st.button("📧 Envoyer alerte par email"):
            if email_manager.send_malfunction_alert(malfunction_percentage, broken_count, total_count):
                st.success("Email d'alerte envoyé avec succès!")
            else:
                st.warning("Erreur lors de l'envoi de l'email. Vérifiez la configuration SMTP.")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Endoscopes", total_count)
    
    with col2:
        st.metric("Fonctionnels", total_count - broken_count)
    
    with col3:
        st.metric("En Panne", broken_count)
    
    with col4:
        st.metric("Taux de Panne", f"{malfunction_percentage:.1f}%")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("État des Endoscopes")
        if not stats['status_stats'].empty:
            fig_status = px.pie(
                stats['status_stats'], 
                values='count', 
                names='etat',
                title="Répartition par État",
                color_discrete_map={'fonctionnel': '#4CAF50', 'en panne': '#F44336'}
            )
            st.plotly_chart(fig_status, use_container_width=True)
        else:
            st.info("Aucune donnée disponible")
    
    with col2:
        st.subheader("Localisation des Endoscopes")
        if not stats['location_stats'].empty:
            fig_location = px.bar(
                stats['location_stats'], 
                x='localisation', 
                y='count',
                title="Répartition par Localisation",
                color='count',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig_location, use_container_width=True)
        else:
            st.info("Aucune donnée disponible")

@require_role(['admin'])
def show_admin_interface():
    """Admin interface for user management"""
    st.title("👤 Gestion des Utilisateurs")
    
    tab1, tab2 = st.tabs(["Voir Utilisateurs", "Ajouter Utilisateur"])
    
    with tab1:
        st.subheader("Liste des Utilisateurs")
        users_df = db.get_all_users()
        
        if not users_df.empty:
            # Display users with edit/delete options
            for idx, user in users_df.iterrows():
                col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
                
                with col1:
                    st.write(f"**{user['username']}**")
                
                with col2:
                    new_role = st.selectbox(
                        "Rôle", 
                        ['admin', 'biomedical', 'sterilisation'],
                        index=['admin', 'biomedical', 'sterilisation'].index(user['role']),
                        key=f"role_{user['id']}"
                    )
                
                with col3:
                    if st.button("💾 Modifier", key=f"edit_{user['id']}"):
                        if db.update_user_role(user['id'], new_role):
                            st.success("Rôle modifié avec succès!")
                            st.rerun()
                        else:
                            st.error("Erreur lors de la modification")
                
                with col4:
                    if user['username'] != 'admin':  # Prevent admin deletion
                        if st.button("❌ Supprimer", key=f"delete_{user['id']}"):
                            if db.delete_user(user['id']):
                                st.success("Utilisateur supprimé!")
                                st.rerun()
                            else:
                                st.error("Erreur lors de la suppression")
                
                st.divider()
        else:
            st.info("Aucun utilisateur trouvé")
    
    with tab2:
        st.subheader("Ajouter un Nouvel Utilisateur")
        
        with st.form("add_user_form"):
            new_username = st.text_input("Nom d'utilisateur")
            new_password = st.text_input("Mot de passe", type="password")
            new_role = st.selectbox("Rôle", ['admin', 'biomedical', 'sterilisation'])
            
            if st.form_submit_button("➕ Ajouter Utilisateur"):
                if new_username and new_password:
                    if db.add_user(new_username, new_password, new_role):
                        st.success("Utilisateur ajouté avec succès!")
                        st.rerun()
                    else:
                        st.error("Erreur: Nom d'utilisateur déjà existant")
                else:
                    st.error("Veuillez remplir tous les champs")

@require_role(['biomedical'])
def show_biomedical_interface():
    """Biomedical engineer interface for inventory management"""
    st.title("🔬 Gestion de l'Inventaire des Endoscopes")
    
    tab1, tab2 = st.tabs(["Inventaire", "Ajouter Endoscope"])
    
    with tab1:
        st.subheader("Inventaire des Endoscopes")
        endoscopes_df = db.get_all_endoscopes()
        
        if not endoscopes_df.empty:
            # Display endoscopes with print option
            for idx, endoscope in endoscopes_df.iterrows():
                with st.expander(f"📱 {endoscope['designation']} - {endoscope['numero_serie']}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Marque:** {endoscope['marque']}")
                        st.write(f"**Modèle:** {endoscope['modele']}")
                        st.write(f"**Numéro de série:** {endoscope['numero_serie']}")
                        st.write(f"**État:** {endoscope['etat']}")
                        st.write(f"**Localisation:** {endoscope['localisation']}")
                        if endoscope['observation']:
                            st.write(f"**Observation:** {endoscope['observation']}")
                        st.write(f"**Créé le:** {endoscope['created_at']}")
                    
                    with col2:
                        if st.button("🖨️ Imprimer", key=f"print_{endoscope['id']}"):
                            record_html = f"""
                            <div class="record">
                                <div class="field"><span class="label">Désignation:</span> {endoscope['designation']}</div>
                                <div class="field"><span class="label">Marque:</span> {endoscope['marque']}</div>
                                <div class="field"><span class="label">Modèle:</span> {endoscope['modele']}</div>
                                <div class="field"><span class="label">Numéro de série:</span> {endoscope['numero_serie']}</div>
                                <div class="field"><span class="label">État:</span> {endoscope['etat']}</div>
                                <div class="field"><span class="label">Localisation:</span> {endoscope['localisation']}</div>
                                <div class="field"><span class="label">Observation:</span> {endoscope['observation'] or 'N/A'}</div>
                                <div class="timestamp">Créé le: {endoscope['created_at']}</div>
                            </div>
                            """
                            print_html = print_record_html(record_html, "Fiche Endoscope")
                            
                            st.download_button(
                                label="📥 Télécharger pour impression",
                                data=print_html,
                                file_name=f"endoscope_{endoscope['numero_serie']}.html",
                                mime="text/html"
                            )
        else:
            st.info("Aucun endoscope dans l'inventaire")
    
    with tab2:
        st.subheader("Ajouter un Endoscope")
        
        with st.form("add_endoscope_form"):
            designation = st.text_input("Désignation*")
            marque = st.text_input("Marque*")
            modele = st.text_input("Modèle*")
            numero_serie = st.text_input("Numéro de série*")
            etat = st.selectbox("État*", ['fonctionnel', 'en panne'])
            observation = st.text_area("Observation")
            localisation = st.text_input("Localisation*", placeholder="ex: stock, externe, en utilisation")
            
            if st.form_submit_button("➕ Ajouter Endoscope"):
                if designation and marque and modele and numero_serie and localisation:
                    if db.add_endoscope(designation, marque, modele, numero_serie, etat, observation, localisation, get_username()):
                        st.success("Endoscope ajouté avec succès!")
                        st.rerun()
                    else:
                        st.error("Erreur: Numéro de série déjà existant")
                else:
                    st.error("Veuillez remplir tous les champs obligatoires (*)")

@require_role(['sterilisation'])
def show_sterilization_interface():
    """Sterilization agent interface for usage reports"""
    st.title("🧴 Rapports d'Usage Post-Procédure")
    
    st.subheader("Enregistrer un Rapport d'Usage")
    
    with st.form("usage_report_form"):
        nom_operateur = st.text_input("Nom de l'opérateur*")
        endoscope = st.text_input("Endoscope (désignation)*")
        numero_serie = st.text_input("Numéro de série*")
        medecin = st.text_input("Médecin en charge*")
        etat = st.selectbox("État de l'appareil*", ['fonctionnel', 'en panne'])
        
        nature_panne = None
        if etat == 'en panne':
            nature_panne = st.text_area("Nature de la panne*")
        
        if st.form_submit_button("📝 Enregistrer Rapport"):
            if nom_operateur and endoscope and numero_serie and medecin:
                if etat == 'en panne' and not nature_panne:
                    st.error("Veuillez spécifier la nature de la panne")
                else:
                    if db.add_usage_report(nom_operateur, endoscope, numero_serie, medecin, etat, nature_panne, get_username()):
                        st.success("Rapport d'usage enregistré avec succès!")
                        st.rerun()
                    else:
                        st.error("Erreur lors de l'enregistrement")
            else:
                st.error("Veuillez remplir tous les champs obligatoires (*)")

def show_archives_interface():
    """Archives interface for all users"""
    st.title("🗃️ Archives des Rapports")
    
    reports_df = db.get_all_usage_reports()
    
    if not reports_df.empty:
        st.subheader("Historique des Rapports d'Usage")
        
        # Display data
        st.dataframe(reports_df, use_container_width=True)
        
        # Print button for archives
        if st.button("🖨️ Imprimer les Archives"):
            archives_html = ""
            for idx, report in reports_df.iterrows():
                archives_html += f"""
                <div class="record">
                    <div class="field"><span class="label">ID Opérateur:</span> {report['ID opérateur']}</div>
                    <div class="field"><span class="label">Endoscope:</span> {report['Endoscope']}</div>
                    <div class="field"><span class="label">Numéro de série:</span> {report['Numéro de série']}</div>
                    <div class="field"><span class="label">Nature de la panne:</span> {report['Nature de la panne'] or 'N/A'}</div>
                    <div class="field"><span class="label">Médecin:</span> {report['Médecin']}</div>
                    <div class="field"><span class="label">Date d'utilisation:</span> {report["Date d'utilisation"]}</div>
                </div>
                """
            
            print_html = print_record_html(archives_html, "Archives des Rapports d'Usage")
            
            st.download_button(
                label="📥 Télécharger Archives pour impression",
                data=print_html,
                file_name=f"archives_endotrace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                mime="text/html"
            )
    else:
        st.info("Aucun rapport d'usage disponible")

if __name__ == "__main__":
    main()
