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
        menu_options = ["Dashboard", "Gestion Inventaire", "Rapports de Stérilisation", "Archives"]
    elif user_role == 'sterilisation':
        menu_options = ["Dashboard", "Rapports de Stérilisation", "Archives"]
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
    elif selected_page == "Rapports de Stérilisation":
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
            
            # Admin individual record management
            st.write("**Gestion Individuelle des Enregistrements**")
            
            # Endoscopes management
            endoscopes_df = db.get_all_endoscopes()
            if not endoscopes_df.empty:
                st.write(f"**Endoscopes ({len(endoscopes_df)} enregistrements):**")
                
                for idx, endoscope in endoscopes_df.iterrows():
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"📱 {endoscope['designation']} - {endoscope['numero_serie']} ({endoscope['etat']})")
                    with col2:
                        if st.button("🗑️ Supprimer", key=f"admin_del_endo_{endoscope['id']}"):
                            if db.delete_endoscope(endoscope['id']):
                                st.success("Endoscope supprimé!")
                                st.rerun()
                st.divider()
            else:
                st.info("Aucun endoscope en base")
            
            # Usage reports management
            all_reports_df = db.get_all_usage_reports()
            if not all_reports_df.empty:
                st.write(f"**Rapports d'usage ({len(all_reports_df)} enregistrements):**")
                
                for idx, report in all_reports_df.iterrows():
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"📋 Rapport #{report['ID opérateur']} - {report['Endoscope']} par {report.get('created_by', 'N/A')}")
                    with col2:
                        if st.button("🗑️ Supprimer", key=f"admin_del_report_{report['ID opérateur']}"):
                            if db.delete_usage_report(report['ID opérateur']):
                                st.success("Rapport supprimé!")
                                st.rerun()
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
                        current_obs = endoscope['observation'] if pd.notna(endoscope['observation']) else ''
                        new_observation = st.text_area("Observation", value=current_obs)
                        new_localisation = st.text_input("Localisation", value=endoscope['localisation'])
                        
                        if st.form_submit_button("💾 Mettre à jour"):
                            # Check permissions
                            if not db.can_user_modify_endoscope(get_user_role(), endoscope['id'], get_username()):
                                st.error("❌ Vous n'avez pas l'autorisation de modifier cet élément.")
                            else:
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
                                    st.error("Erreur lors de la mise à jour - Vérifiez les données saisies")
                
                with col2:
                    st.subheader("❌ Supprimer")
                    st.warning("⚠️ Cette action est irréversible!")
                    if st.button("🗑️ Supprimer cet endoscope", type="secondary"):
                        if not db.can_user_modify_endoscope(get_user_role(), endoscope['id'], get_username()):
                            st.error("❌ Vous n'avez pas l'autorisation de supprimer cet élément.")
                        else:
                            if db.delete_endoscope(endoscope['id']):
                                st.success("Endoscope supprimé avec succès!")
                                st.rerun()
                            else:
                                st.error("Erreur lors de la suppression - Contactez l'administrateur")
        else:
            st.info("Aucun endoscope à modifier")

