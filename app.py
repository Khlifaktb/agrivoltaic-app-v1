# app.py (v1.9.2 - The Final Fix for All Features)

import os
import json
from flask import Flask, request, jsonify, render_template, send_from_directory
import simulation_core as core
from datetime import datetime
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable

# --- Multilingual Comment Functions (The correct, final versions) ---
def _generate_water_comment_v3(water_savings_percent, et_open_mm, et_agri_mm, lang='en'):
    """Generates a detailed, tiered, multilingual comment on water savings."""
    
    text_fragments = {
        'en': {
            'prefix': "The annual water saving is {percent:.1f}%, which is considered a {level} saving. This translates to a reduction of {mm:.0f} mm in evapotranspiration, or about {tonnes:.0f} tonnes of water saved per hectare per year, strengthening the farm's water resilience.",
            'levels': {'negligible': "negligible", 'modest': "modest", 'significant': "significant", 'very_important': "very important", 'exceptional': "exceptional"}
        },
        'it': {
            'prefix': "Il risparmio idrico annuale è del {percent:.1f}%, considerato un risparmio {level}. Ciò si traduce in una riduzione di {mm:.0f} mm di evapotraspirazione, ovvero circa {tonnes:.0f} tonnellate di acqua risparmiate per ettaro all'anno, rafforzando la resilienza idrica dell'azienda.",
            'levels': {'negligible': "trascurabile", 'modest': "modesto", 'significant': "significativo", 'very_important': "molto importante", 'exceptional': "eccezionale"}
        }
    }
    
    saved_mm = et_open_mm - et_agri_mm
    saved_tonnes_per_ha = saved_mm * 10

    if water_savings_percent < 5:
        level_key = "negligible"
        tag = "warn"
    elif water_savings_percent < 10:
        level_key = "modest"
        tag = "good"
    elif water_savings_percent < 20:
        level_key = "significant"
        tag = "good"
    elif water_savings_percent < 30:
        level_key = "very_important"
        tag = "good"
    else:
        level_key = "exceptional"
        tag = "good"
    
    selected_lang = text_fragments.get(lang, text_fragments['en'])
    level_text = selected_lang['levels'][level_key]
    
    text = selected_lang['prefix'].format(percent=water_savings_percent, level=level_text, mm=saved_mm, tonnes=saved_tonnes_per_ha)
    
    return {'title_key': 'water_comment_title', 'text': text, 'tag': tag}


def _generate_temp_comment_v4(temp_agri, peak_temp_open, crop_params, lang='en'):
    """Generates a highly nuanced, multilingual analysis of temperature."""
    
    text_fragments = {
        'en': {
            'prefix': "The panels provide {cooling_desc}, bringing the peak temperature to {temp_agri:.1f}°C. For {crop_name}, this temperature is {crop_impact}",
            'cooling': {'none': "an almost non-existent cooling effect", 'moderate': "a moderate cooling effect", 'beneficial': "a beneficial cooling effect"},
            'impact': {
                'ideal': "maintained within its ideal comfort range of {min}-{max}°C.",
                'hot_slight': "slightly above its comfort threshold of {max}°C, but the risk of stress is low.",
                'hot_moderate': "notably above its comfort threshold of {max}°C, indicating a moderate heat stress risk.",
                'hot_high': "significantly above its comfort threshold of {max}°C, creating a high heat stress risk.",
                'cold_slight': "slightly below its comfort range of {min}°C, which is generally well-tolerated.",
                'cold_moderate': "potentially too cool, being {diff:.1f}°C below the minimum threshold, which could slow its growth."
            }
        },
        'it': {
            'prefix': "I pannelli forniscono {cooling_desc}, portando la temperatura di picco a {temp_agri:.1f}°C. Per {crop_name}, questa temperatura è {crop_impact}",
            'cooling': {'none': "un effetto di raffreddamento quasi inesistente", 'moderate': "un moderato effetto di raffreddamento", 'beneficial': "un benefico effetto di raffreddamento"},
            'impact': {
                'ideal': "mantenuta nel suo intervallo di comfort ideale di {min}-{max}°C.",
                'hot_slight': "leggermente al di sopra della sua soglia di comfort di {max}°C, ma il rischio di stress è basso.",
                'hot_moderate': "notevolmente al di sopra della sua soglia di comfort di {max}°C, indicando un moderato rischio di stress da calore.",
                'hot_high': "significativamente al di sopra della sua soglia di comfort di {max}°C, creando un elevato rischio di stress da calore.",
                'cold_slight': "leggermente al di sotto del suo intervallo di comfort di {min}°C, che è generalmente ben tollerato.",
                'cold_moderate': "potenzialmente troppo fresca, essendo {diff:.1f}°C sotto la soglia minima, il che potrebbe rallentarne la crescita."
            }
        }
    }
    
    selected_lang = text_fragments.get(lang, text_fragments['en'])
    
    temp_min_crop = crop_params['temp_min']
    temp_max_crop = crop_params['temp_max']
    crop_name = crop_params.get('name', 'the crop')
    cooling_effect = peak_temp_open - temp_agri

    if cooling_effect < 0.5: cooling_key = 'none'
    elif cooling_effect < 1.5: cooling_key = 'moderate'
    else: cooling_key = 'beneficial'
    
    if temp_agri >= temp_min_crop and temp_agri <= temp_max_crop:
        impact_key, tag, impact_values = 'ideal', 'good', {'min': temp_min_crop, 'max': temp_max_crop}
    elif temp_agri > temp_max_crop:
        diff_from_max = temp_agri - temp_max_crop
        if diff_from_max <= 2: impact_key, tag, impact_values = 'hot_slight', 'good', {'max': temp_max_crop}
        elif diff_from_max <= 5: impact_key, tag, impact_values = 'hot_moderate', 'warn', {'max': temp_max_crop}
        else: impact_key, tag, impact_values = 'hot_high', 'bad', {'max': temp_max_crop}
    else: # temp_agri < temp_min_crop
        diff_from_min = temp_min_crop - temp_agri
        if diff_from_min <= 3: impact_key, tag, impact_values = 'cold_slight', 'good', {'min': temp_min_crop}
        else: impact_key, tag, impact_values = 'cold_moderate', 'warn', {'min': temp_min_crop, 'diff': diff_from_min}

    cooling_text = selected_lang['cooling'][cooling_key]
    impact_text = selected_lang['impact'][impact_key].format(**impact_values)
    
    text = selected_lang['prefix'].format(cooling_desc=cooling_text, temp_agri=temp_agri, crop_name=crop_name, crop_impact=impact_text)
    
    return {'title_key': 'temp_comment_title', 'text': text, 'tag': tag}


