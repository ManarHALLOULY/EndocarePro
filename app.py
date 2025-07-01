import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import datetime as dt

import io


import qrcode
from io import BytesIO
import base64

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import base64
import os

from database import DatabaseManager
from auth import check_authentication, login_form, logout, get_user_role, get_username, require_role
from email_alerts import EmailAlertManager


# Page configuration
st.set_page_config(
    page_title="EndocarePro - Système de Traçabilité",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
def init_database():
    return DatabaseManager()

db = init_database()


def generate_qr_code(endoscope_id, designation, numero_serie):
    """Generate QR code for endoscope"""
    try:
        # Create QR code data
        qr_data = f"ENDOSCOPE_ID:{endoscope_id}|DESIGNATION:{designation}|SERIE:{numero_serie}"
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create QR code image
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for display
        buffer = BytesIO()
        qr_img.save(buffer, format='PNG')
        buffer.seek(0)
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return qr_base64
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return None

def generate_professional_pdf_report(data, title, report_type="sterilisation"):
    """Generate a professional medical PDF report like the example provided"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom styles for medical report
    title_style = ParagraphStyle(
        'MedicalTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        spaceBefore=10,
        alignment=TA_LEFT,  # Left aligned like medical reports
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    record_header_style = ParagraphStyle(
        'RecordHeader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=10,
        spaceBefore=15,
        textColor=colors.HexColor('#1f4e79'),
        fontName='Helvetica-Bold'
    )
    
    field_style = ParagraphStyle(
        'FieldStyle',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=4,
        fontName='Helvetica',
        leftIndent=0
    )
    
    # Content story
    story = []

    title_style = styles["Title"]

    # Load and resize the logo (centered)
    try:
        logo_path = r'attached_assets\logo.webp'
        if os.path.exists(logo_path):
            logo = Image(logo_path)
            logo.drawHeight = 1 * inch
            logo.drawWidth = 1 * inch * logo.imageWidth / logo.imageHeight  # Maintain aspect ratio
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 10))
    except Exception as e:
        print(f"Logo loading error: {e}")

    # Choose title
    if report_type == "sterilisation":
        title_text = "Rapports de Stérilisation et Désinfection"
    elif report_type == "inventaire":
        title_text = "Rapport d'Inventaire des Endoscopes"
    else:
        title_text = title

    # Add centered title
    title_paragraph = Paragraph(f"<b>{title_text}</b>", title_style)
    title_paragraph.hAlign = 'CENTER'
    story.append(title_paragraph)
    story.append(Spacer(1, 6))

    # Add horizontal line
    story.append(HRFlowable(width="100%", thickness=1.2, color=colors.black))
    story.append(Spacer(1, 15))
    

    # Main content
    if isinstance(data, pd.DataFrame) and not data.empty:
        # Process each record
        for i, (_, row) in enumerate(data.iterrows(), start=1):
            # Construire le titre de l'enregistrement
            record_title = f"• ENREGISTREMENT {i}"
            if report_type == "sterilisation" and 'endoscope' in row:
                record_title += f" - {row['endoscope']}"
            elif report_type == "inventaire" and 'designation' in row:
                record_title += f" - {row['designation']}"

            story.append(Paragraph(record_title, record_header_style))

            # Générer et insérer le QR Code seulement pour les rapports d'inventaire
            if report_type == "inventaire":
                qr_code_base64 = generate_qr_code(row.get('id'), row.get('designation'), row.get('numero_serie'))
                if qr_code_base64:
                    try:
                        qr_buffer = BytesIO(base64.b64decode(qr_code_base64))
                        qr_img = Image(qr_buffer, width=2*cm, height=2*cm)
                        qr_img.hAlign = 'LEFT'
                        story.append(qr_img)
                    except Exception as e:
                        print(f"Erreur QR: {e}")

            story.append(Spacer(1, 10))

            
            # Create simple field entries (no squares, just text)
            for col, val in row.items():
                if pd.notna(val) and str(val).strip():
                    if col.lower() in ['qr', 'qr_code', 'qr_img', 'qr code']:
                        continue  # Empêche l'affichage d'un QR code en double
                    # Format column names in French
                    formatted_col = col.replace('_', ' ').title()
                    if col == 'id':
                        formatted_col = "Id"
                    elif col == 'date_desinfection':
                        formatted_col = "Date de Désinfection"
                    elif col == 'nom_operateur':
                        formatted_col = "Nom de l'Opérateur"
                    elif col == 'numero_serie':
                        formatted_col = "Numéro de Série"
                    elif col == 'medecin_responsable':
                        formatted_col = "Médecin Responsable"
                    elif col == 'type_desinfection':
                        formatted_col = "Type de Désinfection"
                    elif col == 'test_etancheite':
                        formatted_col = "Test d'Étanchéité"
                    elif col == 'etat_endoscope':
                        formatted_col = "État de l'Endoscope"
                    elif col == 'nature_panne':
                        formatted_col = "Nature de la Panne"
                    elif col == 'heure_debut':
                        formatted_col = "Heure de Début"
                    elif col == 'heure_fin':
                        formatted_col = "Heure de Fin"
                    elif col == 'type_acte':
                        formatted_col = "Type d'Acte"
                    elif col == 'salle':
                        formatted_col = "Salle"
                    elif col == 'cycle':
                        formatted_col = "Cycle"
                    elif col == 'marque':
                        formatted_col = "Marque"
                    elif col == 'modele':
                        formatted_col = "Modèle"
                    elif col == 'localisation':
                        formatted_col = "Localisation"
                    elif col == 'observation':
                        formatted_col = "Observations"
                    elif col == 'created_by':
                        formatted_col = "Créé par"
                    elif col == 'created_at':
                        formatted_col = "Date de Création"
                    elif col == 'endoscope':
                        formatted_col = "Endoscope"
                    elif col == 'procedure_medicale':
                        formatted_col = "Procédure Médicale"
                    elif col == 'designation':
                        formatted_col = "Désignation"
                    elif col == 'etat':
                        formatted_col = "État"
                    
                    formatted_val = str(val)
                    
                    # Simple format like the example: ■ Field: Value
                    # Simple clean format like medical reports: Field: Value
                    field_text = f"<b>{formatted_col}:</b> {formatted_val}" 
                    story.append(Paragraph(field_text, field_style))
            
            story.append(Spacer(1, 20))  # Space between records
    else:
        story.append(Paragraph("Aucune donnée disponible", field_style))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def load_css_file(css_file_path):
    """Load CSS from external file"""
    try:
        with open(css_file_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"CSS file not found: {css_file_path}")

def main():
    # Check authentication
    if not check_authentication():
        login_form()
        return
    
    
    # Sidebar navigation
    st.sidebar.image('attached_assets/logo.webp', use_container_width=True)
    st.sidebar.title(f"Bonjour {get_username()}")
    st.sidebar.write(f"**Rôle:** {get_user_role()}")
    
    # Navigation menu based on role
    user_role = get_user_role()
    
    if user_role == 'admin':
        menu_options = ["Dashboard", "Gestion des Utilisateurs", "Archives"]
    elif user_role == 'biomedical':
        menu_options = ["Dashboard", "Gestion Inventaire", "Archives"]
    elif user_role == 'sterilisation':
        menu_options = ["Dashboard", "Rapports de Stérilisation", "Archives"]
    else:
        menu_options = ["Dashboard"]
    
    selected_page = st.sidebar.selectbox("Navigation", menu_options)
    
    if st.sidebar.button("Déconnexion"):
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
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
            st.title("EndocarePro")    
    # --- Section for new breakdown alerts ---
    with st.container(border=True):
        st.subheader(" Alertes de Pannes Récentes")
        recent_breakdowns = db.get_recent_breakdowns(days=7)

        if not recent_breakdowns.empty:
            # Show notification count
            breakdown_count = len(recent_breakdowns)
            if breakdown_count == 1:
                st.error(f" **{breakdown_count} NOUVELLE ALERTE DE PANNE**")
            else:
                st.error(f" **{breakdown_count} NOUVELLES ALERTES DE PANNES**")
            
            # Show each breakdown with enhanced styling
            for idx, report in recent_breakdowns.iterrows():
                with st.expander(f" PANNE {idx+1} - {report['endoscope']}", expanded=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.warning(
                            f"**Date:** {report['date_desinfection']}\n\n"
                            f"**Signalé par:** {report['nom_operateur']}\n\n"
                            f"**Endoscope:** {report['endoscope']} (N/S: {report['numero_serie']})\n\n"
                            f"**Nature de la panne:** {report.get('nature_panne', 'Non spécifiée')}\n\n"
                            f"**Salle:** {report.get('salle', 'Non spécifiée')}"
                        )
        else:
            st.success(" **AUCUNE PANNE RÉCENTE** - Tous les endoscopes fonctionnent correctement au cours des 7 derniers jours.")

    st.divider()

    # Get statistics
    stats = db.get_dashboard_stats()
    malfunction_percentage, broken_count, total_count = db.get_malfunction_percentage()
    
    # Affichage simple de l'alerte critique si besoin, sans email
    if malfunction_percentage > 50:
        st.error(f"**ALERTE CRITIQUE**: {malfunction_percentage:.1f}% des endoscopes sont en panne!")

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        with st.container():
            st.markdown("""
            <div style="background-color: #1f77b4; padding: 20px; border-radius: 10px; text-align: center; color: white; height: 160px; display: flex; flex-direction: column; justify-content: center;">
                <h3 style="margin: 0; color: white; font-size: 20px;">Total Endoscopes</h3>
                <h1 style="margin: 10px 0 0 0; color: white; font-size: 36px;">{}</h1>
            </div>
            """.format(total_count), unsafe_allow_html=True)

    with col2:
        with st.container():
            st.markdown("""
            <div style="background-color: #1f77b4; padding: 20px; border-radius: 10px; text-align: center; color: white; height: 160px; display: flex; flex-direction: column; justify-content: center;">
                <h3 style="margin: 0; color: white; font-size: 20px;">Fonctionnels</h3>
                <h1 style="margin: 10px 0 0 0; color: white; font-size: 36px;">{}</h1>
            </div>
            """.format(total_count - broken_count), unsafe_allow_html=True)

    with col3:
        with st.container():
            st.markdown("""
            <div style="background-color: #1f77b4; padding: 20px; border-radius: 10px; text-align: center; color: white; height: 160px; display: flex; flex-direction: column; justify-content: center;">
                <h3 style="margin: 0; color: white; font-size: 20px;">En Panne</h3>
                <h1 style="margin: 10px 0 0 0; color: white; font-size: 36px;">{}</h1>
            </div>
            """.format(broken_count), unsafe_allow_html=True)

    with col4:
        with st.container():
            st.markdown("""
            <div style="background-color: #1f77b4; padding: 20px; border-radius: 10px; text-align: center; color: white; height: 160px; display: flex; flex-direction: column; justify-content: center;">
                <h3 style="margin: 0; color: white; font-size: 20px;">Taux de Panne</h3>
                <h1 style="margin: 10px 0 0 0; color: white; font-size: 36px;">{:.1f}%</h1>
            </div>
            """.format(malfunction_percentage), unsafe_allow_html=True)
    # Replace the existing availability chart section in show_dashboard() function
    # Starting from "# NEW: Availability Chart by Endoscope Type" until the end of that section

# Replace your availability chart section in show_dashboard() with this:

    # NEW: Availability Chart by Endoscope Type
    st.divider()
    with st.container(border=True):
        availability_stats = db.get_endoscope_availability_by_type()

        if not availability_stats.empty:
            # Create the grouped bar chart with proper side-by-side grouping
            fig_availability = go.Figure()
            
            # Add availability bars (dark green)
            fig_availability.add_trace(go.Bar(
                name='Disponibilité (%)',
                x=availability_stats['type'],
                y=availability_stats['disponibilite_pct'],
                marker_color='#2E7D32',  # Dark green
                text=availability_stats['disponibilite_pct'].apply(lambda x: f'{x}%'),
                textposition='auto',
                textfont=dict(color='white', size=12, family='Arial', weight='bold'),
                width=0.4,  # Make bars thinner for better grouping
                offset=-0.2,  # Position for grouping
            ))
            
            # Add unavailability bars (coral red)
            fig_availability.add_trace(go.Bar(
                name='Indisponibilité (%)',
                x=availability_stats['type'],
                y=availability_stats['indisponibilite_pct'],
                marker_color='#E57373',  # Coral red
                text=availability_stats['indisponibilite_pct'].apply(lambda x: f'{x}%' if x > 0 else ''),
                textposition='auto',
                textfont=dict(color='white', size=12, family='Arial', weight='bold'),
                width=0.4,  # Make bars thinner for better grouping
                offset=0.2,  # Position for grouping
            ))
            
            # Update layout for proper grouping (NOT stacking)
            fig_availability.update_layout(
                title=dict(
                    text="Taux de disponibilité et d'indisponibilité des endoscopes",
                    font=dict(size=16, color='black', family='Arial'),
                    x=0.5,
                    xanchor='center'
                ),
                xaxis=dict(
                    title="",
                    tickangle=45,
                    tickfont=dict(size=11, color='black', family='Arial'),
                    showgrid=False,
                    showline=True,
                    linecolor='black',
                    linewidth=1
                ),
                yaxis=dict(
                    title="Taux (%)",
                    titlefont=dict(size=12, color='black', family='Arial'),
                    tickfont=dict(size=11, color='black', family='Arial'),
                    showgrid=True,
                    gridcolor='lightgray',
                    gridwidth=0.5,
                    showline=True,
                    linecolor='black',
                    linewidth=1,
                    range=[0, 110]
                ),
                barmode='group',  # THIS IS KEY - Group bars side by side, not stack
                bargap=0.6,  # Space between groups
                bargroupgap=0.15,  # Space between bars in the same group
                height=500,
                width=1000,
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=0.98,
                    xanchor="right",
                    x=0.98,
                    bgcolor="rgba(255,255,255,0.8)",
                    bordercolor="black",
                    borderwidth=1,
                    font=dict(size=11, color='black', family='Arial')
                ),
                plot_bgcolor='white',
                paper_bgcolor='white',
                margin=dict(l=60, r=60, t=80, b=120)
            )
            
            # Add borders around the plot area
            fig_availability.update_xaxes(mirror=True)
            fig_availability.update_yaxes(mirror=True)
            
            st.plotly_chart(fig_availability, use_container_width=True, key="plotly_availability")
            
            
            
            # Add a summary table below the chart
            with st.expander("Détails par Type d'Endoscope"):
                display_stats = availability_stats[['type', 'total', 'fonctionnel', 'en_panne', 'disponibilite_pct', 'indisponibilite_pct']].copy()
                display_stats.columns = ['Type', 'Total', 'Fonctionnels', 'En Panne', 'Disponibilité (%)', 'Indisponibilité (%)']
                st.dataframe(display_stats, use_container_width=True)
        else:
            st.info("Aucune donnée disponible pour le graphique de disponibilité")

    # Original charts (keep existing ones)
     # Original charts (keep existing ones)
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("État des Endoscopes")
            if not stats['status_stats'].empty:
                fig_status = px.pie(
                    stats['status_stats'], 
                    values='count', 
                    names='etat',
                    title="Répartition par État",
                    color_discrete_map={'fonctionnel': '#4CAF50', 'en panne': '#F44336'}
                )
                st.plotly_chart(fig_status, use_container_width=True, key="plotly_status")
            else:
                st.info("Aucune donnée disponible")

    with col2:
        with st.container(border=True):
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
                st.plotly_chart(fig_location, use_container_width=True, key="plotly_location")
            else:
                st.info("Aucune donnée disponible")
@require_role(['admin'])
def show_admin_interface():
    """Admin interface for user management"""
    st.title("Administration des Utilisateurs")
    
    tab1, tab2 = st.tabs(["Gestion des Utilisateurs", "Ajouter un Utilisateur"])
    
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
                    st.write("")
                    st.write("")
                    if st.button("💾 Modifier", key=f"edit_{user['id']}"):
                        try:
                            updated = False
                            if new_role != current_role:
                                if db.update_user_role(user['id'], new_role):
                                    updated = True
                                    st.success(f"Rôle modifié pour {user['username']}")
                                else:
                                    st.error(f"Erreur lors de la modification du rôle pour {user['username']}")
                            
                            if new_password:
                                if db.update_user_password(user['id'], new_password):
                                    updated = True
                                    st.success(f"Mot de passe modifié pour {user['username']}")
                                else:
                                    st.error(f"Erreur lors de la modification du mot de passe pour {user['username']}")
                            
                            if updated:
                                st.rerun()
                            else:
                                st.warning("Aucune modification effectuée")
                        except Exception as e:
                            st.error(f"Erreur lors de la modification: {str(e)}")
                
                with col5:
                    st.write("")
                    st.write("")
                    if str(user['username']) != 'admin':  # Prevent admin deletion
                        if st.button("❌ Supprimer", key=f"delete_{user['id']}"):
                            try:
                                if db.delete_user(user['id']):
                                    st.success(f"Utilisateur {user['username']} supprimé avec succès!")
                                    st.rerun()
                                else:
                                    st.error(f"Erreur lors de la suppression de {user['username']}")
                            except Exception as e:
                                st.error(f"Erreur lors de la suppression: {str(e)}")
                    else:
                        # Remplace st.info par un bouton désactivé pour maintenir l'alignement
                        st.button("🔒 Admin protégé", key=f"protected_{user['id']}", disabled=True) 

                st.divider()
        else:
            st.info("Aucun utilisateur trouvé")
    
    with tab2:
        st.subheader("Ajouter un Nouvel Utilisateur")
        
        with st.form("add_user_form", clear_on_submit=True):
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
    user_role = get_user_role()
    st.title("Gestion de l'Inventaire des Endoscopes")
    
    tab1, tab2 = st.tabs(["Inventaire", "Ajouter Endoscope"])
    
    with tab1:
        st.subheader("Liste des Endoscopes")
        endoscopes_df = db.get_all_endoscopes()
        
        if not endoscopes_df.empty:
            # Add Print/Export section at the top
            col_print1, col_print2, col_print3 = st.columns([2, 2, 2])
            
            with col_print1:
                if st.button("📄 Imprimer Rapport Inventaire", key="print_inventory_biomedical", type="secondary"):
                    try:
                        with st.spinner("Génération du rapport d'inventaire..."):
                            pdf_bytes = generate_professional_pdf_report(
                                endoscopes_df, 
                                "Rapport d'Inventaire des Endoscopes",
                                "inventaire"
                            )
                            st.download_button(
                                label="💾 Télécharger le Rapport PDF",
                                data=pdf_bytes,
                                file_name=f"inventaire_endoscopes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                mime="application/pdf",
                                key="download_inventory_biomedical"
                            )
                            st.success("✅ Rapport d'inventaire généré avec succès!")
                    except Exception as e:
                        st.error(f"❌ Erreur lors de la génération du PDF: {str(e)}")
            
            with col_print2:
                # Filter by status for printing
                filter_status = st.selectbox("Filtrer par état", ['Tous', 'fonctionnel', 'en panne'], key="filter_print")
            
            with col_print3:
                # Filter by location for printing
                filter_location = st.selectbox("Filtrer par localisation", 
                                            ['Tous', 'En utilisation', 'En stock', 'En zone de stérilisation', 'En externe', 'En réforme'], 
                                            key="filter_location_print")
            
            # Apply filters if any are selected
            filtered_df = endoscopes_df.copy()
            if filter_status != 'Tous':
                filtered_df = filtered_df[filtered_df['etat'] == filter_status]
            if filter_location != 'Tous':
                filtered_df = filtered_df[filtered_df['localisation'] == filter_location]
            
            # Show filtered count
            if filter_status != 'Tous' or filter_location != 'Tous':
                st.info(f"📊 Affichage de {len(filtered_df)} endoscope(s) sur {len(endoscopes_df)} total")
                if st.button("🖨️ Imprimer Sélection Filtrée", key="print_filtered", type="primary"):
                    try:
                        with st.spinner("Génération du rapport filtré..."):
                            filter_title = f"Rapport d'Inventaire des Endoscopes"
                            if filter_status != 'Tous':
                                filter_title += f" - État: {filter_status}"
                            if filter_location != 'Tous':
                                filter_title += f" - Localisation: {filter_location}"
                            
                            pdf_bytes = generate_professional_pdf_report(
                                filtered_df, 
                                filter_title,
                                "inventaire"
                            )
                            st.download_button(
                                label="💾 Télécharger le Rapport Filtré",
                                data=pdf_bytes,
                                file_name=f"inventaire_filtre_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                mime="application/pdf",
                                key="download_filtered_inventory"
                            )
                            st.success("✅ Rapport filtré généré avec succès!")
                    except Exception as e:
                        st.error(f"❌ Erreur lors de la génération du PDF: {str(e)}")
            
            st.divider()
            
            # Use filtered_df for display
            current_df = filtered_df
            
            for idx, endoscope in current_df.iterrows():
                # Generate QR code for this endoscope
                qr_code = generate_qr_code(endoscope['id'], endoscope['designation'], endoscope['numero_serie'])
    
                with st.expander(f"📱 {endoscope['designation']} - {endoscope['numero_serie']} (QR: {endoscope['id']})"):
                    # --- Affichage des détails ---
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.write(f"**Marque:** {endoscope['marque']}")
                        st.write(f"**Modèle:** {endoscope['modele']}")
                        st.write(f"**État:** {endoscope['etat']}")
                        st.write(f"**Localisation:** {endoscope['localisation']}")
                        obs_value = endoscope.get('observation')
                        if obs_value and pd.notna(obs_value) and str(obs_value).strip():
                            st.write(f"**Observation:** {obs_value}")
                        st.write(f"**Créé par:** {endoscope.get('created_by', 'N/A')} le {endoscope['created_at']}")

                    # --- Boutons d'action ---
                    with col2:
                        edit_key = f"edit_mode_{endoscope['id']}"
                        if st.button("✏️ Modifier", key=f"edit_btn_{endoscope['id']}"):
                            st.session_state[edit_key] = True
                            st.rerun()

                        if st.button("🗑️ Supprimer", key=f"delete_btn_{endoscope['id']}", type="secondary"):
                            if db.delete_endoscope(endoscope['id']):
                                st.success("✅ Endoscope supprimé avec succès!")
                                st.rerun()
                            else:
                                st.error("❌ Erreur lors de la suppression.")

                    with col3:
                        # Display QR Code
                        if qr_code:
                            st.write("**QR Code:**")
                            st.image(f"data:image/png;base64,{qr_code}", width=120)
                        else:
                            st.write("QR Code non disponible")

                    # --- Formulaire de modification (si activé) ---
                    if st.session_state.get(edit_key, False):
                        st.info(f"Modification de : {endoscope['designation']}")
                        with st.form(f"update_form_{endoscope['id']}"):
                            new_designation = st.text_input("Désignation", value=endoscope['designation'])
                            new_marque = st.text_input("Marque", value=endoscope['marque'])
                            new_modele = st.text_input("Modèle", value=endoscope['modele'])
                            new_numero_serie = st.text_input("Numéro de série", value=endoscope['numero_serie'])
                            new_etat = st.selectbox("État", ['fonctionnel', 'en panne'], 
                                                  index=0 if endoscope['etat'] == 'fonctionnel' else 1)
                            new_observation = st.text_area("Observation", value=str(endoscope.get('observation', '')))
                            
                            location_options = ['En utilisation', 'En stock', 'En zone de stérilisation', 'En externe', 'En réforme']
                            current_location_index = location_options.index(endoscope['localisation']) if endoscope['localisation'] in location_options else 0
                            new_localisation = st.selectbox("Localisation", options=location_options, index=current_location_index)
                                                        
                            col_f1, col_f2 = st.columns(2)
                            with col_f1:
                                if st.form_submit_button("💾 Mettre à jour"):
                                    update_data = {
                                        'designation': new_designation, 'marque': new_marque, 'modele': new_modele,
                                        'numero_serie': new_numero_serie, 'etat': new_etat,
                                        'observation': new_observation, 'localisation': new_localisation
                                    }
                                    if db.update_endoscope(endoscope['id'], **update_data):
                                        st.success("✅ Endoscope mis à jour!")
                                        st.session_state.pop(edit_key, None)
                                        st.rerun()
                                    else:
                                        st.error("❌ Erreur lors de la mise à jour.")
                            with col_f2:
                                if st.form_submit_button("❌ Annuler"):
                                    st.session_state.pop(edit_key, None)
                                    st.rerun()
        else:
            st.info("Aucun endoscope dans l'inventaire.")

    with tab2:
        st.subheader("Ajouter un Nouvel Endoscope")
        with st.form("add_endoscope_form", clear_on_submit=True):
            designation = st.text_input("Désignation*")
            marque = st.text_input("Marque*")
            modele = st.text_input("Modèle*")
            numero_serie = st.text_input("Numéro de série*")
            etat = st.selectbox("État*", ['fonctionnel', 'en panne'])
            observation = st.text_area("Observation")
            localisation = st.selectbox("Localisation*", [
                'En utilisation', 'En stock', 'En zone de stérilisation', 'En externe', 'En réforme'])            
            submitted = st.form_submit_button("➕ Ajouter Endoscope")
            if submitted:
                if all([designation, marque, modele, numero_serie, localisation]):
                    if db.add_endoscope(designation, marque, modele, numero_serie, etat, observation, localisation, get_username()):
                        st.success("✅ Endoscope ajouté avec succès!")
                    else:
                        st.error("❌ Erreur: Numéro de série déjà existant.")
                else:
                    st.error("❌ Veuillez remplir tous les champs obligatoires (*)")

@require_role(['sterilisation', 'biomedical'])
def show_sterilization_interface():
    """Sterilization agent interface for sterilization reports"""
    st.title("🧴 Rapports de Stérilisation et Désinfection")
    tab1, tab2 = st.tabs(["Nouveau Rapport Stérilisation", "Gérer Rapports"])
    
    with tab1:
        st.subheader("Enregistrer un Rapport de Stérilisation")
        
        endoscopes_df = db.get_all_endoscopes()
        
        if endoscopes_df.empty:
            st.warning("⚠️ Aucun endoscope n'est disponible dans l'inventaire. Veuillez en ajouter un avant de créer un rapport.")
            return

        with st.form("sterilisation_report_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Informations Générales**")
                
                # Operator name is auto-filled and disabled
                st.text_input("Nom de l'opérateur*", value=get_username(), disabled=True)
                
                # Dropdown for endoscope selection
                endoscope_options = {row['id']: f"{row['designation']} - {row['numero_serie']}" for index, row in endoscopes_df.iterrows()}
                selected_id = st.selectbox(
                    "Endoscope*",
                    options=list(endoscope_options.keys()),
                    format_func=lambda x: endoscope_options.get(x, "Inconnu")
                )
                
                selected_endoscope_details = None
                if selected_id:
                    selected_endoscope_details = endoscopes_df[endoscopes_df['id'] == selected_id].iloc[0]
                    st.text_input("Numéro de série*", value=selected_endoscope_details['numero_serie'], disabled=True)

                medecin_responsable = st.text_input("Médecin responsable*")
                
                st.write("**Désinfection**")
                date_desinfection = st.date_input("Date de désinfection*")
                type_desinfection = st.selectbox("Type de désinfection*", ['manuel', 'automatique'])
                cycle = st.selectbox("Cycle*", ['complet', 'incomplet'])
                test_etancheite = st.selectbox("Test d'étanchéité*", ['réussi', 'échoué'])
            
            with col2:
                st.write("**Horaires**")
                col_t1, col_t2 = st.columns(2)

                with col_t1:
                    heure_debut_time = st.time_input("Heure de début*", value=dt.time(8, 0))
                with col_t2:
                    heure_fin_time = st.time_input("Heure de fin*", value=dt.time(17, 0))

                # Convertir en format string HH:MM
                heure_debut = heure_debut_time.strftime("%H:%M")
                heure_fin = heure_fin_time.strftime("%H:%M")
                
                salle = st.text_input("Salle*")
                type_acte = st.text_input("Type d'acte*")
                
                st.write("**    État**")
                etat_endoscope = st.selectbox("État de l'endoscope*", ['fonctionnel', 'en panne'])

                # Toujours afficher nature de la panne, mais avec validation conditionnelle
                if etat_endoscope == 'en panne':
                    nature_panne = st.text_area("Nature de la panne*", 
                                            placeholder="Décrivez la nature de la panne...",
                                            help="Ce champ est obligatoire pour les endoscopes en panne")
                else:
                    nature_panne = st.text_area("Observations sur l'état", 
                                            placeholder="Optionnel - Observations générales",
                                            help="Champ optionnel quand l'endoscope est fonctionnel")
            
            if st.form_submit_button(" Enregistrer Rapport de Stérilisation"):
                # Validation
                if not selected_id or not medecin_responsable or not salle or not type_acte:
                    st.error("Veuillez remplir tous les champs obligatoires (*)")
                elif etat_endoscope == 'en panne' and (not nature_panne or not nature_panne.strip()):
                    st.error("Veuillez spécifier la nature de la panne pour un endoscope en panne")
                elif heure_debut_time >= heure_fin_time:
                    st.error("L'heure de fin doit être postérieure à l'heure de début")
                else:
                    nom_operateur = get_username()
                    # Re-fetch details inside the submit block to be safe
                    selected_endoscope_details = endoscopes_df[endoscopes_df['id'] == selected_id].iloc[0]
                    endoscope_name = selected_endoscope_details['designation']
                    numero_serie_val = selected_endoscope_details['numero_serie']
                    
                    # Nettoyer la valeur nature_panne
                    nature_panne_cleaned = nature_panne.strip() if nature_panne else None
                    if etat_endoscope == 'fonctionnel' and not nature_panne_cleaned:
                        nature_panne_cleaned = None

                    if db.add_sterilisation_report(
                        nom_operateur, endoscope_name, numero_serie_val, medecin_responsable,
                        date_desinfection, type_desinfection, cycle, test_etancheite,
                        heure_debut, heure_fin, "N/A", salle, type_acte,
                        etat_endoscope, nature_panne_cleaned, nom_operateur
                    ):
                        st.success("Rapport de stérilisation enregistré avec succès!")
                        st.rerun()
                    else:
                        st.error("Erreur lors de l'enregistrement - Vérifiez le format des données")
    
    with tab2:
        st.subheader("Gérer les Rapports de Stérilisation")
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_by_user = st.checkbox("Mes rapports uniquement", value=(get_user_role() == 'sterilisation'))
        with col2:
            filter_date = st.date_input("Filtrer par date", value=None)
        with col3:
            filter_etat = st.selectbox("Filtrer par état", ['Tous', 'fonctionnel', 'en panne'])
        if filter_by_user or get_user_role() == 'sterilisation':
            steril_reports = db.get_user_sterilisation_reports(get_username())
        else:
            steril_reports = db.get_all_sterilisation_reports()
        if not steril_reports.empty:
            if filter_date:
                steril_reports = steril_reports[steril_reports['date_desinfection'] == str(filter_date)]
            if filter_etat != 'Tous':
                steril_reports = steril_reports[steril_reports['etat_endoscope'] == filter_etat]
            if not steril_reports.empty:
                st.write(f"**Rapports trouvés: {len(steril_reports)}**")
                for idx, report in steril_reports.iterrows():
                    with st.expander(f"📋 Rapport #{report['id']} - {report['endoscope']} ({report['date_desinfection']})"):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**Opérateur:** {report['nom_operateur']}")
                            st.write(f"**Médecin:** {report['medecin_responsable']}")
                            st.write(f"**Désinfection:** {report['type_desinfection']} - {report['cycle']}")
                            st.write(f"**Test étanchéité:** {report['test_etancheite']}")
                            st.write(f"**Horaires:** {report['heure_debut']} - {report['heure_fin']}")
                            st.write(f"**Salle:** {report['salle']}")
                            st.write(f"**État:** {report['etat_endoscope']}")
                            try:
                                nature_panne = str(report['nature_panne'])
                                if nature_panne not in ['nan', 'None', '']:
                                    st.write(f"**Nature panne:** {nature_panne}")
                            except:
                                pass
                        with col2:
                            can_modify = db.can_user_modify_sterilisation_report(get_user_role(), report['id'], get_username())
                            if can_modify:
                                if st.button("✏️ Modifier", key=f"edit_steril_{report['id']}"):
                                    st.session_state[f"edit_steril_{report['id']}"] = True
                                    st.rerun()
                                if st.button("🗑️ Supprimer", key=f"del_steril_{report['id']}"):
                                    try:
                                        if db.delete_sterilisation_report(report['id']):
                                            st.success("✅ Rapport supprimé avec succès!")
                                            st.rerun()
                                        else:
                                            st.error("❌ Erreur lors de la suppression du rapport")
                                    except Exception as e:
                                        st.error(f"❌ Erreur lors de la suppression: {str(e)}")
                            else:
                                st.info("Lecture seule")
                        edit_key = f"edit_steril_{report['id']}"
                        if st.session_state.get(edit_key, False):
                            st.info("Modification du rapport en cours...")
                            with st.form(f"edit_sterilisation_report_form_{report['id']}"):
                                new_nom_operateur = st.text_input("Nom de l'opérateur*", value=report['nom_operateur'])
                                new_endoscope = st.text_input("Endoscope*", value=report['endoscope'])
                                new_numero_serie = st.text_input("Numéro de série*", value=report['numero_serie'])
                                new_medecin_responsable = st.text_input("Médecin responsable*", value=report['medecin_responsable'])
                                new_date_desinfection = st.date_input("Date de désinfection*", value=pd.to_datetime(report['date_desinfection']).date())
                                new_type_desinfection = st.selectbox("Type de désinfection*", ['manuel', 'automatique'], index=0 if report['type_desinfection']=='manuel' else 1)
                                new_cycle = st.selectbox("Cycle*", ['complet', 'incomplet'], index=0 if report['cycle']=='complet' else 1)
                                new_test_etancheite = st.selectbox("Test d'étanchéité*", ['réussi', 'échoué'], index=0 if report['test_etancheite']=='réussi' else 1)
                                new_heure_debut = st.text_input("Heure de début* (HH:MM)", value=report['heure_debut'])
                                new_heure_fin = st.text_input("Heure de fin* (HH:MM)", value=report['heure_fin'])
                                new_salle = st.text_input("Salle*", value=report['salle'])
                                new_type_acte = st.text_input("Type d'acte*", value=report['type_acte'])
                                new_etat_endoscope = st.selectbox("État de l'endoscope*", ['fonctionnel', 'en panne'], index=0 if report['etat_endoscope']=='fonctionnel' else 1)
                                new_nature_panne = st.text_area("Nature de la panne*", value=report['nature_panne'] if report['etat_endoscope']=='en panne' else '') if new_etat_endoscope=='en panne' else None
                                if st.form_submit_button("💾 Enregistrer les modifications"):
                                    try:
                                        # Validate required fields
                                        required_fields = [new_nom_operateur, new_endoscope, new_numero_serie, 
                                                         new_medecin_responsable, new_salle, new_type_acte, 
                                                         new_heure_debut, new_heure_fin]
                                        
                                        if not all(required_fields):
                                            st.error("❌ Veuillez remplir tous les champs obligatoires (*)")
                                        elif new_etat_endoscope == 'en panne' and not new_nature_panne:
                                            st.error("❌ Veuillez spécifier la nature de la panne")
                                        elif ":" not in new_heure_debut or ":" not in new_heure_fin:
                                            st.error("❌ Format d'heure invalide. Utilisez HH:MM (ex: 14:30)")
                                        else:
                                            update_fields = {
                                                'nom_operateur': new_nom_operateur,
                                                'endoscope': new_endoscope,
                                                'numero_serie': new_numero_serie,
                                                'medecin_responsable': new_medecin_responsable,
                                                'date_desinfection': str(new_date_desinfection),
                                                'type_desinfection': new_type_desinfection,
                                                'cycle': new_cycle,
                                                'test_etancheite': new_test_etancheite,
                                                'heure_debut': new_heure_debut,
                                                'heure_fin': new_heure_fin,
                                                'salle': new_salle,
                                                'type_acte': new_type_acte,
                                                'etat_endoscope': new_etat_endoscope,
                                                'nature_panne': new_nature_panne,
                                                'procedure_medicale': report.get('procedure_medicale', 'N/A')
                                            }
                                            
                                            if db.update_sterilisation_report(report['id'], **update_fields):
                                                st.success("✅ Rapport modifié avec succès!")
                                                st.session_state.pop(edit_key, None)
                                                st.rerun()
                                            else:
                                                st.error("❌ Erreur lors de la modification du rapport.")
                                    except Exception as e:
                                        st.error(f"❌ Erreur lors de la modification: {str(e)}")
                            if st.button("❌ Annuler la modification", key=f"cancel_edit_{report['id']}"):
                                st.session_state.pop(edit_key, None)
                                st.rerun()
            else:
                st.info("Aucun rapport correspondant aux filtres")
        else:
            st.info("Aucun rapport de stérilisation disponible")

def show_archives_interface():
    """Archives interface for all users with filtering and sorting"""
    st.title("Archives")

    user_role = get_user_role()
    
    tab_titles = ["Rapports de Stérilisation"]
    if user_role in ['biomedical', 'admin']:
        tab_titles.append("Historique Inventaire")
    
    tabs = st.tabs(tab_titles)
    
    # --- Tab 1: Sterilization Reports ---
    with tabs[0]:
        st.subheader("Historique des Rapports de Stérilisation")
        steril_reports = db.get_all_sterilisation_reports()
        
        if not steril_reports.empty:
            filtered_steril = steril_reports.copy()
            with st.expander("Filtres et Tri pour les Rapports"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    operators = st.multiselect("Opérateur", options=steril_reports['nom_operateur'].unique(), key="op_filter")
                    medecins = st.multiselect("Médecin", options=steril_reports['medecin_responsable'].unique(), key="med_filter")
                with col2:
                    states = st.multiselect("État de l'endoscope", options=steril_reports['etat_endoscope'].unique(), key="state_filter")
                    start_date = st.date_input("Du", None, key="steril_start")
                    end_date = st.date_input("Au", None, key="steril_end")
                with col3:
                    sort_by_steril = st.selectbox("Trier par", options=list(steril_reports.columns), index=5, key="sort_steril_col")
                    sort_order_steril = st.radio("Ordre", ["Descendant", "Ascendant"], key="sort_steril_order")

            # Apply filters
            if operators: filtered_steril = filtered_steril[filtered_steril['nom_operateur'].isin(operators)]
            if medecins: filtered_steril = filtered_steril[filtered_steril['medecin_responsable'].isin(medecins)]
            if states: filtered_steril = filtered_steril[filtered_steril['etat_endoscope'].isin(states)]
            if start_date: filtered_steril = filtered_steril[pd.to_datetime(filtered_steril['date_desinfection']).dt.date >= start_date]
            if end_date: filtered_steril = filtered_steril[pd.to_datetime(filtered_steril['date_desinfection']).dt.date <= end_date]
            if sort_by_steril: filtered_steril = filtered_steril.sort_values(by=sort_by_steril, ascending=(sort_order_steril == 'Ascendant'))
            
            st.dataframe(filtered_steril.drop(columns=['procedure_medicale'], errors='ignore'), use_container_width=True)
            
            # Single PDF Download Button
            if st.button("📄 Télécharger Rapport PDF", key="download_pdf_steril", type="primary"):
                try:
                    with st.spinner("Génération du rapport PDF en cours..."):
                        # Prepare data for PDF
                        pdf_data = filtered_steril.drop(columns=['procedure_medicale'], errors='ignore')
                        
                        # Generate professional PDF
                        pdf_bytes = generate_professional_pdf_report(
                            pdf_data, 
                            "Rapports de Stérilisation et Désinfection",
                            "sterilisation"
                        )
                        
                        # Download button
                        st.download_button(
                            label="💾 Télécharger le Rapport PDF",
                            data=pdf_bytes,
                            file_name=f"rapport_sterilisation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf",
                            key="download_steril_final"
                        )
                        st.success("✅ Rapport PDF généré avec succès!")
                except Exception as e:
                    st.error(f"❌ Erreur lors de la génération du PDF: {str(e)}")

    # --- Tab 2: Inventory History ---
    if user_role in ['biomedical', 'admin']:
        with tabs[1]:
            st.subheader("Historique de l'Inventaire des Endoscopes")
            inventory_df = db.get_all_endoscopes()
            
            if not inventory_df.empty:
                filtered_inventory = inventory_df.copy()
                
                # Ajout des filtres et tri pour l'inventaire
                with st.expander("Filtres et Tri pour l'Inventaire"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        # Filtres par état
                        etats = st.multiselect("État", 
                                            options=inventory_df['etat'].unique(), 
                                            key="inv_etat_filter")
                        
                        # Filtres par marque
                        marques = st.multiselect("Marque", 
                                            options=inventory_df['marque'].unique(), 
                                            key="inv_marque_filter")
                    
                    with col2:
                        # Filtres par localisation
                        localisations = st.multiselect("Localisation", 
                                                    options=inventory_df['localisation'].unique(), 
                                                    key="inv_localisation_filter")
                        
                        # Filtres par créateur
                        createurs = st.multiselect("Créé par", 
                                                options=inventory_df['created_by'].unique(), 
                                                key="inv_createur_filter")
                    
                    with col3:
                        # Options de tri
                        sort_by_inv = st.selectbox("Trier par", 
                                                options=['designation', 'marque', 'modele', 'numero_serie', 
                                                        'etat', 'localisation', 'created_at', 'created_by'], 
                                                index=0, 
                                                key="sort_inv_col")
                        
                        sort_order_inv = st.radio("Ordre", ["Descendant", "Ascendant"], key="sort_inv_order")
                        
                        # Recherche par texte
                        search_text = st.text_input("Rechercher (désignation, modèle, N° série)", 
                                                key="inv_search_text")

                # Application des filtres
                if etats: 
                    filtered_inventory = filtered_inventory[filtered_inventory['etat'].isin(etats)]
                if marques: 
                    filtered_inventory = filtered_inventory[filtered_inventory['marque'].isin(marques)]
                if localisations: 
                    filtered_inventory = filtered_inventory[filtered_inventory['localisation'].isin(localisations)]
                if createurs: 
                    filtered_inventory = filtered_inventory[filtered_inventory['created_by'].isin(createurs)]
                
                # Recherche par texte
                if search_text:
                    mask = (
                        filtered_inventory['designation'].str.contains(search_text, case=False, na=False) |
                        filtered_inventory['modele'].str.contains(search_text, case=False, na=False) |
                        filtered_inventory['numero_serie'].str.contains(search_text, case=False, na=False)
                    )
                    filtered_inventory = filtered_inventory[mask]
                
                # Application du tri
                if sort_by_inv: 
                    filtered_inventory = filtered_inventory.sort_values(
                        by=sort_by_inv, 
                        ascending=(sort_order_inv == 'Ascendant')
                    )
                
                # Affichage du nombre de résultats
                st.info(f"📊 Affichage de {len(filtered_inventory)} endoscope(s) sur {len(inventory_df)} total")
                
                display_inventory = filtered_inventory.copy()

                # Remplacer la colonne 'id' par une image QR Code
                display_inventory['QR Code'] = display_inventory.apply(
                    lambda row: f'<img src="data:image/png;base64,{generate_qr_code(row["id"], row["designation"], row["numero_serie"])}" width="80"/>',
                    axis=1
                )

                # Optionnel : retirer l'ID si tu ne veux plus le voir
                display_inventory.drop(columns=['id'], inplace=True, errors='ignore')

                # Réorganisation des colonnes : QR Code en premier
                cols = ['QR Code'] + [col for col in display_inventory.columns if col != 'QR Code']
                display_inventory = display_inventory[cols]

                # Affichage en HTML pour voir les images
                st.write(display_inventory.to_html(escape=False, index=False), unsafe_allow_html=True)

                
                # Single PDF Download Button for Inventory (avec données filtrées)
                if st.button("📄 Télécharger Rapport Inventaire PDF", key="download_pdf_inventory", type="primary"):
                    try:
                        with st.spinner("Génération du rapport d'inventaire PDF en cours..."):
                            # Utiliser les données filtrées pour le PDF
                            pdf_title = "Historique de l'Inventaire des Endoscopes"
                            if len(filtered_inventory) < len(inventory_df):
                                pdf_title += f" (Filtré - {len(filtered_inventory)} sur {len(inventory_df)})"
                            
                            pdf_bytes = generate_professional_pdf_report(
                                filtered_inventory,  # Utiliser les données filtrées
                                pdf_title,
                                "inventaire"
                            )
                            st.download_button(
                                label="💾 Télécharger le Rapport Inventaire PDF",
                                data=pdf_bytes,
                                file_name=f"rapport_inventaire_filtre_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                mime="application/pdf",
                                key="download_inventory_final"
                            )
                            st.success("✅ Rapport d'inventaire PDF généré avec succès!")
                    except Exception as e:
                        st.error(f"❌ Erreur lors de la génération du PDF: {str(e)}")
            else:
                st.info("Aucun endoscope dans l'inventaire.")

if __name__ == "__main__":
    main()