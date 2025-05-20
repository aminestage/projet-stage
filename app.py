from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Données en mémoire (temporaire)
evenements = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/events', methods=['GET', 'POST'])
def events():
    if request.method == 'POST':
        titre = request.form.get('title')
        type_ = request.form.get('type')
        date = request.form.get('date')
        heure = request.form.get('time')
        duree = request.form.get('duration')
        lieu = request.form.get('location')
        description = request.form.get('description')
        capacite = request.form.get('capacity')

        evenements.append({
            'titre': titre,
            'type': type_,
            'date': date,
            'heure': heure,
            'duree': duree,
            'lieu': lieu,
            'description': description,
            'capacite': capacite,
            'participants': 0
        })

        return redirect(url_for('events'))

    return render_template('events.html', evenements=evenements)

if __name__ == '__main__':
    app.run(debug=True)