def _generate_dli_comment_v3(dli_agri, dli_open, peak_temp_open, crop_params, lang='en'):
    """Generates a three-dimensional, multilingual analysis of DLI."""
    
    text_fragments = {
        'en': {
            'prefix': "The system provides {shading_desc} ({shading_percent:.0f}%), resulting in a DLI of {dli_agri:.1f} mol/m²/day. For {crop_name}, this light level is {light_level_desc} (optimal range: {dli_min}-{dli_max}). {climate_context}",
            'shading': {'none': "almost no shade", 'light': "light shade", 'moderate': "moderate shade", 'significant': "significant shade"},
            'level': {'critical': "critically low", 'low': "below the recommended threshold", 'ideal': "ideal", 'abundant': "abundant, even with shading"},
            'context': {
                'hot_low_shade': "In a hot climate like this (peaks at {peak_temp:.0f}°C), such light shading might not offer sufficient thermal protection.",
                'hot_good_shade': "In a hot climate like this (peaks at {peak_temp:.0f}°C), this shade is particularly beneficial for protecting the crop.",
                'temperate_high_shade': "In a temperate climate (peaks at {peak_temp:.0f}°C), such strong shading risks limiting yield if light is already a limiting factor.",
                'temperate_low_shade': "In a temperate climate (peaks at {peak_temp:.0f}°C), minimal shading is a logical strategy to maximize the crop's light exposure."
            }
        },
        'it': {
            'prefix': "Il sistema fornisce {shading_desc} ({shading_percent:.0f}%), risultando in un DLI di {dli_agri:.1f} mol/m²/giorno. Per {crop_name}, questo livello di luce è {light_level_desc} (intervallo ottimale: {dli_min}-{dli_max}). {climate_context}",
            'shading': {'none': "un'ombreggiatura quasi nulla", 'light': "un'ombreggiatura leggera", 'moderate': "un'ombreggiatura moderata", 'significant': "un'ombreggiatura significativa"},
            'level': {'critical': "criticamente basso", 'low': "inferiore alla soglia raccomandata", 'ideal': "ideale", 'abundant': "abbondante, anche con l'ombreggiatura"},
            'context': {
                'hot_low_shade': "In un clima caldo come questo (picchi a {peak_temp:.0f}°C), un'ombreggiatura così leggera potrebbe non offrire una protezione termica sufficiente.",
                'hot_good_shade': "In un clima caldo come questo (picchi a {peak_temp:.0f}°C), questa ombreggiatura è particolarmente vantaggiosa per proteggere la coltura.",
                'temperate_high_shade': "In un clima temperato (picchi a {peak_temp:.0f}°C), un'ombreggiatura così forte rischia di limitare la resa se la luce è già un fattore limitante.",
                'temperate_low_shade': "In un clima temperato (picchi a {peak_temp:.0f}°C), un'ombreggiatura minima è una strategia logica per massimizzare l'esposizione alla luce della coltura."
            }
        }
    }
    
    selected_lang = text_fragments.get(lang, text_fragments['en'])

    dli_min = crop_params['dli_min']
    dli_max = crop_params['dli_max']
    crop_name = crop_params.get('name', "the crop")
    
    shading_percent = (1 - (dli_agri / dli_open)) * 100 if dli_open > 0 else 0
    if shading_percent < 5: shading_key = 'none'
    elif shading_percent < 15: shading_key = 'light'
    elif shading_percent < 30: shading_key = 'moderate'
    else: shading_key = 'significant'
    
    if dli_agri < dli_min * 0.8: level_key, tag = 'critical', 'bad'
    elif dli_agri < dli_min: level_key, tag = 'low', 'warn'
    elif dli_agri <= dli_max: level_key, tag = 'ideal', 'good'
    else: level_key, tag = 'abundant', 'good'

    context_key, context_text = None, ""
    if peak_temp_open > 30:
        if shading_percent < 10: context_key = 'hot_low_shade'
        else: context_key = 'hot_good_shade'
    else:
        if shading_percent > 20 and dli_agri < dli_min: context_key = 'temperate_high_shade'
        elif shading_percent < 5: context_key = 'temperate_low_shade'
    
    if context_key:
        context_text = selected_lang['context'][context_key].format(peak_temp=peak_temp_open)
        
    shading_text = selected_lang['shading'][shading_key]
    level_text = selected_lang['level'][level_key]
    
    text = selected_lang['prefix'].format(shading_desc=shading_text, shading_percent=shading_percent, dli_agri=dli_agri, crop_name=crop_name, light_level_desc=level_text, dli_min=dli_min, dli_max=dli_max, climate_context=context_text)
    
    return {'title_key': 'dli_comment_title', 'text': text, 'tag': tag}


