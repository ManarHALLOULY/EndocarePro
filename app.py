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
    st.title("👤 Administration Système")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Utilisateurs", "Ajouter Utilisateur", "Gestion Base de Données", "Statistiques"])
    
    with tab1:
        st.subheader("Liste des Utilisateurs")
        users_df = db.get_all_users()
        
        if not users_df.empty:
            # Display users with edit/delete options
            for idx, user in users_df.iterrows():
                col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
                
                with col1:
                    st.write(f"**{user['username']}**")
                
                with col2:
                    current_role = str(user['role'])
                    new_role = st.selectbox(
                        "Rôle", 
                        ['admin', 'biomedical', 'sterilisation'],
                        index=['admin', 'biomedical', 'sterilisation'].index(current_role),
                        key=f"role_{user['id']}"
                    )
                
                with col3:
                    new_password = st.text_input("Nouveau mot de passe", type="password", key=f"pwd_{user['id']}")
                
                with col4:
                    if st.button("💾 Modifier", key=f"edit_{user['id']}"):
                        updated = False
                        if new_role != current_role:
                            if db.update_user_role(user['id'], new_role):
                                updated = True
                        if new_password:
                            if db.update_user_password(user['id'], new_password):
                                updated = True
                        
                        if updated:
                            st.success("Utilisateur modifié!")
                            st.rerun()
                        else:
                            st.error("Erreur lors de la modification")
                
                with col5:
                    if str(user['username']) != 'admin':  # Prevent admin deletion
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
    
    with tab3:
        st.subheader("🗑️ Gestion de la Base de Données")
        st.warning("⚠️ **ATTENTION**: Ces actions sont irréversibles!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Purger les Données**")
            
            if st.button("🗑️ Supprimer tous les endoscopes", type="secondary"):
                deleted_count = db.purge_all_endoscopes()
                st.success(f"{deleted_count} endoscopes supprimés de la base de données")
                st.rerun()
            
            if st.button("🗑️ Supprimer tous les rapports d'usage", type="secondary"):
                deleted_count = db.purge_all_usage_reports()
                st.success(f"{deleted_count} rapports supprimés de la base de données")
                st.rerun()
        
        with col2:
            st.write("**Accès Complet aux Données**")
            
            # Display all endoscopes
            endoscopes_df = db.get_all_endoscopes()
            if not endoscopes_df.empty:
                st.write(f"**Endoscopes ({len(endoscopes_df)} enregistrements):**")
                st.dataframe(endoscopes_df, use_container_width=True)
            else:
                st.info("Aucun endoscope en base")
            
            # Display all usage reports
            reports_df = db.get_all_usage_reports()
            if not reports_df.empty:
                st.write(f"**Rapports d'usage ({len(reports_df)} enregistrements):**")
                st.dataframe(reports_df, use_container_width=True)
            else:
                st.info("Aucun rapport d'usage en base")
    
    with tab4:
        st.subheader("📊 Statistiques de la Base de Données")
        
        stats = db.get_database_statistics()
        
        # Key metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Utilisateurs", stats['total_users'])
        
        with col2:
            st.metric("Total Endoscopes", stats['total_endoscopes'])
        
        with col3:
            st.metric("Total Rapports", stats['total_reports'])
        
        # Users by role chart
        if not stats['users_by_role'].empty:
            st.subheader("Répartition des Utilisateurs par Rôle")
            fig_users = px.pie(
                stats['users_by_role'], 
                values='count', 
                names='role',
                title="Utilisateurs par Rôle"
            )
            st.plotly_chart(fig_users, use_container_width=True)

