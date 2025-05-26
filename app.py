from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

DATA_FILE = 'evenements.json'
CONFIG_FILE = 'config.json'

def charger_evenements():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []

def sauvegarder_evenements(evenements):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(evenements, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"Erreur sauvegarde: {e}")

def calculer_notifications_intelligentes():
    """Calcule les notifications selon différents niveaux d'urgence"""
    evenements = charger_evenements()
    now = datetime.now()
    
    notifications = {
        'urgent': [],
        'bientot': [],
        'aujourd_hui': [],
        'demain': [],
        'cette_semaine': []
    }
    
    for event in evenements:
        try:
            event_date = datetime.strptime(event['date'], '%Y-%m-%d')
            
            if event.get('heure'):
                event_time = datetime.strptime(f"{event['date']} {event['heure']}", '%Y-%m-%d %H:%M')
            else:
                event_time = event_date.replace(hour=9, minute=0)
            
            time_diff = event_time - now
            
            if time_diff.total_seconds() > 0: 
                if time_diff.total_seconds() <= 1800: 
                    notifications['urgent'].append({**event, 'time_diff': time_diff})
                elif time_diff.total_seconds() <= 7200:  
                    notifications['bientot'].append({**event, 'time_diff': time_diff})
                elif event_date.date() == now.date():  
                    notifications['aujourd_hui'].append({**event, 'time_diff': time_diff})
                elif event_date.date() == (now + timedelta(days=1)).date(): 
                    notifications['demain'].append({**event, 'time_diff': time_diff})
                elif time_diff.days <= 7:  
                    notifications['cette_semaine'].append({**event, 'time_diff': time_diff})
        
        except ValueError as e:
            print(f"Erreur format date pour {event.get('titre', 'Événement')}: {e}")
            continue
    
    return notifications

def formater_temps_restant(time_diff):
    """Formate le temps restant de manière lisible"""
    total_seconds = int(time_diff.total_seconds())
    
    if total_seconds < 3600:
        minutes = total_seconds // 60
        return f"dans {minutes} min"
    elif total_seconds < 86400:
        heures = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"dans {heures}h{minutes:02d}"
    else:
        jours = total_seconds // 86400
        return f"dans {jours} jour{'s' if jours > 1 else ''}"

@app.context_processor
def inject_datetime_utils():
    return dict(
        datetime=datetime,
        timedelta=timedelta,
        formater_temps_restant=formater_temps_restant
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/events', methods=['GET', 'POST'])
def events():
    if request.method == 'POST':
        titre = request.form.get('title')
        type_ = request.form.get('type', 'Autre')
        date = request.form.get('date')
        heure = request.form.get('time')
        duree = request.form.get('duration')
        lieu = request.form.get('location')
        description = request.form.get('description')
        capacite = request.form.get('capacity')
        
        if titre and date and lieu:
            evenements = charger_evenements()
            
            nouvel_evenement = {
                'id': max([e.get('id', 0) for e in evenements], default=0) + 1,
                'titre': titre,
                'type': type_,
                'date': date,
                'heure': heure if heure else None,
                'duree': int(duree) if duree and duree.isdigit() else None,
                'lieu': lieu,
                'description': description if description else None,
                'capacite': int(capacite) if capacite and capacite.isdigit() else None,
                'participants': 0,
                'created_at': datetime.now().isoformat()
            }
            
            evenements.append(nouvel_evenement)
            sauvegarder_evenements(evenements)
        
        return redirect(url_for('events'))
    
    evenements = charger_evenements()
    notifications = calculer_notifications_intelligentes()
    now = datetime.now()
    
    return render_template('events.html', 
                         evenements=evenements, 
                         notifications=notifications,
                         now=now,
                         timedelta=timedelta)

@app.route('/dashboard')
def dashboard():
    """Tableau de bord professionnel avec notifications et statistiques - VERSION CORRIGÉE"""
    evenements = charger_evenements()
    notifications = calculer_notifications_intelligentes()
    now = datetime.now()
    
    stats = {
        'total_evenements': len(evenements),
        'evenements_aujourd_hui': len([e for e in evenements if e['date'] == now.strftime('%Y-%m-%d')]),
        'evenements_cette_semaine': 0,
        'types_evenements': {}
    }
    
    for event in evenements:
        try:
            event_date = datetime.strptime(event['date'], '%Y-%m-%d')
            if event_date.date() >= now.date() and event_date.date() <= (now + timedelta(days=7)).date():
                stats['evenements_cette_semaine'] += 1
        except ValueError:
            continue
    
    for event in evenements:
        type_event = event.get('type', 'Autre')
        stats['types_evenements'][type_event] = stats['types_evenements'].get(type_event, 0) + 1
    
    evenements_a_venir = []
    for event in evenements:
        try:
            event_date = datetime.strptime(event['date'], '%Y-%m-%d')
            if event_date.date() >= now.date() and event_date.date() <= (now + timedelta(days=7)).date():
                evenements_a_venir.append(event)
        except ValueError:
            continue
    
    evenements_a_venir.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d'))
    
    return render_template('dashboard.html', 
                         notifications=notifications,
                         stats=stats,
                         evenements_a_venir=evenements_a_venir[:5],
                         now=now)

@app.route('/api/notifications')
def api_notifications():
    """API pour récupérer les notifications en temps réel"""
    notifications = calculer_notifications_intelligentes()
    
    result = {}
    for key, events in notifications.items():
        result[key] = []
        for event in events:
            result[key].append({
                'id': event['id'],
                'titre': event['titre'],
                'type': event['type'],
                'date': event['date'],
                'heure': event.get('heure'),
                'lieu': event['lieu'],
                'temps_restant': formater_temps_restant(event['time_diff'])
            })
    
    return jsonify(result)

@app.route('/delete_event/<int:event_id>')
def delete_event(event_id):
    evenements = charger_evenements()
    evenements = [e for e in evenements if e.get('id') != event_id]
    sauvegarder_evenements(evenements)
    return redirect(url_for('events'))

@app.route('/clear_all_events')
def clear_all_events():
    """Route pour supprimer tous les événements (utile pour les tests)"""
    sauvegarder_evenements([])
    return f"""
    <div style="padding: 20px; font-family: Arial, sans-serif; text-align: center;">
        <h2>Tous les événements ont été supprimés</h2>
        <p><a href="{url_for('events')}">Retour aux événements</a></p>
        <p><a href="{url_for('dashboard')}">Voir le dashboard</a></p>
    </div>
    """

if __name__ == '__main__':    
    app.run(debug=True)