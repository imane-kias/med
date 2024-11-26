from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import logging

# Configuration du logging
logging.basicConfig(level=logging.DEBUG)

# Initialisation de l'application Flask
app = Flask(__name__)
app.secret_key = 'XAB123'

# Import du Blueprint pour le chatbot
from routes.chatbot_api import chatbot_bp

app.register_blueprint(chatbot_bp, url_prefix='/api')
  # Préfixe pour les routes API

@app.route('/analyze-symptoms')
def analyze_symptoms():
    return render_template('analyze_symptoms.html')


# Connexion à la base de données
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",  # Modifie si nécessaire (ex : XAMPP avec un autre port)
            user="root",
            password="",
            database="Med"
        )
        logging.debug("Connexion à la base de données réussie.")
        return connection
    except mysql.connector.Error as err:
        logging.error(f"Erreur de connexion à la base de données : {err}")
        flash("Connexion à la base de données échouée.", 'danger')
        return None

# Route for the homepage
@app.route('/')
def index():
    return render_template('index.html')

# Route for signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        nom = request.form['name']
        email = request.form['email']
        mot_de_passe = request.form['password']
        confirmation = request.form['confirm_password']
        role = request.form['role']
        
        # Only get num_licence and num_assurance if they are applicable to the role
        num_licence = request.form['num_licence'] if role == 'medecin' else None
        num_assurance = request.form['num_assurance'] if role == 'patient' else None
        role_administratif = request.form['role_administratif'] if role == 'administrateur' else None
        logging.debug("Form data received: Name: %s, Email: %s, Role: %s, Licence: %s, Assurance: %s",
                      nom, email, role, num_licence, num_assurance)

        # Check if passwords match
        if mot_de_passe != confirmation:
            flash('Les mots de passe ne correspondent pas', 'danger')
            return redirect(url_for('signup'))

        # Generate and log the hashed password
        mot_de_passe_hashed = generate_password_hash(mot_de_passe)
        logging.debug("Generated hashed password: %s", mot_de_passe_hashed)

        connection = get_db_connection()
        if connection is None:
            flash("Database connection failed.", 'danger')
            return redirect(url_for('signup'))

        try:
            cursor = connection.cursor()
            # Insert the user into the utilisateurs table
            cursor.execute(
                """
                INSERT INTO utilisateurs (nom, email, mot_de_passe, role, numero_licence, numero_assurance) 
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (nom, email, mot_de_passe_hashed, role, num_licence, num_assurance)
            )
            connection.commit()
            utilisateur_id = cursor.lastrowid  # Récupère l'ID de l'utilisateur ajouté

            # Si le rôle est "administrateur", insère également un enregistrement dans `administration`
            if role == 'administrateur' and role_administratif:
                cursor.execute(
                    """
                    INSERT INTO administration (utilisateur_id, role_administratif) 
                    VALUES (%s, %s)
                    """,
                    (utilisateur_id, role_administratif)
                )
                connection.commit()

            flash('Inscription réussie, vous pouvez maintenant vous connecter', 'success')
        except mysql.connector.Error as err:
            # Log the error and show it in a flash message
            logging.error("Database error: %s", err)
            flash("Un problème est survenu lors de l'inscription : " + str(err), 'danger')
        finally:
            cursor.close()
            connection.close()

        return redirect(url_for('login'))
    
    return render_template('signup.html')


# Route for login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        mot_de_passe = request.form['password']

        connection = get_db_connection()
        if connection is None:
            return redirect(url_for('login'))

        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM utilisateurs WHERE email = %s", (email,))
            utilisateur = cursor.fetchone()

            # Log fetched user data
            if utilisateur:
                logging.debug("Fetched user: %s", utilisateur)
                logging.debug("Stored hashed password: %s", utilisateur['mot_de_passe'])

                # Check password hash
                if check_password_hash(utilisateur['mot_de_passe'], mot_de_passe):
                    session['user_id'] = utilisateur['id']
                    session['user_role'] = utilisateur['role']
                    flash('Connexion réussie', 'success')
                    
                    # Redirection en fonction du rôle de l'utilisateur
                    if session['user_role'] == 'patient':
                        return redirect(url_for('dashboard_patient'))
                    elif session['user_role'] == 'medecin':
                        return redirect(url_for('dashboard_medecin'))
                    elif session['user_role'] == 'administrateur':
                        return redirect(url_for('dashboard_administration'))
                    else:
                        flash("Rôle utilisateur inconnu.", 'danger')
                        return redirect(url_for('login'))
                else:
                    logging.debug("Password check failed.")
                    flash('Identifiants incorrects', 'danger')
            else:
                logging.debug("No user found with provided email.")
                flash('Identifiants incorrects', 'danger')
        except mysql.connector.Error as err:
            logging.error("Database error: %s", err)
            flash("Un problème est survenu lors de la connexion", 'danger')
        finally:
            cursor.close()
            connection.close()

    return render_template('login.html')

# Run the app
if __name__ == '__main__':
    app.run(debug=True)


# Route for logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_role', None)
    flash('Vous êtes déconnecté', 'success')
    return redirect(url_for('index'))

# Route pour afficher le dossier médical d'un patient par numéro d'assurance
@app.route('/dossier/<numero_assurance>', methods=['GET', 'POST'])
def dossier_medical(numero_assurance):
    if 'user_role' in session and session['user_role'] == 'medecin':
        try:
            # Connexion à la base de données
            connection = get_db_connection()
            if connection is None or not connection.is_connected():
                flash("Impossible de se connecter à la base de données.", 'danger')
                return redirect(url_for('dashboard_medecin'))
            
            cursor = connection.cursor(dictionary=True)

            # Récupérer le dossier médical par numéro d'assurance
            cursor.execute("""
                SELECT dm.*, p.adresse, p.numero_telephone, u.nom
                FROM dossiers_medicaux dm
                JOIN patients p ON dm.patient_id = p.utilisateur_id
                JOIN utilisateurs u ON dm.patient_id = u.id
                WHERE dm.numero_assurance = %s
            """, (numero_assurance,))
            dossier = cursor.fetchone()

            # Log pour vérifier l'ID du dossier récupéré
            app.logger.info(f"ID du dossier récupéré pour le numéro d'assurance {numero_assurance} : {dossier['id']}")

            # Vérifier si le dossier existe
            if not dossier:
                flash("Aucun dossier trouvé pour ce numéro d'assurance.", 'danger')
                return redirect(url_for('dashboard_medecin'))

            app.logger.info(f"ID du dossier actuel : {dossier['id']}")

            
           

            # Afficher la page dossier médical avec les informations
            return render_template('dossier_medical.html', dossier=dossier)
        except mysql.connector.Error as err:
            flash(f"Erreur de base de données : {err}", 'danger')
            app.logger.error(f"Erreur de base de données : {err}")
            return redirect(url_for('dashboard_medecin'))
        
        finally:
            # Fermer le curseur et la connexion dans le bloc finally pour éviter les erreurs
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    else:
        flash('Accès refusé', 'danger')
        return redirect(url_for('login'))

@app.route('/consultations/<int:dossier_id>', methods=['GET'])
def consultations(dossier_id):
    # Connexion à la base de données pour récupérer les consultations du dossier
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    # Récupérer les consultations pour le dossier spécifié
    cursor.execute("SELECT * FROM visites_medicaux WHERE dossier_id = %s", (dossier_id,))
    consultations = cursor.fetchall()
    
     # Load modifications for each consultation
    for consultation in consultations:
        cursor.execute("SELECT * FROM modifications_dossiers WHERE dossier_id = %s", (consultation['dossier_id'],))
        consultation['modifications'] = cursor.fetchall()
    

    # Fermer le curseur et la connexion
    cursor.close()
    connection.close()
    
    return render_template('consultations.html', dossier_id=dossier_id, consultations=consultations)



@app.route('/ajouter_consultation/<int:dossier_id>', methods=['GET', 'POST'])
def ajouter_consultation(dossier_id):
    if 'user_role' in session and session['user_role'] == 'medecin':
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

    # Récupérer numero_assurance pour l'affichage dans le template et la redirection
        cursor.execute("SELECT numero_assurance FROM dossiers_medicaux WHERE id = %s", (dossier_id,))
        result = cursor.fetchone()
        
        if result:
            numero_assurance = result['numero_assurance']
        else:
            # Gérer l'erreur si numero_assurance n'est pas trouvé
            flash("Numéro d'assurance non trouvé pour ce dossier.", 'danger')
            cursor.close()
            connection.close()
            return redirect(url_for('dashboard_medecin'))  # Redirige vers le tableau de bord    
    
        
        
        if request.method == 'POST':
            etablissement = request.form['etablissement_visite']
            date_visite = request.form['date_visite']
            diagnostique = request.form['diagnostique']
            traitement = request.form['traitement']
            resume_visite = request.form['resume_visite']
            notes = request.form['notes']

            

            # Insérer la consultation dans la table visites_medicaux
            cursor.execute("""
                INSERT INTO visites_medicaux 
                (dossier_id, etablissement_visite, medecin_id, date_visite, diagnostique, traitement, resume_visite, notes) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (dossier_id, etablissement, session['user_id'], date_visite, diagnostique, traitement, resume_visite, notes))
            connection.commit()

            # Archiver la modification dans modifications_dossiers
            details_modification = f"Consultation ajoutée par le médecin {session['user_id']} le {date_visite}"
            cursor.execute("""
                INSERT INTO modifications_dossiers 
                (dossier_id, utilisateur_id, details_modification) 
                VALUES (%s, %s, %s)
            """, (dossier_id, session['user_id'], details_modification))
            connection.commit()
                
            flash('Consultation ajoutée avec succès.', 'success')
            cursor.close()
            connection.close()
            return redirect(url_for('dossier_medical', numero_assurance=numero_assurance))
        cursor.close()
        connection.close()   
           

        return render_template('ajouter_consultation.html', dossier_id=dossier_id,numero_assurance=numero_assurance)
    else:
        flash('Accès refusé', 'danger')
        return redirect(url_for('login'))