@require_role(['biomedical'])
def show_biomedical_interface():
    """Biomedical engineer interface for inventory management"""
    st.title("🔬 Gestion de l'Inventaire des Endoscopes")
    
    tab1, tab2, tab3 = st.tabs(["Inventaire", "Ajouter Endoscope", "Modifier/Supprimer"])
    
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
                        try:
                            obs_value = endoscope['observation']
                            if obs_value is not None and str(obs_value).strip() not in ['', 'nan', 'None']:
                                st.write(f"**Observation:** {obs_value}")
                        except:
                            pass
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
                                <div class="field"><span class="label">Observation:</span> {str(endoscope.get('observation', 'N/A'))}</div>
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
            localisation = st.text_input("Localisation*", placeholder="ex: stockage, externe, en utilisation")
            
            if st.form_submit_button("➕ Ajouter Endoscope"):
                if designation and marque and modele and numero_serie and localisation:
                    if db.add_endoscope(designation, marque, modele, numero_serie, etat, observation, localisation, get_username()):
                        st.success("Endoscope ajouté avec succès!")
                        st.rerun()
                    else:
                        st.error("Erreur: Numéro de série déjà existant")
                else:
                    st.error("Veuillez remplir tous les champs obligatoires (*)")
    
    with tab3:
        st.subheader("Modifier ou Supprimer un Endoscope")
        endoscopes_df = db.get_all_endoscopes()
        
        if not endoscopes_df.empty:
            # Select endoscope to modify
            endoscope_options = [(idx, f"{row['designation']} - {row['numero_serie']}") for idx, row in endoscopes_df.iterrows()]
            
            if endoscope_options:
                selected_idx = st.selectbox(
                    "Sélectionner un endoscope à modifier/supprimer:",
                    options=[opt[0] for opt in endoscope_options],
                    format_func=lambda x: next(opt[1] for opt in endoscope_options if opt[0] == x)
                )
                
                endoscope = endoscopes_df.loc[selected_idx]
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.subheader("✏️ Modifier l'Endoscope")
                    with st.form("update_endoscope_form"):
                        new_designation = st.text_input("Désignation", value=endoscope['designation'])
                        new_marque = st.text_input("Marque", value=endoscope['marque'])
                        new_modele = st.text_input("Modèle", value=endoscope['modele'])
                        new_numero_serie = st.text_input("Numéro de série", value=endoscope['numero_serie'])
                        new_etat = st.selectbox("État", ['fonctionnel', 'en panne'], 
                                              index=0 if endoscope['etat'] == 'fonctionnel' else 1)
                        new_observation = st.text_area("Observation", value=endoscope['observation'] or '')
                        new_localisation = st.text_input("Localisation", value=endoscope['localisation'])
                        
                        if st.form_submit_button("💾 Mettre à jour"):
                            update_data = {
                                'designation': new_designation,
                                'marque': new_marque,
                                'modele': new_modele,
                                'numero_serie': new_numero_serie,
                                'etat': new_etat,
                                'observation': new_observation,
                                'localisation': new_localisation
                            }
                            
                            if db.update_endoscope(endoscope['id'], **update_data):
                                st.success("Endoscope mis à jour avec succès!")
                                st.rerun()
                            else:
                                st.error("Erreur lors de la mise à jour")
                
                with col2:
                    st.subheader("❌ Supprimer")
                    st.warning("⚠️ Cette action est irréversible!")
                    if st.button("🗑️ Supprimer cet endoscope", type="secondary"):
                        if db.delete_endoscope(endoscope['id']):
                            st.success("Endoscope supprimé avec succès!")
                            st.rerun()
                        else:
                            st.error("Erreur lors de la suppression")
        else:
            st.info("Aucun endoscope à modifier")

@require_role(['sterilisation'])
def show_sterilization_interface():
    """Sterilization agent interface for usage reports"""
    st.title("🧴 Rapports d'Usage Post-Procédure")
    
    tab1, tab2 = st.tabs(["Nouveau Rapport", "Modifier/Supprimer Rapports"])
    
    with tab1:
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
    
    with tab2:
        st.subheader("Gérer mes Rapports d'Usage")
        user_reports = db.get_user_usage_reports(get_username())
        
        if not user_reports.empty:
            report_options = [(idx, f"Rapport #{row['id']} - {row['endoscope']} ({row['date_utilisation']})") for idx, row in user_reports.iterrows()]
            
            if report_options:
                selected_idx = st.selectbox(
                    "Sélectionner un rapport à modifier/supprimer:",
                    options=[opt[0] for opt in report_options],
                    format_func=lambda x: next(opt[1] for opt in report_options if opt[0] == x)
                )
                
                report = user_reports.loc[selected_idx]
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.subheader("✏️ Modifier le Rapport")
                    with st.form("update_report_form"):
                        new_nom_operateur = st.text_input("Nom de l'opérateur", value=report['nom_operateur'])
                        new_endoscope = st.text_input("Endoscope", value=report['endoscope'])
                        new_numero_serie = st.text_input("Numéro de série", value=report['numero_serie'])
                        new_medecin = st.text_input("Médecin", value=report['medecin'])
                        new_etat = st.selectbox("État", ['fonctionnel', 'en panne'], 
                                              index=0 if report['etat'] == 'fonctionnel' else 1)
                        new_nature_panne = st.text_area("Nature de la panne", value=report['nature_panne'] or '')
                        
                        if st.form_submit_button("💾 Mettre à jour"):
                            if new_etat == 'en panne' and not new_nature_panne:
                                st.error("Veuillez spécifier la nature de la panne")
                            else:
                                update_data = {
                                    'nom_operateur': new_nom_operateur,
                                    'endoscope': new_endoscope,
                                    'numero_serie': new_numero_serie,
                                    'medecin': new_medecin,
                                    'etat': new_etat,
                                    'nature_panne': new_nature_panne if new_etat == 'en panne' else None
                                }
                                
                                if db.update_usage_report(report['id'], **update_data):
                                    st.success("Rapport mis à jour avec succès!")
                                    st.rerun()
                                else:
                                    st.error("Erreur lors de la mise à jour")
                
                with col2:
                    st.subheader("❌ Supprimer")
                    st.warning("⚠️ Cette action est irréversible!")
                    if st.button("🗑️ Supprimer ce rapport", type="secondary"):
                        if db.delete_usage_report(report['id']):
                            st.success("Rapport supprimé avec succès!")
                            st.rerun()
                        else:
                            st.error("Erreur lors de la suppression")
        else:
            st.info("Aucun rapport d'usage créé par vous")

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
                    <div class="field"><span class="label">Nature de la panne:</span> {report['Nature de la panne'] if pd.notna(report['Nature de la panne']) else 'N/A'}</div>
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
