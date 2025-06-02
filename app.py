import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta, date, time
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'secret_key'

DB_CONFIG = {
    'host': 'localhost',
    'database': 'gestion_evenements',
    'user': 'root',
    'password': ''
}

class DatabaseManager:
    def __init__(self):
        self.connection = None
    
    def connect(self):
        """Établir la connexion à la base de données"""
        try:
            if self.connection and self.connection.is_connected():
                return True
                
            self.connection = mysql.connector.connect(**DB_CONFIG)
            if self.connection.is_connected():
                print("Connexion à MySQL réussie")
                return True
        except Error as e:
            print(f"Erreur de connexion à MySQL: {e}")
            return False
    
    def disconnect(self):
        """Fermer la connexion à la base de données"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("Connexion MySQL fermée")
    
    def execute_query(self, query, params=None, fetch=False):
        """Exécuter une requête SQL"""
        try:
            if not self.connection or not self.connection.is_connected():
                if not self.connect():
                    return None if fetch else False
            
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            
            if fetch:
                result = cursor.fetchall()
                cursor.close()
                return result
            else:
                self.connection.commit()
                cursor.close()
                return True
        except Error as e:
            print(f"Erreur lors de l'exécution de la requête: {e}")
            print(f"Requête: {query}")
            print(f"Paramètres: {params}")
            return None if fetch else False

db_manager = DatabaseManager()

class EvenementManager:
    def __init__(self):
        db_manager.connect()
    
    def get_tous_evenements(self):
        """Récupérer tous les événements"""
        query = """
        SELECT id, titre, type, date, heure, duree, lieu, description, 
               capacite, participants, created_at 
        FROM evenements 
        ORDER BY date, heure
        """
        return db_manager.execute_query(query, fetch=True)
    
    def get_evenement_par_id(self, evenement_id):
        """Récupérer un événement par son ID"""
        query = "SELECT * FROM evenements WHERE id = %s"
        result = db_manager.execute_query(query, (evenement_id,), fetch=True)
        return result[0] if result else None
    
    def ajouter_evenement(self, data):
        """Ajouter un nouvel événement"""
        print(f"DEBUG - Données reçues pour ajout: {data}")
        
        query = """
        INSERT INTO evenements (titre, type, date, heure, duree, lieu, description, capacite, participants)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['titre'],
            data['type'],
            data['date'],
            data['heure'],
            data['duree'],
            data['lieu'],
            data.get('description', ''),
            data['capacite'],
            data.get('participants', 0)
        )
        
        print(f"DEBUG - Paramètres SQL: {params}")
        result = db_manager.execute_query(query, params)
        print(f"DEBUG - Résultat insertion: {result}")
        return result
    
    def modifier_evenement(self, evenement_id, data):
        """Modifier un événement existant"""
        query = """
        UPDATE evenements 
        SET titre=%s, type=%s, date=%s, heure=%s, duree=%s, lieu=%s, 
            description=%s, capacite=%s, participants=%s
        WHERE id=%s
        """
        params = (
            data['titre'],
            data['type'],
            data['date'],
            data['heure'],
            data['duree'],
            data['lieu'],
            data.get('description', ''),
            data['capacite'],
            data.get('participants', 0),
            evenement_id
        )
        return db_manager.execute_query(query, params)
    
    def supprimer_evenement(self, evenement_id):
        """Supprimer un événement"""
        query = "DELETE FROM evenements WHERE id = %s"
        return db_manager.execute_query(query, (evenement_id,))
    
    def incrementer_participants(self, evenement_id):
        """Incrémenter le nombre de participants"""
        query = "UPDATE evenements SET participants = participants + 1 WHERE id = %s"
        return db_manager.execute_query(query, (evenement_id,))
    
    def decrementer_participants(self, evenement_id):
        """Décrémenter le nombre de participants"""
        query = """
        UPDATE evenements 
        SET participants = CASE 
            WHEN participants > 0 THEN participants - 1 
            ELSE 0 
        END 
        WHERE id = %s
        """
        return db_manager.execute_query(query, (evenement_id,))
    
    def get_evenements_dashboard(self):
        evenements = self.get_tous_evenements()
        if not evenements:
            return []
            
        now = datetime.now()

        for event in evenements:
            event_date = event.get('date')
            event_heure = event.get('heure')
            
            if isinstance(event_heure, timedelta):
                event_heure = (datetime.min + event_heure).time()
            elif isinstance(event_heure, datetime):
                event_heure = event_heure.time()
            
            if isinstance(event_date, date) and isinstance(event_heure, time):
                event_datetime = datetime.combine(event_date, event_heure)
                event['time_diff'] = event_datetime - now
            else:
                event['time_diff'] = timedelta(seconds=-1)
        
        return evenements

    def get_statistiques(self):
        """Calculer les statistiques pour le dashboard"""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        stats = {}

        query = "SELECT COUNT(*) as count FROM evenements"
        result = db_manager.execute_query(query, fetch=True)
        stats['total_evenements'] = result[0]['count'] if result else 0
        
        query = "SELECT COUNT(*) as count FROM evenements WHERE date = %s"
        result = db_manager.execute_query(query, (today,), fetch=True)
        stats['evenements_aujourd_hui'] = result[0]['count'] if result else 0
        
        query = "SELECT COUNT(*) as count FROM evenements WHERE date BETWEEN %s AND %s"
        result = db_manager.execute_query(query, (week_start, week_end), fetch=True)
        stats['evenements_cette_semaine'] = result[0]['count'] if result else 0
        
        query = "SELECT DISTINCT type FROM evenements"
        result = db_manager.execute_query(query, fetch=True)
        stats['types_evenements'] = [row['type'] for row in result] if result else []
        
        return stats