@app.route('/modifier_consultation/<int:consultation_id>', methods=['GET', 'POST'])
def modifier_consultation(consultation_id):
    if 'user_role' in session and session['user_role'] == 'medecin':
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Récupérer la consultation originale
        cursor.execute("SELECT * FROM visites_medicaux WHERE id = %s", (consultation_id,))
        original_consultation = cursor.fetchone()

        if not original_consultation:
            flash("Consultation introuvable.", 'danger')
            return redirect(url_for('dashboard_medecin'))

        if request.method == 'POST':
            etablissement = request.form['etablissement_visite']
            date_visite = request.form['date_visite']
            diagnostique = request.form['diagnostique']
            traitement = request.form['traitement']
            resume_visite = request.form['resume_visite']
            notes = request.form['notes']

            # Ajouter la version modifiée de la consultation
            cursor.execute("""
                INSERT INTO visites_medicaux 
                (dossier_id, etablissement_visite, medecin_id, date_visite, diagnostique, traitement, resume_visite, notes) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (original_consultation['dossier_id'], etablissement, session['user_id'], date_visite, diagnostique, traitement, resume_visite, notes))
            connection.commit()

            # Archiver la modification dans modifications_dossiers
            details_modification = f"Consultation modifiée par le médecin {session['user_id']} le {date_visite}"
            cursor.execute("""
                INSERT INTO modifications_dossiers 
                (dossier_id, utilisateur_id, details_modification) 
                VALUES (%s, %s, %s)
            """, (original_consultation['dossier_id'], session['user_id'], details_modification))
            connection.commit()
            
            # Récupération de numero_assurance à partir de dossier_id
            cursor.execute("SELECT numero_assurance FROM dossiers_medicaux WHERE id = %s", (original_consultation['dossier_id'],))
            result = cursor.fetchone()
            if result:
                numero_assurance = result['numero_assurance']
            else:
                # Gérer l'erreur si numero_assurance n'est pas trouvé
                flash("Numéro d'assurance non trouvé", 'danger')
                return redirect(url_for('dashboard_medecin'))

            cursor.close()
            connection.close()

            flash('Consultation modifiée et sauvegardée.', 'success')
            return redirect(url_for('dossier_medical', numero_assurance=numero_assurance))
        cursor.close()
        connection.close()
        return render_template('modifier_consultation.html', consultation=original_consultation)
    else:
        flash('Accès refusé', 'danger')
        return redirect(url_for('login'))

@app.route('/annuler_modification/<int:modification_id>/<int:dossier_id>', methods=['POST'])
def annuler_modification(modification_id, dossier_id):
    if 'user_role' in session and session['user_role'] == 'medecin':
        connection = get_db_connection()
        cursor = connection.cursor()

        # Supprimer la dernière modification
        cursor.execute("DELETE FROM modifications_dossiers WHERE id = %s", (modification_id,))
        connection.commit()

       
         
        # Récupérer le numero_assurance correspondant au dossier_id pour la redirection
        cursor.execute("SELECT numero_assurance FROM dossiers_medicaux WHERE id = %s", (dossier_id,))
        result = cursor.fetchone()
        if result:
            numero_assurance = result[0]
        else:
            flash("Numéro d'assurance non trouvé.", 'danger')
            cursor.close()
            connection.close()
            return redirect(url_for('dashboard_medecin'))

        cursor.close()
        connection.close()

        flash('Modification annulée avec succès.', 'success')
        return redirect(url_for('dossier_medical', numero_assurance=numero_assurance))
    else:
        flash('Accès refusé', 'danger')
        return redirect(url_for('login'))


@app.route('/patient/update/<int:user_id>', methods=['GET', 'POST'])
def update_patient(user_id):
    try:
        if 'user_role' not in session or session['user_role'] != 'patient' or session['user_id'] != user_id:
            flash('Accès refusé.', 'danger')
            return redirect(url_for('login'))

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        if request.method == 'POST':
            # Récupérer les données du formulaire
            adresse = request.form.get('adresse')
            numero_telephone = request.form.get('numero_telephone')
            date_naissance = request.form.get('date_naissance')
            groupe_sanguin = request.form.get('groupe_sanguin')
            lieu_naissance = request.form.get('lieu_naissance')
            genre = request.form.get('genre')

            # Logs pour vérifier les données
            print("Données reçues :", {
                "adresse": adresse,
                "numero_telephone": numero_telephone,
                "date_naissance": date_naissance,
                "groupe_sanguin": groupe_sanguin,
                "lieu_naissance": lieu_naissance,
                "genre": genre,
                "user_id": user_id
            })

            if not all([adresse, numero_telephone, date_naissance, groupe_sanguin, lieu_naissance, genre]):
                flash('Tous les champs sont requis.', 'danger')
                return redirect(url_for('update_patient', user_id=user_id))

            # Exécuter la requête SQL
            update_query = """
                UPDATE patients 
                SET adresse=%s, numero_telephone=%s, date_naissance=%s, 
                    groupe_sanguin=%s, lieu_naissance=%s, genre=%s 
                WHERE utilisateur_id=%s
            """
            cursor.execute(update_query, (adresse, numero_telephone, date_naissance, groupe_sanguin, lieu_naissance, genre, user_id))
            connection.commit()

            # Vérification si la mise à jour a été effectuée
            if cursor.rowcount > 0:
                flash('Coordonnées mises à jour avec succès.', 'success')
            else:
                flash('Aucune modification effectuée.', 'warning')

            return redirect(url_for('dashboard_patient'))

        # Charger les données actuelles du patient
        cursor.execute("SELECT * FROM patients WHERE utilisateur_id = %s", (user_id,))
        patient = cursor.fetchone()

        print("Données actuelles du patient :", patient)

        if not patient:
            flash('Patient introuvable.', 'danger')
            return redirect(url_for('dashboard_patient'))

        return render_template('update_patient.html', patient=patient)

    except Exception as e:
        print("Erreur détectée :", str(e))
        flash(f"Erreur serveur : {e}", 'danger')
        return redirect(url_for('dashboard_patient'))

    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'connection' in locals() and connection:
            connection.close()
@app.route('/patient_rendez_vous', methods=['GET'])
def patient_rendez_vous():
    if 'user_role' in session and session['user_role'] == 'patient':
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Récupérer les rendez-vous du patient connecté
        cursor.execute("""
            SELECT r.date_rdv, r.heure_rdv, r.statut, u.nom AS medecin_nom
            FROM rendez_vous r
            JOIN utilisateurs u ON r.medecin_id = u.id
            WHERE r.patient_id = %s
        """, (session['user_id'],))
        rendez_vous = cursor.fetchall()
        cursor.close()
        connection.close()
        
        return render_template('patient_rendez_vous.html', rendez_vous=rendez_vous)
    else:
        flash('Accès refusé.', 'danger')
        return redirect(url_for('login'))



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
            return redirect(url_for('dashboard_patient'))

        # Récupère la liste des médecins pour le formulaire de rendez-vous
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

        # Récupère la liste des rendez-vous pour le médecin connecté
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
    
    # Tableau de bord pour le patient
@app.route('/dashboard_patient')
def dashboard_patient():
    if 'user_role' in session and session['user_role'] == 'patient':
        return render_template('dashboard_patient.html')
    else:
        flash('Accès refusé', 'danger')
        return redirect(url_for('login'))

# Tableau de bord pour le médecin
@app.route('/dashboard_medecin')
def dashboard_medecin():
    if 'user_role' in session and session['user_role'] == 'medecin':
        return render_template('dashboard_medecin.html')
    else:
        flash('Accès refusé', 'danger')
        return redirect(url_for('login'))

# Tableau de bord pour l'administration (ajustez les fonctionnalités selon vos besoins)
@app.route('/dashboard_administration', methods=['GET', 'POST'])
def dashboard_administration():
    # Check if user has 'administrateur' role in session
    if 'user_role' in session and session['user_role'] == 'administrateur':
        dossier = None
        search = False  # Flag to indicate if a search was performed

        # If this is a POST request, process the insurance number search
        if request.method == 'POST':
            numero_assurance = request.form.get('numero_assurance')
            search = True  # Set the flag since a search is happening

            # Connect to the database and search for the dossier by insurance number
            connection = get_db_connection()
            if connection:
                try:
                    cursor = connection.cursor(dictionary=True)
                    cursor.execute(
                        "SELECT * FROM dossiers_medicaux WHERE numero_assurance = %s",
                        (numero_assurance,)
                    )
                    dossier = cursor.fetchone()  # Fetch the dossier if found
                except mysql.connector.Error as err:
                    logging.error("Database error: %s", err)
                    flash("Erreur lors de la recherche du dossier", 'danger')
                finally:
                    cursor.close()
                    connection.close()

        # Render the template with the dossier and search flag
        return render_template('dashboard_administration.html', dossier=dossier, search=search)
    else:
        # If user is not an administrator, deny access
        flash('Accès refusé', 'danger')
        return redirect(url_for('login'))

    
@app.route('/verifier_num_assurance', methods=['POST'])
def verifier_num_assurance():
    if 'user_role' in session and session['user_role'] == 'medecin':
        num_assurance = request.form['num_assurance']
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Rechercher le patient avec ce numéro d'assurance dans `utilisateurs`
        cursor.execute("SELECT * FROM utilisateurs WHERE numero_assurance = %s AND role = 'patient'", (num_assurance,))
        patient_data = cursor.fetchone()

        if patient_data:
            # Si le patient existe, récupérer les informations additionnelles depuis `patients`
            cursor.execute("SELECT * FROM patients WHERE utilisateur_id = %s", (patient_data['id'],))
            patient_details = cursor.fetchone()
            cursor.close()
            connection.close()

            if patient_details:
                # Combiner les données des deux tables pour les envoyer à la vue
                dossier_data = {**patient_data, **patient_details}
                return render_template('dossier_medical.html', dossier=dossier_data)
            else:
                flash("Informations complémentaires introuvables pour ce patient.", 'danger')
                return redirect(url_for('dashboard_medecin'))
        else:
            cursor.close()
            connection.close()
            flash("Numéro d'assurance invalide ou patient introuvable.", 'danger')
            return redirect(url_for('dashboard_medecin'))
    else:
        flash('Accès refusé', 'danger')
        return redirect(url_for('login'))
    





if __name__ == '__main__':
    app.run(debug=True)
