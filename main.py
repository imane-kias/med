from flask import Flask, render_template, request, redirect, url_for, flash,session
from app import get_db_connection
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'XAB123'

# Route pour la page d'inscription
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Vérification des mots de passe
        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas', 'danger')
            return redirect(url_for('signup'))

        # Ici tu pourrais ajouter la logique pour enregistrer les informations dans une base de données
        flash('Inscription réussie, vous pouvez maintenant vous connecter', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

# Route pour la page de connexion
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Logique de validation simple (peut être remplacée par une base de données)
        if email == "test@example.com" and password == "password":
            flash('Connexion réussie', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Email ou mot de passe incorrect', 'danger')

    return render_template('login.html')

# Route pour le tableau de bord (dashboard)
@app.route('/dashboard')
def dashboard():
    return "Bienvenue dans votre tableau de bord !"

# Route pour la mise à jour des informations du patient
@app.route('/patient/update/<int:user_id>', methods=['GET', 'POST'])
def update_patient(user_id):
    if 'user_role' in session and session['user_role'] == 'patient' and session['user_id'] == user_id:
        if request.method == 'POST':
            adresse = request.form['adresse']
            numero_telephone = request.form['numero_telephone']

            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("UPDATE patients SET adresse=%s, numero_telephone=%s WHERE utilisateur_id=%s", 
                           (adresse, numero_telephone, user_id))
            connection.commit()
            cursor.close()
            connection.close()

            flash('Coordonnées mises à jour avec succès', 'success')
            return redirect(url_for('dashboard'))

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM patients WHERE utilisateur_id = %s", (user_id,))
        patient = cursor.fetchone()
        cursor.close()
        connection.close()

        return render_template('update_patient.html', patient=patient)
    else:
        flash('Accès refusé', 'danger')
        return redirect(url_for('login'))

# Route pour la consultation et modification de dossier médical par le médecin
@app.route('/dossier/<int:patient_id>', methods=['GET', 'POST'])
def dossier_medical(patient_id):
    if 'user_role' in session and session['user_role'] == 'medecin':
        if request.method == 'POST':
            description = request.form['description']
            prescription = request.form['prescription']
            diagnostique = request.form['diagnostique']
            date_consultation = datetime.now().strftime('%Y-%m-%d')

            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("INSERT INTO consultations (patient_id, medecin_id, date_consultation, notes, prescription, diagnostique) VALUES (%s, %s, %s, %s, %s, %s)",
                           (patient_id, session['user_id'], date_consultation, description, prescription, diagnostique))
            connection.commit()

            dossier_id = cursor.lastrowid
            cursor.execute("INSERT INTO modifications_dossiers (dossier_id, utilisateur_id, details_modification) VALUES (%s, %s, %s)", 
                           (dossier_id, session['user_id'], "Consultation ajoutée"))
            connection.commit()
            cursor.close()
            connection.close()

            flash('Consultation ajoutée et modification archivée', 'success')
            return redirect(url_for('dossier_medical', patient_id=patient_id))

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM consultations WHERE patient_id = %s", (patient_id,))
        consultations = cursor.fetchall()
        cursor.close()
        connection.close()

        return render_template('dossier_medical.html', consultations=consultations)
    else:
        flash('Accès refusé', 'danger')
        return redirect(url_for('login'))

# Route pour annuler une modification du dossier médical
@app.route('/annuler_modification/<int:modification_id>', methods=['POST'])
def annuler_modification(modification_id):
    if 'user_role' in session and session['user_role'] == 'medecin':
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM modifications_dossiers WHERE id = %s", (modification_id,))
        connection.commit()
        cursor.close()
        connection.close()

        flash('Modification annulée avec succès', 'success')
    else:
        flash('Accès refusé', 'danger')

    return redirect(url_for('dashboard'))

# Route pour faire une demande de rendez-vous par un patient
@app.route('/rendez_vous', methods=['GET', 'POST'])
def rendez_vous():
    if 'user_role' in session and session['user_role'] == 'patient':
        if request.method == 'POST':
            medecin_id = request.form['medecin_id']
            date_rdv = request.form['date_rdv']
            heure_rdv = request.form['heure_rdv']

            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("INSERT INTO rendez_vous (patient_id, medecin_id, date_rdv, heure_rdv) VALUES (%s, %s, %s, %s)",
                           (session['user_id'], medecin_id, date_rdv, heure_rdv))
            connection.commit()
            cursor.close()
            connection.close()

            flash('Demande de rendez-vous envoyée', 'success')
            return redirect(url_for('dashboard'))

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM utilisateurs WHERE role='medecin'")
        medecins = cursor.fetchall()
        cursor.close()
        connection.close()

        return render_template('rendez_vous.html', medecins=medecins)
    else:
        flash('Accès refusé', 'danger')
        return redirect(url_for('login'))

# Route pour la gestion des rendez-vous par le médecin
@app.route('/rendez_vous/gestion', methods=['GET', 'POST'])
def gestion_rendez_vous():
    if 'user_role' in session and session['user_role'] == 'medecin':
        if request.method == 'POST':
            rdv_id = request.form['rdv_id']
            action = request.form['action']  # 'confirmé' ou 'refusé'

            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("UPDATE rendez_vous SET statut=%s WHERE id=%s AND medecin_id=%s", 
                           (action, rdv_id, session['user_id']))
            connection.commit()
            cursor.close()
            connection.close()

            flash('Rendez-vous mis à jour', 'success')
            return redirect(url_for('gestion_rendez_vous'))

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM rendez_vous WHERE medecin_id = %s", (session['user_id'],))
        rendez_vous = cursor.fetchall()
        cursor.close()
        connection.close()

        return render_template('gestion_rendez_vous.html', rendez_vous=rendez_vous)
    else:
        flash('Accès refusé', 'danger')
        return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)