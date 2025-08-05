# app.py

import os
from flask import Flask, render_template, request, jsonify, url_for
import google.generativeai as genai
import json # Pour charger les fichiers de langue

# --- Simulation Placeholder ---
# HADI GHI BLASSA DIAL SIMULATION DIALEK L7A9I9IYA
# Hna ghadi tkon la fonction dialek li kadir l7ssab dial simulation
def perform_actual_simulation(inputs):
    # DÉBUT DU CODE DE SIMULATION FACTICE (À REMPLACER)
    # Dans un vrai cas, vous utiliseriez les 'inputs' pour calculer des vrais résultats.
    import random
    mode = inputs.get('mode')
    results = {}
    graph_data = {}

    if mode == 'Optimization':
        optimal_pitch = random.uniform(5.0, 7.0)
        max_savings = random.uniform(25.0, 40.0)
        results = {
            "pitch": optimal_pitch,
            "water_savings_percent": max_savings
        }
        graph_data['optimization'] = {
            "labels": [p/10 for p in range(30, 101)],
            "datasets": [{
                "label": "Water Savings (%)",
                "data": [max_savings * (1 - ((p/10 - optimal_pitch)**2) / 25) for p in range(30, 101)],
                "borderColor": "blue"
            }],
            "optimal_pitch": optimal_pitch,
            "max_savings": max_savings
        }
    else:
        results = {
            "water_savings": random.uniform(15.0, 30.0),
            "dli_agri": random.uniform(15.0, 22.0),
            "dli_open": random.uniform(25.0, 35.0),
            "peak_temp_agri": random.uniform(28.0, 32.0),
            "peak_temp_open": random.uniform(35.0, 40.0)
        }

    # Données factices communes pour les graphiques
    graph_data['irradiance'] = {"labels": ["6am", "9am", "12pm", "3pm", "6pm"], "datasets": [{"label": "Ground", "data": [50, 400, 600, 350, 40]}, {"label": "Open", "data": [60, 500, 900, 450, 50]}]}
    graph_data['peak_temp'] = {"title": "Hottest Day Temp", "labels": ["6am", "9am", "12pm", "3pm", "6pm"], "datasets": [{"label": "Agri", "data": [22, 26, 29, 31, 27]}, {"label": "Open", "data": [23, 29, 35, 38, 32]}]}
    graph_data['monthly_water'] = {"labels": ["J", "F", "M", "A", "M", "J"], "datasets": [{"label": "Savings", "data": [10, 15, 20, 30, 35, 40]}]}
    graph_data['cumulative_water'] = {"labels": ["J", "F", "M", "A", "M", "J"], "datasets": [{"label": "Cumulative", "data": [10, 25, 45, 75, 110, 150]}]}
    # FIN DU CODE DE SIMULATION FACTICE

    return results, graph_data

# --- Configuration de l'API Google ---
try:
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    if not GOOGLE_API_KEY:
        print("AVERTISSEMENT: La clé GOOGLE_API_KEY n'est pas définie. L'IA sera désactivée.")
    else:
        genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    print(f"Erreur lors de la configuration de l'API Google: {e}")
    GOOGLE_API_KEY = None

# --- Nouvelle fonction IA (adaptée à votre code) ---
def generate_ai_comment(crop_params, sim_results, lang='en'):
    """
    Génère un commentaire IA et le retourne dans le format attendu par le script JS.
    """
    if not GOOGLE_API_KEY:
        # Retourne un commentaire par défaut si l'IA n'est pas configurée
        return {
            "tag": "ai-disabled",
            "title_key": "ai_analysis_title",
            "text": "AI analysis is currently disabled. Please configure the API key on the server."
        }
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        
        # Créer un prompt plus intelligent qui utilise les résultats de la simulation
        crop_name = crop_params.get('name', 'the crop')
        results_summary = json.dumps(sim_results) # Convertit les résultats en texte
        
        prompt_lang = "French" if lang == 'it' else "English" # On peut adapter la langue du prompt

        prompt = (f"You are an agronomist specializing in agrivoltaics. "
                  f"Based on the simulation for '{crop_name}' which yielded these results: {results_summary}, "
                  f"provide a short, insightful analysis (2-3 sentences) in {prompt_lang}. "
                  f"Focus on the benefits or potential drawbacks shown by the data.")
                  
        response = model.generate_content(prompt)
        ai_text = response.text
        
        # On retourne un dictionnaire qui correspond à la structure de `analysis_comments`
        return {
            "tag": "ai", # Un tag pour le style CSS si vous voulez
            "title_key": "ai_analysis_title", # La clé pour la traduction du titre
            "text": ai_text # Le texte généré par l'IA
        }

    except Exception as e:
        print(f"Erreur lors de l'appel à l'API Gemini: {e}")
        return {
            "tag": "ai-error",
            "title_key": "ai_analysis_title",
            "text": "An error occurred while generating the AI analysis. The agrivoltaic system seems promising for this crop."
        }

# --- Application Flask ---
app = Flask(__name__, static_folder='static', static_url_path='')

@app.route('/')
def index():
    return render_template('index.html')

# Endpoint pour servir les fichiers de langue que votre JS demande
@app.route('/languages/<lang>.json')
def language(lang):
    return app.send_static_file(os.path.join('languages', f'{lang}.json'))

# --- L'API endpoint que votre JS appelle ---
@app.route('/simulate', methods=['POST'])
def simulate():
    try:
        # 1. Récupérer les données envoyées par votre script JS
        inputs = request.get_json()
        
        # 2. Lancer votre VRAIE simulation ici
        sim_results, graph_data = perform_actual_simulation(inputs)
        
        # 3. Créer les commentaires basés sur des règles (comme vous faites déjà)
        # Ceci est un exemple, adaptez-le à votre logique existante
        analysis_comments = []
        if inputs['mode'] == 'Optimization':
             analysis_comments.append({
                 "tag": "info",
                 "title_key": "opt_summary_title",
                 "text": f"The optimization for {inputs['crop_params']['name']} found the best balance at a pitch of {sim_results['pitch']:.1f}m."
             })
        else:
             analysis_comments.append({
                 "tag": "info",
                 "title_key": "custom_summary_title",
                 "text": f"The simulation with a custom pitch shows water savings of {sim_results['water_savings']:.1f}%."
             })

        # 4. === L'AJOUT IMPORTANT ===
        # Générer le commentaire IA et l'ajouter à la liste
        # On passe les paramètres de la culture et les résultats pour une meilleure analyse
        ai_comment = generate_ai_comment(inputs['crop_params'], sim_results)
        analysis_comments.append(ai_comment)

        # 5. Construire la réponse JSON finale exactement comme votre script l'attend
        response_data = {
            "results": sim_results,
            "graph_data": graph_data,
            "analysis_comments": analysis_comments # La liste contient maintenant le commentaire de l'IA
        }
        
        return jsonify(response_data)

    except Exception as e:
        print(f"Erreur dans /simulate: {e}")
        return jsonify({"error": f"An internal server error occurred: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)