@require_role(['sterilisation', 'biomedical'])
def show_sterilization_interface():
    """Sterilization agent interface for sterilization reports"""
    st.title("🧴 Rapports de Stérilisation et Désinfection")
    
    tab1, tab2, tab3 = st.tabs(["Nouveau Rapport Stérilisation", "Gérer Rapports", "Ancien Système"])
    
    with tab1:
        st.subheader("Enregistrer un Rapport de Stérilisation")
        
        with st.form("sterilisation_report_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**📋 Informations Générales**")
                nom_operateur = st.text_input("Nom de l'opérateur*")
                endoscope = st.text_input("Endoscope*")
                numero_serie = st.text_input("Numéro de série*")
                medecin_responsable = st.text_input("Médecin responsable*")
                
                st.write("**💧 Désinfection**")
                date_desinfection = st.date_input("Date de désinfection*")
                type_desinfection = st.selectbox("Type de désinfection*", ['manuel', 'automatique'])
                cycle = st.selectbox("Cycle*", ['complet', 'incomplet'])
                test_etancheite = st.selectbox("Test d'étanchéité*", ['réussi', 'échoué'])
            
            with col2:
                st.write("**⏰ Horaires**")
                heure_debut = st.time_input("Heure de début*")
                heure_fin = st.time_input("Heure de fin*")
                
                st.write("**🏥 Procédure Médicale**")
                procedure_medicale = st.text_input("Procédure médicale*")
                salle = st.text_input("Salle*")
                type_acte = st.text_input("Type d'acte*")
                
                st.write("**⚙️ État**")
                etat_endoscope = st.selectbox("État de l'endoscope*", ['fonctionnel', 'en panne'])
                nature_panne = None
                if etat_endoscope == 'en panne':
                    nature_panne = st.text_area("Nature de la panne*")
            
            if st.form_submit_button("📝 Enregistrer Rapport de Stérilisation"):
                required_fields = [nom_operateur, endoscope, numero_serie, medecin_responsable, 
                                 procedure_medicale, salle, type_acte]
                
                if all(required_fields):
                    if etat_endoscope == 'en panne' and not nature_panne:
                        st.error("Veuillez spécifier la nature de la panne")
                    else:
                        if db.add_sterilisation_report(
                            nom_operateur, endoscope, numero_serie, medecin_responsable,
                            date_desinfection, type_desinfection, cycle, test_etancheite,
                            heure_debut, heure_fin, procedure_medicale, salle, type_acte,
                            etat_endoscope, nature_panne, get_username()
                        ):
                            st.success("Rapport de stérilisation enregistré avec succès!")
                            st.rerun()
                        else:
                            st.error("Erreur lors de l'enregistrement")
                else:
                    st.error("Veuillez remplir tous les champs obligatoires (*)")
    
    with tab2:
        st.subheader("Gérer les Rapports de Stérilisation")
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_by_user = st.checkbox("Mes rapports uniquement", value=(get_user_role() == 'sterilisation'))
        with col2:
            filter_date = st.date_input("Filtrer par date", value=None)
        with col3:
            filter_etat = st.selectbox("Filtrer par état", ['Tous', 'fonctionnel', 'en panne'])
        
        # Get reports based on filters
        if filter_by_user or get_user_role() == 'sterilisation':
            steril_reports = db.get_user_sterilisation_reports(get_username())
        else:
            steril_reports = db.get_all_sterilisation_reports()
        
        if not steril_reports.empty:
            # Apply additional filters
            if filter_date:
                steril_reports = steril_reports[steril_reports['date_desinfection'] == str(filter_date)]
            if filter_etat != 'Tous':
                steril_reports = steril_reports[steril_reports['etat_endoscope'] == filter_etat]
            
            if not steril_reports.empty:
                st.write(f"**Rapports trouvés: {len(steril_reports)}**")
                
                # Display reports with edit/delete options
                for idx, report in steril_reports.iterrows():
                    with st.expander(f"📋 Rapport #{report['id']} - {report['endoscope']} ({report['date_desinfection']})"):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**Opérateur:** {report['nom_operateur']}")
                            st.write(f"**Médecin:** {report['medecin_responsable']}")
                            st.write(f"**Désinfection:** {report['type_desinfection']} - {report['cycle']}")
                            st.write(f"**Test étanchéité:** {report['test_etancheite']}")
                            st.write(f"**Horaires:** {report['heure_debut']} - {report['heure_fin']}")
                            st.write(f"**Procédure:** {report['procedure_medicale']} (Salle: {report['salle']})")
                            st.write(f"**État:** {report['etat_endoscope']}")
                            if report['nature_panne']:
                                st.write(f"**Nature panne:** {report['nature_panne']}")
                        
                        with col2:
                            can_modify = db.can_user_modify_sterilisation_report(get_user_role(), report['id'], get_username())
                            
                            if can_modify:
                                if st.button("✏️ Modifier", key=f"edit_steril_{report['id']}"):
                                    st.session_state[f"edit_steril_{report['id']}"] = True
                                    st.rerun()
                                
                                if st.button("🗑️ Supprimer", key=f"del_steril_{report['id']}"):
                                    if db.delete_sterilisation_report(report['id']):
                                        st.success("Rapport supprimé!")
                                        st.rerun()
                                    else:
                                        st.error("Erreur lors de la suppression")
                            else:
                                st.info("Lecture seule")
            else:
                st.info("Aucun rapport correspondant aux filtres")
        else:
            st.info("Aucun rapport de stérilisation disponible")
    
    with tab3:
        st.subheader("Ancien Système - Rapports d'Usage Simple")
        
        # Keep the old usage reports system for backward compatibility
        subcol1, subcol2 = st.columns(2)
        
        with subcol1:
            st.write("**Nouveau Rapport d'Usage Simple**")
            with st.form("simple_usage_report_form"):
                nom_operateur = st.text_input("Nom de l'opérateur*")
                endoscope = st.text_input("Endoscope (désignation)*")
                numero_serie = st.text_input("Numéro de série*")
                medecin = st.text_input("Médecin en charge*")
                etat = st.selectbox("État de l'appareil*", ['fonctionnel', 'en panne'])
                
                nature_panne = None
                if etat == 'en panne':
                    nature_panne = st.text_area("Nature de la panne*")
                
                if st.form_submit_button("📝 Enregistrer Rapport Simple"):
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
        
        with subcol2:
            st.write("**Gérer Rapports d'Usage Simple**")
            user_reports = db.get_user_usage_reports(get_username())
            
            if not user_reports.empty:
                selected_report_id = st.selectbox(
                    "Sélectionner un rapport:",
                    options=user_reports['id'].tolist(),
                    format_func=lambda x: f"Rapport #{x} - {user_reports[user_reports['id']==x]['endoscope'].iloc[0]}"
                )
                
                if selected_report_id:
                    selected_report = user_reports[user_reports['id'] == selected_report_id].iloc[0]
                    
                    if st.button("✏️ Modifier ce rapport"):
                        st.session_state[f"edit_usage_{selected_report_id}"] = True
                        st.rerun()
                    
                    if st.button("🗑️ Supprimer ce rapport"):
                        if db.can_user_modify_usage_report(get_user_role(), selected_report_id, get_username()):
                            if db.delete_usage_report(selected_report_id):
                                st.success("Rapport supprimé!")
                                st.rerun()
                            else:
                                st.error("Erreur lors de la suppression")
                        else:
                            st.error("❌ Vous n'avez pas l'autorisation de supprimer cet élément.")
            else:
                st.info("Aucun rapport d'usage simple")

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
                # Safe extraction of nature_panne value
                try:
                    nature_panne_value = str(report['Nature de la panne'])
                    nature_panne_display = nature_panne_value if nature_panne_value not in ['nan', 'None', ''] else 'N/A'
                except:
                    nature_panne_display = 'N/A'
                
                archives_html += f"""
                <div class="record">
                    <div class="field"><span class="label">ID Opérateur:</span> {report['ID opérateur']}</div>
                    <div class="field"><span class="label">Endoscope:</span> {report['Endoscope']}</div>
                    <div class="field"><span class="label">Numéro de série:</span> {report['Numéro de série']}</div>
                    <div class="field"><span class="label">Nature de la panne:</span> {nature_panne_display}</div>
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
