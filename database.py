import sqlite3
import os
from datetime import datetime
import pandas as pd


class DatabaseManager:

    def __init__(self, db_path="endotrace.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize database with schema from init.sql"""
        conn = sqlite3.connect(self.db_path)
        try:
            # Read and execute init.sql
            with open('init.sql', 'r', encoding='utf-8') as f:
                sql_script = f.read()
            conn.executescript(sql_script)
            conn.commit()
        except Exception as e:
            print(f"Error initializing database: {e}")
        finally:
            conn.close()

    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def authenticate_user(self, username, password):
        """Authenticate user and return role"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role FROM users WHERE username = ? AND password = ?",
                (username, password))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()

    def get_all_users(self):
        """Get all users (admin only)"""
        conn = self.get_connection()
        try:
            return pd.read_sql_query(
                "SELECT id, username, role, created_at FROM users ORDER BY created_at DESC",
                conn)
        finally:
            conn.close()

    def add_user(self, username, password, role):
        """Add new user"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, password, role))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def update_user_role(self, user_id, new_role):
        """Update user role"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET role = ? WHERE id = ?",
                           (new_role, user_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_user(self, user_id):
        """Delete user"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id, ))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def add_endoscope(self, designation, marque, modele, numero_serie, etat,
                      observation, localisation, created_by):
        """Add new endoscope to inventory"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO endoscopes 
                   (designation, marque, modele, numero_serie, etat, observation, localisation, created_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (designation, marque, modele, numero_serie, etat, observation,
                 localisation, created_by))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_all_endoscopes(self):
        """Get all endoscopes"""
        conn = self.get_connection()
        try:
            return pd.read_sql_query(
                "SELECT * FROM endoscopes ORDER BY created_at DESC", conn)
        finally:
            conn.close()

    def update_endoscope(self, endoscope_id, **kwargs):
        """Update endoscope record"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values()) + [endoscope_id]

            cursor.execute(
                f"UPDATE endoscopes SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_endoscope(self, endoscope_id):
        """Delete endoscope"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM endoscopes WHERE id = ?",
                           (endoscope_id, ))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def add_usage_report(self, nom_operateur, endoscope, numero_serie, medecin,
                         etat, nature_panne, created_by):
        """Add usage report"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO usage_reports 
                   (nom_operateur, endoscope, numero_serie, medecin, etat, nature_panne, created_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (nom_operateur, endoscope, numero_serie, medecin, etat,
                 nature_panne, created_by))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    def get_all_usage_reports(self):
        """Get all usage reports for archives"""
        conn = self.get_connection()
        try:
            return pd.read_sql_query(
                """SELECT id as [ID opérateur], endoscope as [Endoscope], 
                   numero_serie as [Numéro de série], nature_panne as [Nature de la panne],
                   medecin as [Médecin], date_utilisation as [Date d'utilisation]
                   FROM usage_reports ORDER BY date_utilisation DESC""",
                conn
            )
        finally:
            conn.close()

    def get_dashboard_stats(self):
        """Get statistics for dashboard"""
        conn = self.get_connection()
        try:
            # Get endoscope status statistics
            status_stats = pd.read_sql_query(
                "SELECT etat, COUNT(*) as count FROM endoscopes GROUP BY etat",
                conn)

            # Get location statistics
            location_stats = pd.read_sql_query(
                "SELECT localisation, COUNT(*) as count FROM endoscopes GROUP BY localisation",
                conn)

            # Get total counts
            total_endoscopes = pd.read_sql_query(
                "SELECT COUNT(*) as total FROM endoscopes",
                conn).iloc[0]['total']

            return {
                'status_stats': status_stats,
                'location_stats': location_stats,
                'total_endoscopes': total_endoscopes
            }
        finally:
            conn.close()

    def get_malfunction_percentage(self):
        """Calculate percentage of malfunctioning endoscopes"""
        conn = self.get_connection()
        try:
            result = pd.read_sql_query(
                """SELECT 
                   COUNT(*) as total,
                   SUM(CASE WHEN etat = 'en panne' THEN 1 ELSE 0 END) as en_panne
                   FROM endoscopes""", conn)

            if result.iloc[0]['total'] > 0:
                percentage = (result.iloc[0]['en_panne'] /
                              result.iloc[0]['total']) * 100
                return percentage, result.iloc[0]['en_panne'], result.iloc[0][
                    'total']
            return 0, 0, 0
        finally:
            conn.close()
    
    def get_user_usage_reports(self, username):
        """Get usage reports created by specific user"""
        conn = self.get_connection()
        try:
            return pd.read_sql_query(
                """SELECT * FROM usage_reports 
                   WHERE created_by = ? 
                   ORDER BY date_utilisation DESC""",
                conn, params=[username]
            )
        finally:
            conn.close()
    
    def update_usage_report(self, report_id, **kwargs):
        """Update usage report"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values()) + [report_id]
            
            cursor.execute(
                f"UPDATE usage_reports SET {set_clause} WHERE id = ?",
                values
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def delete_usage_report(self, report_id):
        """Delete usage report"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM usage_reports WHERE id = ?", (report_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def update_user_password(self, user_id, new_password):
        """Update user password"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET password = ? WHERE id = ?",
                (new_password, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def purge_all_endoscopes(self):
        """Delete all endoscope records (admin only)"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM endoscopes")
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
    
    def purge_all_usage_reports(self):
        """Delete all usage reports (admin only)"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM usage_reports")
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
    
    def get_database_statistics(self):
        """Get comprehensive database statistics"""
        conn = self.get_connection()
        try:
            stats = {}
            
            # Users count
            result = pd.read_sql_query("SELECT COUNT(*) as count FROM users", conn)
            stats['total_users'] = result.iloc[0]['count']
            
            # Endoscopes count
            result = pd.read_sql_query("SELECT COUNT(*) as count FROM endoscopes", conn)
            stats['total_endoscopes'] = result.iloc[0]['count']
            
            # Usage reports count
            result = pd.read_sql_query("SELECT COUNT(*) as count FROM usage_reports", conn)
            stats['total_reports'] = result.iloc[0]['count']
            
            # Users by role
            result = pd.read_sql_query("SELECT role, COUNT(*) as count FROM users GROUP BY role", conn)
            stats['users_by_role'] = result
            
            return stats
        finally:
            conn.close()
