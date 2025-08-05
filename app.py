# app.py (v1.2)
# Zedna fih les fonctions dyal les commentaires

import os
import json
from flask import Flask, request, jsonify, render_template, send_from_directory
import simulation_core as core
from datetime import datetime

# --- [NEW v1.2] Fonctions pour générer les commentaires ---
def _generate_water_comment(water_savings_percent, et_open_mm, et_agri_mm):
    saved_mm = et_open_mm - et_agri_mm
    saved_tonnes_per_ha = saved_mm * 10
    text = f"This amounts to an estimated saving of {saved_tonnes_per_ha:.0f} tonnes of water per hectare per year."
    if water_savings_percent < 8:
        return text + " This is a modest saving, but still beneficial.", "warn"
    elif water_savings_percent < 15:
        return text + " This is a significant saving, contributing well to water conservation.", "good"
    else:
        return text + " This is an excellent level of water savings, making a major impact on local water resources!", "good"

def _generate_dli_comment(dli_agri, crop_params):
    dli_min = crop_params['dli_min']
    dli_max = crop_params['dli_max']
    crop_name = crop_params.get('name', "the crop")
    if dli_agri < dli_min * 0.8:
        return f"The light level ({dli_agri:.1f}) is critically low, well below the minimum of {dli_min} required by {crop_name}. Crop failure is likely.", "bad"
    elif dli_agri < dli_min:
        return f"The light level ({dli_agri:.1f}) is below the recommended minimum of {dli_min} for {crop_name}. This could stress the plant and reduce yield.", "warn"
    elif dli_agri <= dli_max:
        return f"The light level ({dli_agri:.1f}) is within the optimal range for {crop_name} ({dli_min} - {dli_max}). Conditions are ideal.", "good"
    else:
        return f"The light level ({dli_agri:.1f}) exceeds the optimal maximum of {dli_max} for {crop_name}. Shading effect is minimal in summer.", "good"

def _generate_temp_comment(temp_agri, crop_params):
    temp_max = crop_params['temp_max']
    if temp_agri < 33:
        return f"Although the peak temperature ({temp_agri:.1f} °C) is higher than the optimal {temp_max}°C for {crop_params.get('name', 'the crop')}, the difference is not significant enough to cause serious heat stress.", "good"
    else:
        return f"Even with shading, peak temperature ({temp_agri:.1f} C) exceeds the optimal maximum of {temp_max}°C for {crop_params.get('name', 'the crop')}, indicating a risk of heat stress", "warn"

# --- Configuration ---
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['LANGUAGES_FOLDER'] = 'languages'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/simulate', methods=['POST'])
def simulate():
    try:
        params = request.json
        sys_params = params['sys_params']
        crop_params = params['crop_params']
        mode = params['mode']
        custom_pitch = params.get('custom_pitch')

        df_env = core.fetch_pvgis_data(sys_params['latitude'], sys_params['longitude'], sys_params['altitude'])
        if df_env is None:
            return jsonify({'error': "Erreur lors de la récupération des données de PVGIS."}), 500
        
        analysis_comments = [] # Liste khawya fin ghadi n7etto les commentaires

        if mode == 'Optimization':
            results, graph_data = core.run_optimization_analysis(df_env, sys_params, crop_params)
            # Zedna commentaire dyal l'optimization
            water_text, water_tag = _generate_water_comment(results['water_savings_percent'], results['et_open'], results['et_agri'])
            analysis_comments.append({'title_key': 'water_comment_title', 'text': water_text, 'tag': water_tag})
        else:
            if not custom_pitch or custom_pitch <= 0:
                return jsonify({'error': 'La valeur du pitch personnalisé est invalide.'}), 400
            results, graph_data = core.run_single_pitch_analysis(df_env, sys_params, crop_params, custom_pitch)
            # Zedna les 3 commentaires
            water_text, water_tag = _generate_water_comment(results['water_savings'], results['et_open'], results['et_agri'])
            dli_text, dli_tag = _generate_dli_comment(results['dli_agri'], crop_params)
            temp_text, temp_tag = _generate_temp_comment(results['peak_temp_agri'], crop_params)
            analysis_comments.append({'title_key': 'water_comment_title', 'text': water_text, 'tag': water_tag})
            analysis_comments.append({'title_key': 'dli_comment_title', 'text': dli_text, 'tag': dli_tag})
            analysis_comments.append({'title_key': 'temp_comment_title', 'text': temp_text, 'tag': temp_tag})

        # [MODIFIED v1.2] Siftna hta les commentaires
        return jsonify({
            'results': results,
            'graph_data': graph_data,
            'analysis_comments': analysis_comments
        })

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/languages/<lang_code>.json')
def get_language(lang_code):
    return send_from_directory(app.config['LANGUAGES_FOLDER'], f"{lang_code}.json")

if __name__ == '__main__':
    app.run(debug=True)
