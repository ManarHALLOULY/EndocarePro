import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

class EmailAlertManager:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.email_user = os.getenv("EMAIL_USER", "your_email@gmail.com")
        self.email_password = os.getenv("EMAIL_PASSWORD", "your_app_password")
        self.alert_recipients = os.getenv("ALERT_RECIPIENTS", "admin@hospital.com").split(",")
    
    def send_malfunction_alert(self, percentage, broken_count, total_count):
        """Send email alert when malfunction rate exceeds 50%"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = ", ".join(self.alert_recipients)
            msg['Subject'] = "🚨 ALERTE EndoTrace - Taux de panne élevé"
            
            # Email body
            body = f"""
            <html>
            <body>
                <h2>🚨 Alerte Système EndoTrace</h2>
                <p><strong>Date:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                
                <div style="background-color: #ffebee; padding: 15px; border-left: 4px solid #f44336; margin: 10px 0;">
                    <h3 style="color: #d32f2f; margin-top: 0;">Taux de panne critique détecté</h3>
                    <ul>
                        <li><strong>Pourcentage d'endoscopes en panne:</strong> {percentage:.1f}%</li>
                        <li><strong>Nombre d'endoscopes en panne:</strong> {broken_count}</li>
                        <li><strong>Total d'endoscopes:</strong> {total_count}</li>
                    </ul>
                </div>
                
                <p><strong>Action requise:</strong> Le taux de panne des endoscopes a dépassé le seuil critique de 50%. 
                Une intervention immédiate est recommandée pour évaluer et réparer les équipements défaillants.</p>
                
                <p>Veuillez vous connecter au système EndoTrace pour plus de détails.</p>
                
                <hr>
                <p style="font-size: 12px; color: #666;">
                    Cet email a été généré automatiquement par le système EndoTrace.
                </p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            text = msg.as_string()
            server.sendmail(self.email_user, self.alert_recipients, text)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"Erreur lors de l'envoi de l'email: {e}")
            return False
    
    def test_email_configuration(self):
        """Test email configuration"""
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            server.quit()
            return True
        except Exception as e:
            print(f"Erreur de configuration email: {e}")
            return False
