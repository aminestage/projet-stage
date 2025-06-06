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
        self.connect()

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host='localhost',
                database='gestion_evenements',
                user='root',
                password=''
            )
            if self.connection.is_connected():
                print("Connexion à MySQL réussie")
        except Error as e:
            print(f"Erreur lors de la connexion : {e}")
            self.connection = None
    
    def disconnect(self):
        """Fermer la connexion à la base de données"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("Connexion MySQL fermée")
    
    def execute_query(self, query, params=None, fetch=False, commit=False):
        if self.connection is None or not self.connection.is_connected():
            self.connect()

        cursor = self.connection.cursor(dictionary=True)

        try:
            cursor.execute(query, params or [])
            if fetch:
                result = cursor.fetchall()
                return result
            if commit:
                self.connection.commit()
            return True
        except Error as e:
            print(f"Erreur lors de l'exécution de la requête : {e}")
            return False
        finally:
            cursor.close()

db_manager = DatabaseManager()

class EvenementManager:
    def __init__(self):
        db_manager.connect()
    
    def get_tous_evenements(self):
        """Récupérer tous les événements"""
        query = """
        SELECT id, title, type, date, time, duration, location, description, 
               capacite, participants, created_at 
        FROM evenements 
        ORDER BY date, time
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
        INSERT INTO evenements (title, type, date, time, duration, location, description, capacite, participants)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['title'],
            data['type'],
            data['date'],
            data['time'],
            data['duration'],
            data['location'],
            data.get('description', ''),
            data['capacite'],
            data.get('participants', 0)
        )
        
        print(f"DEBUG - Paramètres SQL: {params}")
        result = db_manager.execute_query(query, params, commit=True)  # Added commit=True
        print(f"DEBUG - Résultat insertion: {result}")
        return result
    
    def modifier_evenement(self, evenement_id, data):
        """Modifier un événement existant"""
        query = """
        UPDATE evenements 
        SET title=%s, type=%s, date=%s, time=%s, duration=%s, location=%s, 
            description=%s, capacite=%s, participants=%s
        WHERE id=%s
        """
        params = (
            data['title'],
            data['type'],
            data['date'],
            data['time'],
            data['duration'],
            data['location'],
            data.get('description', ''),
            data['capacite'],
            data.get('participants', 0),
            evenement_id
        )
        return db_manager.execute_query(query, params, commit=True)
    
    def supprimer_evenement(self, evenement_id):
        """Supprimer un événement"""
        query = "DELETE FROM evenements WHERE id = %s"
        return db_manager.execute_query(query, (evenement_id,), commit=True)
    
    def incrementer_participants(self, evenement_id):
        """Incrémenter le nombre de participants"""
        query = "UPDATE evenements SET participants = participants + 1 WHERE id = %s"
        return db_manager.execute_query(query, (evenement_id,), commit=True)
    
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
        return db_manager.execute_query(query, (evenement_id,), commit=True)
    
    def get_evenements_dashboard(self):
        evenements = self.get_tous_evenements()
        if not evenements:
            return []
            
        now = datetime.now()

        for event in evenements:
            event_date = event.get('date')
            event_heure = event.get('time')
            
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

