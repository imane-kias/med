import os
import pandas as pd

def analyze_symptoms(user_symptoms):
    # Chemin vers le fichier CSV
    dataset_path = 'C:/Users/bziks/OneDrive/Desktop/AT2/med2/Disease.csv'  # Mettez le bon chemin ici

    # Vérifiez si le fichier existe
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Le fichier {dataset_path} est introuvable. Vérifiez le chemin.")

    # Charger le dataset
    try:
        data = pd.read_csv(dataset_path)
    except Exception as e:
        raise RuntimeError(f"Erreur lors du chargement du fichier CSV : {e}")

    # Vérifiez que les colonnes nécessaires existent
    required_columns = ['Disease', 'Symptoms', 'Advice', 'Urgency']
    if not all(col in data.columns for col in required_columns):
        raise ValueError(f"Le fichier CSV doit contenir les colonnes suivantes : {', '.join(required_columns)}")

    # Convertir les colonnes de symptômes en listes pour faciliter la comparaison
    data['Symptoms'] = data['Symptoms'].apply(lambda x: x.split(';'))

    # Convertir les symptômes fournis par l'utilisateur en une liste
    user_symptoms = [symptom.strip().lower() for symptom in user_symptoms]

    # Recherche des maladies correspondant aux symptômes
    matches = []
    for _, row in data.iterrows():
        matched_symptoms = [symptom for symptom in user_symptoms if symptom in row['Symptoms']]
        if matched_symptoms:
            matches.append({
                "disease": row['Disease'],
                "matched_symptoms": matched_symptoms,
                "advice": row['Advice'],
                "urgency": row['Urgency']
            })

    # Si aucune correspondance trouvée
    if not matches:
        return {
            "disease": "Inconnu",
            "description": f"Symptômes non valides : {', '.join(user_symptoms)}",
            "advice": "Veuillez vérifier les symptômes entrés.",
            "urgency": "Modérée"
        }

    # Retourner la maladie ayant le plus de correspondances
    best_match = max(matches, key=lambda x: len(x['matched_symptoms']))
    return {
        "disease": best_match['disease'],
        "description": f"Symptômes correspondants : {', '.join(best_match['matched_symptoms'])}",
        "advice": best_match['advice'],
        "urgency": best_match['urgency']
    }
