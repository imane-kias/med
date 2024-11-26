from flask import Blueprint, request, jsonify
from scripts.symptom_analyzer import analyze_symptoms

chatbot_bp = Blueprint('chatbot', __name__)

@chatbot_bp.route('/analyze-symptoms', methods=['POST'])
def analyze():
    try:
        # Récupérer les données JSON envoyées par le client
        data = request.json
        symptoms = data.get('symptoms', [])

        # Vérifier que l'utilisateur a fourni au moins 3 symptômes
        if not symptoms or len(symptoms) < 3:
            return jsonify({"error": "Veuillez fournir au moins 3 symptômes."}), 400

        # Analyser les symptômes en utilisant la fonction du module symptom_analyzer
        result = analyze_symptoms(symptoms)
        return jsonify(result)

    except Exception as e:
        # Gérer les erreurs et renvoyer un message approprié
        return jsonify({"error": f"Erreur lors de l'analyse des symptômes : {str(e)}"}), 500