def render_template_with_events(template, **kwargs):
    """Helper pour rendre le template avec la liste des événements formatés"""
    evenements = evenement_manager.get_tous_evenements() or []
    
    print(f"DEBUG - render_template_with_events: {len(evenements)} événements récupérés")
    
    for event in evenements:
        print(f"DEBUG - Événement brut: {event}")
        
        if event.get('date'):
            if hasattr(event['date'], 'strftime'):
                event['date_formatted'] = event['date'].strftime('%d/%m/%Y')
            else:
                event['date_formatted'] = str(event['date'])
        else:
            event['date_formatted'] = 'Non définie'
            
        if event.get('time'):
            if isinstance(event['time'], timedelta):
                total_seconds = int(event['time'].total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                event['time_formatted'] = f"{hours:02d}:{minutes:02d}"
            elif hasattr(event['time'], 'strftime'):
                event['time_formatted'] = event['time'].strftime('%H:%M')
            else:
                event['time_formatted'] = str(event['time'])
        else:
            event['time_formatted'] = 'Non définie'
            
        if event.get('duration'):
            if isinstance(event['duration'], timedelta):
                duration_minutes = int(event['duration'].total_seconds() // 60)
                event['duration_formatted'] = f"{duration_minutes} min"
            elif isinstance(event['duration'], int):
                event['duration_formatted'] = f"{event['duration']} min"
            else:
                event['duration_formatted'] = str(event['duration'])
        else:
            event['duration_formatted'] = 'Non définie'
            
        if not event.get('location'):
            event['location'] = 'Non défini'
            
        if event.get('capacite') == 0:
            event['capacite_formatted'] = 'Illimitée'
        else:
            event['capacite_formatted'] = str(event['capacite'])
            
        print(f"DEBUG - Événement formaté: date={event.get('date_formatted')}, time={event.get('time_formatted')}, duration={event.get('duration_formatted')}, location={event.get('location')}")
    
    return render_template(template, evenements=evenements, **kwargs)

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
        if event['time']:
            event['time'] = event['time'].strftime('%H:%M') if hasattr(event['time'], 'strftime') else str(event['time'])
        
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
            title = request.form.get('title', '').strip()
            event_type = request.form.get('type', '').strip()  
            event_date = request.form.get('date', '').strip()  
            event_time = request.form.get('time', '').strip()  
            location = request.form.get('location', '').strip()
            duration = request.form.get('duration', '60').strip()
            capacite = request.form.get('capacite', '0').strip()
            description = request.form.get('description', '').strip()
                        
            champs_requis = {
                'title': title,
                'type': event_type,
                'date': event_date,
                'time': event_time,
                'location': location
            }
            
            champs_manquants = [nom for nom, valeur in champs_requis.items() if not valeur]
            
            if champs_manquants:
                error_msg = f'Champs requis manquants: {", ".join(champs_manquants)}'
                print(f"DEBUG - {error_msg}")
                flash(error_msg, 'error')
                return render_template_with_events('events.html', form_data=request.form.to_dict())
            
            try:
                duration = int(duration) if duration else 60
                capacite = int(capacite) if capacite else 0
            except ValueError:
                error_msg = 'Durée et capacité doivent être des nombres entiers'
                print(f"DEBUG - {error_msg}")
                flash(error_msg, 'error')
                return render_template_with_events('events.html', form_data=request.form.to_dict())
            
            types_valides = ['Réunion', 'Formation', 'Conférence', 'Team Building', 'Présentation', 'Autre']
            if event_type not in types_valides:
                error_msg = f'Type d\'événement invalide. Types valides: {", ".join(types_valides)}'
                print(f"DEBUG - {error_msg}")
                flash(error_msg, 'error')
                return render_template_with_events('events.html', form_data=request.form.to_dict())
            
            try:
                time_obj = datetime.strptime(event_time, '%H:%M').time()
                heure_formatted = time_obj.strftime('%H:%M:%S')
            except ValueError:
                error_msg = 'Format de l\'heure invalide. Utilisez le format HH:MM'
                print(f"DEBUG - {error_msg}")
                flash(error_msg, 'error')
                return render_template_with_events('events.html', form_data=request.form.to_dict())
            
            try:
                date_obj = datetime.strptime(event_date, '%Y-%m-%d').date()
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
                'title': title,
                'type': event_type,
                'date': event_date,
                'time': heure_formatted,
                'duration': duration,
                'location': location,
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
    TYPES_EVENEMENT = ['Réunion', 'Formation', 'Conférence', 'Team Building', 'Présentation', 'Autre']

    if request.method == 'POST':
        title = request.form['title']
        event_type = request.form['type']  
        event_date = request.form['date']  
        event_time = request.form['time']
        duration = request.form['duration']
        location = request.form['location']
        description = request.form['description']
        capacite = request.form['capacite']

        if not title or not event_type or not event_date:
            flash('Veuillez remplir tous les champs obligatoires.', 'error')
            return redirect(request.url)

        if event_type not in TYPES_EVENEMENT:
            flash("Type d'événement invalide.", 'error')
            return redirect(request.url)

        query = """
            UPDATE evenements
            SET title=%s, type=%s, date=%s, time=%s, duration=%s, location=%s, description=%s, capacite=%s, updated_at=NOW()
            WHERE id=%s
        """
        values = (title, event_type, event_date, event_time, duration, location, description, capacite, event_id)

        success = db_manager.execute_query(query, values, commit=True)
        if success:
            flash('Événement mis à jour avec succès.', 'success')
            return redirect(url_for('events'))
        else:
            flash('Erreur lors de la mise à jour.', 'error')

    evenement = db_manager.execute_query("SELECT * FROM evenements WHERE id = %s", (event_id,), fetch=True)
    if evenement:
        evenement = evenement[0]
    else:
        flash("Événement introuvable.", "error")
        return redirect(url_for('events'))

    return render_template('edit_event.html', evenement=evenement, types_evenement=TYPES_EVENEMENT)


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
            title VARCHAR(255) NOT NULL,
            type ENUM('Réunion', 'Formation', 'Conférence', 'Team Building', 'Présentation', 'Autre') NOT NULL,
            date DATE NOT NULL,
            time TIME NOT NULL,
            duration INT NOT NULL COMMENT 'Durée en minutes',
            location VARCHAR(255) NOT NULL,
            description TEXT,
            capacite INT NOT NULL DEFAULT 0,
            participants INT NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """
        cursor.execute(create_table_query)
        connection.commit()
        
        cursor.execute("SELECT COUNT(*) FROM evenements")
        result = cursor.fetchone()
        print(f"Table evenements has {result[0]} records")
        
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