# --- Configuration ---
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['LANGUAGES_FOLDER'] = 'languages'


# --- [THE FIX IS HERE] ---
# Restoring the full, correct code for the get_location_name function
@app.route('/get_location_name', methods=['POST'])
def get_location_name():
    try:
        data = request.json
        lat = data.get('lat')
        lon = data.get('lon')

        if not lat or not lon:
            return jsonify({'error': 'Latitude and Longitude are required.'}), 400

        geolocator = Nominatim(user_agent="agrivoltaic_app_final_v1.3")
        location = geolocator.reverse(f"{lat}, {lon}", exactly_one=True, timeout=10)

        if location:
            return jsonify({'location_name': location.address})
        else:
            return jsonify({'location_name': 'Location name not found.'})

    except GeocoderUnavailable:
        return jsonify({'error': 'Geocoding service is unavailable. Please try again later.'}), 503
    except Exception as e:
        print(f"An error occurred in get_location_name: {e}")
        return jsonify({'error': str(e)}), 500


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
        lang = params.get('lang', 'en')

        df_env = core.fetch_pvgis_data(sys_params['latitude'], sys_params['longitude'], sys_params['altitude'])
        if df_env is None:
            return jsonify({'error': "Error fetching data from PVGIS."}), 500
        
        results = {}
        graph_data = {}
        analysis_comments = []

        if mode == 'Optimization':
            opt_results, graph_data = core.run_optimization_analysis(df_env, sys_params, crop_params)
            best_pitch = opt_results['pitch']
            temp_results, _ = core.run_single_pitch_analysis(df_env, sys_params, crop_params, best_pitch)
            results.update(temp_results)
            results.update(opt_results)
            water_savings_value = results['water_savings_percent']
        else:
            if not custom_pitch or custom_pitch <= 0:
                return jsonify({'error': 'Invalid custom pitch value.'}), 400
            results, graph_data = core.run_single_pitch_analysis(df_env, sys_params, crop_params, custom_pitch)
            water_savings_value = results['water_savings']
        
        analysis_comments.append(_generate_water_comment_v3(water_savings_value, results['et_open'], results['et_agri'], lang))
        analysis_comments.append(_generate_temp_comment_v4(results['peak_temp_agri'], results['peak_temp_open'], crop_params, lang))
        analysis_comments.append(_generate_dli_comment_v3(results['dli_agri'], results['dli_open'], results['peak_temp_open'], crop_params, lang))

        return jsonify({
            'results': results,
            'graph_data': graph_data,
            'analysis_comments': analysis_comments
        })

    except Exception as e:
        import traceback
        print(f"An error occurred in /simulate: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/languages/<lang_code>.json')
def get_language(lang_code):
    return send_from_directory(app.config['LANGUAGES_FOLDER'], f"{lang_code}.json")


if __name__ == '__main__':
    app.run(debug=True)