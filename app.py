from flask import Flask, render_template, request, redirect, url_for
import json
import os

app = Flask(__name__)

# Fichier pour stocker les événements
DATA_FILE = 'evenements.json'

def charger_evenements():
    """Charge les événements depuis le fichier JSON"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []

def sauvegarder_evenements(evenements):
    """Sauvegarde les événements dans le fichier JSON"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(evenements, f, ensure_ascii=False, indent=2)
    except IOError:
        print("Erreur lors de la sauvegarde des événements")

# Charger les événements au démarrage
evenements = charger_evenements()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/events', methods=['GET', 'POST'])
def events():
    global evenements
    
    if request.method == 'POST':
        titre = request.form.get('title')
        type_ = request.form.get('type')
        date = request.form.get('date')
        heure = request.form.get('time')
        duree = request.form.get('duration')
        lieu = request.form.get('location')
        description = request.form.get('description')
        capacite = request.form.get('capacity')
        
        # Validation basique
        if titre and date and lieu:
            nouvel_evenement = {
                'id': len(evenements) + 1,  # ID simple
                'titre': titre,
                'type': type_,
                'date': date,
                'heure': heure,
                'duree': duree,
                'lieu': lieu,
                'description': description,
                'capacite': int(capacite) if capacite else 0,
                'participants': 0
            }
            
            evenements.append(nouvel_evenement)
            sauvegarder_evenements(evenements)
        
        return redirect(url_for('events'))
    
    return render_template('events.html', evenements=evenements)

@app.route('/delete_event/<int:event_id>')
def delete_event(event_id):
    """Supprimer un événement"""
    global evenements
    evenements = [e for e in evenements if e.get('id') != event_id]
    sauvegarder_evenements(evenements)
    return redirect(url_for('events'))

if __name__ == '__main__':
    app.run(debug=True)