evenement_manager = EvenementManager()

def formater_temps_restant(time_diff):
    """Formater le temps restant en format lisible"""
    if time_diff.total_seconds() < 0:
        return "Événement passé"
    
    days = time_diff.days
    hours, remainder = divmod(time_diff.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    if days > 0:
        return f"Dans {days}j {hours}h"
    elif hours > 0:
        return f"Dans {hours}h {minutes}min"
    else:
        return f"Dans {minutes}min"

app.jinja_env.globals.update(formater_temps_restant=formater_temps_restant)

@app.route('/')
def index():
    """Page d'accueil"""
    evenements = evenement_manager.get_tous_evenements()
    return render_template('index.html', evenements=evenements)

@app.route('/dashboard')
def dashboard():
    """Page du dashboard"""
    evenements = evenement_manager.get_evenements_dashboard()
    now = datetime.now()
    
    notifications = {
        'urgent': [],     
        'bientot': [],    
        'aujourd_hui': [], 
        'demain': []       
    }
    
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    for event in evenements:
        time_diff = event['time_diff']
        event_date = event['date']
        
        if isinstance(event_date, date):
            event['date'] = event_date.strftime('%Y-%m-%d')
        if event['heure']:
            event['heure'] = event['heure'].strftime('%H:%M') if hasattr(event['heure'], 'strftime') else str(event['heure'])
        
        if time_diff.total_seconds() > 0:  
            if time_diff.total_seconds() <= 1800: 
                notifications['urgent'].append(event)
            elif time_diff.total_seconds() <= 7200:  
                notifications['bientot'].append(event)
            elif event_date == today:
                notifications['aujourd_hui'].append(event)
            elif event_date == tomorrow:
                notifications['demain'].append(event)
    
    evenements_a_venir = []
    end_date = today + timedelta(days=7)
    
    for event in evenements:
        if event['date'] and isinstance(event['date'], str):
            event_date = datetime.strptime(event['date'], '%Y-%m-%d').date()
        else:
            event_date = event['date']
            
        if today <= event_date <= end_date:
            evenements_a_venir.append(event)
    
    stats = evenement_manager.get_statistiques()
    
    return render_template('dashboard.html', 
                         notifications=notifications,
                         evenements_a_venir=evenements_a_venir[:10],  
                         stats=stats)

@app.route('/events', methods=['GET', 'POST'])
def events():
    if request.method == 'POST':
        print(f"DEBUG - Données du formulaire: {request.form.to_dict()}")
        
        try:
            titre = request.form.get('title', '').strip()
            type_event = request.form.get('type', '').strip()
            date_event = request.form.get('date', '').strip()
            heure_event = request.form.get('time', '').strip()
            lieu_event = request.form.get('location', '').strip()
            duree_str = request.form.get('duration', '60').strip()
            capacite_str = request.form.get('capacity', '0').strip()
            description = request.form.get('description', '').strip()
            
            print(f"DEBUG - Champs extraits: titre={titre}, type={type_event}, date={date_event}, heure={heure_event}")
            
            champs_requis = {
                'titre': titre,
                'type': type_event,
                'date': date_event,
                'heure': heure_event,
                'lieu': lieu_event
            }
            
            champs_manquants = [nom for nom, valeur in champs_requis.items() if not valeur]
            
            if champs_manquants:
                error_msg = f'Champs requis manquants: {", ".join(champs_manquants)}'
                print(f"DEBUG - {error_msg}")
                flash(error_msg, 'error')
                return render_template_with_events('events.html', form_data=request.form.to_dict())
            
            try:
                duree = int(duree_str) if duree_str else 60
                capacite = int(capacite_str) if capacite_str else 0
            except ValueError:
                error_msg = 'Durée et capacité doivent être des nombres entiers'
                print(f"DEBUG - {error_msg}")
                flash(error_msg, 'error')
                return render_template_with_events('events.html', form_data=request.form.to_dict())
            
            types_valides = ['Conférence', 'Atelier', 'Séminaire', 'Formation', 'Réunion']
            if type_event not in types_valides:
                error_msg = f'Type d\'événement invalide. Types valides: {", ".join(types_valides)}'
                print(f"DEBUG - {error_msg}")
                flash(error_msg, 'error')
                return render_template_with_events('events.html', form_data=request.form.to_dict())
            
            try:
                time_obj = datetime.strptime(heure_event, '%H:%M').time()
                heure_formatted = time_obj.strftime('%H:%M:%S')
            except ValueError:
                error_msg = 'Format de l\'heure invalide. Utilisez le format HH:MM'
                print(f"DEBUG - {error_msg}")
                flash(error_msg, 'error')
                return render_template_with_events('events.html', form_data=request.form.to_dict())
            
            try:
                date_obj = datetime.strptime(date_event, '%Y-%m-%d').date()
                if date_obj < date.today():
                    error_msg = 'La date de l\'événement ne peut pas être dans le passé'
                    print(f"DEBUG - {error_msg}")
                    flash(error_msg, 'error')
                    return render_template_with_events('events.html', form_data=request.form.to_dict())
            except ValueError:
                error_msg = 'Format de date invalide'
                print(f"DEBUG - {error_msg}")
                flash(error_msg, 'error')
                return render_template_with_events('events.html', form_data=request.form.to_dict())
            
            data = {
                'titre': titre,
                'type': type_event,
                'date': date_event,
                'heure': heure_formatted,
                'duree': duree,
                'lieu': lieu_event,
                'description': description if description else None,
                'capacite': capacite,
                'participants': 0
            }
            
            print(f"DEBUG - Données préparées pour insertion: {data}")
            
            if evenement_manager.ajouter_evenement(data):
                print("DEBUG - Événement ajouté avec succès")
                flash('Événement ajouté avec succès!', 'success')
                return redirect(url_for('events'))
            else:
                error_msg = 'Erreur lors de l\'ajout de l\'événement en base de données'
                print(f"DEBUG - {error_msg}")
                flash(error_msg, 'error')
                return render_template_with_events('events.html', form_data=request.form.to_dict())
                
        except Exception as e:
            error_msg = f'Erreur inattendue: {str(e)}'
            print(f"DEBUG - {error_msg}")
            flash(error_msg, 'error')
            return render_template_with_events('events.html', form_data=request.form.to_dict())
    
    return render_template_with_events('events.html')

@app.route('/edit_event/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    """Modifier un événement existant"""
    if request.method == 'POST':
        try:
            titre = request.form.get('title', '').strip()
            type_event = request.form.get('type', '').strip()
            date_event = request.form.get('date', '').strip()
            heure_event = request.form.get('time', '').strip()
            lieu_event = request.form.get('location', '').strip()
            duree_str = request.form.get('duration', '60').strip()
            capacite_str = request.form.get('capacity', '0').strip()
            participants_str = request.form.get('participants', '0').strip()
            description = request.form.get('description', '').strip()
            
            if not all([titre, type_event, date_event, heure_event, lieu_event]):
                flash('Tous les champs requis doivent être remplis', 'error')
                return redirect(url_for('edit_event', event_id=event_id))
            
            duree = int(duree_str) if duree_str else 60
            capacite = int(capacite_str) if capacite_str else 0
            participants = int(participants_str) if participants_str else 0
            
            time_obj = datetime.strptime(heure_event, '%H:%M').time()
            heure_formatted = time_obj.strftime('%H:%M:%S')
            
            datetime.strptime(date_event, '%Y-%m-%d').date()
            
            data = {
                'titre': titre,
                'type': type_event,
                'date': date_event,
                'heure': heure_formatted,
                'duree': duree,
                'lieu': lieu_event,
                'description': description if description else None,
                'capacite': capacite,
                'participants': participants
            }
            
            if evenement_manager.modifier_evenement(event_id, data):
                flash('Événement modifié avec succès!', 'success')
                return redirect(url_for('events'))
            else:
                flash('Erreur lors de la modification de l\'événement', 'error')
                
        except ValueError:
            flash('Données invalides. Vérifiez les formats de date et heure.', 'error')
        except Exception as e:
            flash(f'Erreur inattendue: {str(e)}', 'error')
    
    evenement = evenement_manager.get_evenement_par_id(event_id)
    if not evenement:
        flash('Événement introuvable', 'error')
        return redirect(url_for('events'))
    
    if evenement.get('date') and hasattr(evenement['date'], 'strftime'):
        evenement['date'] = evenement['date'].strftime('%Y-%m-%d')
    if evenement.get('heure') and hasattr(evenement['heure'], 'strftime'):
        evenement['heure'] = evenement['heure'].strftime('%H:%M')
    if evenement.get('duree') and isinstance(evenement['duree'], timedelta):
        evenement['duree'] = int(evenement['duree'].total_seconds() // 60)
    
    return render_template('edit_event.html', evenement=evenement)

@app.route('/delete_event/<int:event_id>')
def delete_event(event_id):
    """Supprimer un événement"""
    if evenement_manager.supprimer_evenement(event_id):
        flash('Événement supprimé avec succès!', 'success')
    else:
        flash('Erreur lors de la suppression de l\'événement', 'error')
    return redirect(url_for('events'))

@app.route('/add_participant/<int:event_id>')
def add_participant(event_id):
    """Ajouter un participant à un événement"""
    if evenement_manager.incrementer_participants(event_id):
        flash('Participant ajouté avec succès!', 'success')
    else:
        flash('Erreur lors de l\'ajout du participant', 'error')
    return redirect(url_for('events'))

@app.route('/remove_participant/<int:event_id>')
def remove_participant(event_id):
    """Retirer un participant d'un événement"""
    if evenement_manager.decrementer_participants(event_id):
        flash('Participant retiré avec succès!', 'success')
    else:
        flash('Erreur lors du retrait du participant', 'error')
    return redirect(url_for('events'))

def render_template_with_events(template, **kwargs):
    """Helper pour rendre le template avec la liste des événements formatés"""
    evenements = evenement_manager.get_tous_evenements() or []
    
    for event in evenements:
        if event.get('date') and hasattr(event['date'], 'strftime'):
            event['date'] = event['date'].strftime('%d/%m/%Y')
        if event.get('heure') and hasattr(event['heure'], 'strftime'):
            event['heure'] = event['heure'].strftime('%H:%M')
        if event.get('duree') and isinstance(event['duree'], timedelta):
            event['duree'] = int(event['duree'].total_seconds() // 60)
    
    return render_template(template, evenements=evenements, **kwargs)

def init_database():
    """Initialiser la base de données avec la structure requise"""
    try:
        temp_config = DB_CONFIG.copy()
        temp_config.pop('database')
        
        connection = mysql.connector.connect(**temp_config)
        cursor = connection.cursor()
        
        cursor.execute("CREATE DATABASE IF NOT EXISTS gestion_evenements")
        cursor.execute("USE gestion_evenements")
        
        create_table_query = """
        CREATE TABLE IF NOT EXISTS evenements (
            id INT AUTO_INCREMENT PRIMARY KEY,
            titre VARCHAR(255) NOT NULL,
            type ENUM('Conférence', 'Atelier', 'Séminaire', 'Formation', 'Réunion') NOT NULL,
            date DATE NOT NULL,
            heure TIME NOT NULL,
            duree INT NOT NULL COMMENT 'Durée en minutes',
            lieu VARCHAR(255) NOT NULL,
            description TEXT,
            capacite INT NOT NULL DEFAULT 0,
            participants INT NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """
        cursor.execute(create_table_query)
        
        cursor.execute("SELECT COUNT(*) FROM evenements")
        cursor.close()
        connection.close()
        print("Base de données initialisée avec succès")
        
    except Error as e:
        print(f"Erreur lors de l'initialisation de la base de données: {e}")

if __name__ == '__main__':
    print("Initialisation de l'application...")
    init_database()
    
    try:
        print("Démarrage du serveur Flask...")
        app.run(debug=True, host='0.0.0.0', port=5000)
    finally:
        print("Fermeture de l'application...")
        db_manager.disconnect()