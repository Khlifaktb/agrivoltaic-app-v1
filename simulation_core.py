# simulation_core.py (v1.1)
# Fih nafs l'hissab, walakin mab9ach kayressem, ghir kayjma3 data.

import pandas as pd
import numpy as np
import pvlib
import pyet
import os

def fetch_pvgis_data(latitude, longitude, altitude):
    try:
        pvgis_output = pvlib.iotools.get_pvgis_tmy(latitude, longitude, map_variables=True)
        weather = pvgis_output[0]
        clean_index = pd.date_range(start='2022-01-01 00:00', end='2022-12-31 23:00', freq='h', tz='Etc/GMT')
        weather = weather.iloc[:len(clean_index)].reset_index(drop=True)
        weather.index = clean_index

        solar_position = pvlib.solarposition.get_solarposition(
            time=weather.index, latitude=latitude, longitude=longitude, altitude=altitude,
            temperature=weather.get('temp_air', 15)
        )
        df_env = pd.DataFrame(index=weather.index)
        df_env['ghi'] = weather.get('ghi', np.nan)
        df_env['dhi'] = weather.get('dhi', np.nan)
        df_env['dni'] = weather.get('dni', np.nan)
        df_env['temp_air'] = weather.get('temp_air', np.nan)
        df_env['wind_speed'] = weather.get('wind_speed', np.nan)
        df_env['relative_humidity'] = weather.get('relative_humidity', np.nan)
        df_env['sun_elevation'] = solar_position['elevation']
        df_env['sun_azimuth'] = solar_position['azimuth']
        return df_env.ffill().bfill()
    except Exception as e:
        print(f"CRITICAL ERROR fetching PVGIS data: {e}")
        return None

def _run_shading_and_et_simulation(df_env, system_params, pitch):
    gcr = system_params['panel_width'] / pitch
    tracking_data = pvlib.tracking.singleaxis(
        apparent_zenith=df_env['sun_elevation'].apply(lambda x: 90 - x),
        apparent_azimuth=df_env['sun_azimuth'],
        axis_azimuth=system_params['axis_azimuth'],
        max_angle=system_params['max_tilt'],
        backtrack=True, gcr=gcr
    )
    df_env['panel_tilt'] = tracking_data['surface_tilt'].fillna(0)

    ground_x = np.arange(0, pitch, 0.1)
    pivot_x = pitch / 2
    is_shaded = pd.DataFrame(0.0, index=df_env.index, columns=ground_x)

    for hour in df_env[df_env['sun_elevation'] > 0].index:
        tilt = np.radians(df_env.loc[hour, 'panel_tilt'])
        sun_ele = np.radians(df_env.loc[hour, 'sun_elevation'])
        sun_azi = np.radians(df_env.loc[hour, 'sun_azimuth'])
        
        panel_half_width = 0.5 * system_params['panel_width']
        x1 = pivot_x - panel_half_width * np.cos(tilt)
        y1 = system_params['pivot_height'] + panel_half_width * np.sin(tilt)
        x2 = pivot_x + panel_half_width * np.cos(tilt)
        y2 = system_params['pivot_height'] - panel_half_width * np.sin(tilt)

        shadow_proj_factor = np.sin(sun_azi - np.radians(system_params['axis_azimuth']-180)) / np.tan(sun_ele + 1e-6)
        shadow_x1 = x1 - y1 * shadow_proj_factor
        shadow_x2 = x2 - y2 * shadow_proj_factor

        start, end = min(shadow_x1, shadow_x2), max(shadow_x1, shadow_x2)
        is_shaded.loc[hour, (ground_x >= start) & (ground_x <= end)] = 1.0

    ghi = df_env['ghi'].to_numpy()[:, np.newaxis]
    dhi = df_env['dhi'].to_numpy()[:, np.newaxis]
    ground_irradiance = dhi + (ghi - dhi) * (1 - is_shaded)
    df_env['avg_ghi_agrivoltaic'] = ground_irradiance.mean(axis=1)

    daily_df = df_env.resample('D').agg({
        'temp_air': ['min', 'max', 'mean'], 'wind_speed': 'mean', 'relative_humidity': 'mean'
    })
    daily_df.columns = ['tmin', 'tmax', 'tmean', 'wind', 'rh']
    daily_df['sol_rad_open'] = (df_env['ghi'] * 3600 / 1_000_000).resample('D').sum()
    daily_df['sol_rad_agri'] = (df_env['avg_ghi_agrivoltaic'] * 3600 / 1_000_000).resample('D').sum()

    et_open_field = pyet.pm(tmean=daily_df['tmean'], wind=daily_df['wind'], rs=daily_df['sol_rad_open'], elevation=system_params['altitude'], lat=system_params['latitude'], tmax=daily_df['tmax'], tmin=daily_df['tmin'], rh=daily_df['rh'])
    et_agrivoltaic = pyet.pm(tmean=daily_df['tmean'], wind=daily_df['wind'], rs=daily_df['sol_rad_agri'], elevation=system_params['altitude'], lat=system_params['latitude'], tmax=daily_df['tmax'], tmin=daily_df['tmin'], rh=daily_df['rh'])
    
    total_et_open_field = et_open_field.sum()
    total_et_agrivoltaic = et_agrivoltaic.sum()

    water_savings_percent = ((total_et_open_field - total_et_agrivoltaic) / total_et_open_field) * 100 if total_et_open_field > 0 else 0

    return df_env, water_savings_percent, total_et_open_field, total_et_agrivoltaic, et_open_field, et_agrivoltaic

def _calculate_crop_metrics(df_sim):
    june_21_data = df_sim[df_sim.index.strftime('%m-%d') == '06-21']
    ppfd_open = -46.65 + 1.792 * june_21_data['ghi'].clip(lower=0)
    dli_open = (ppfd_open.clip(lower=0) * 3600).sum() / 1_000_000
    ppfd_agrivoltaic = -46.65 + 1.792 * june_21_data['avg_ghi_agrivoltaic'].clip(lower=0)
    dli_agrivoltaic = (ppfd_agrivoltaic.clip(lower=0) * 3600).sum() / 1_000_000

    df_sim['temp_agrivoltaic'] = df_sim['temp_air'] - 1.2
    summer_months = df_sim[df_sim.index.month.isin([6, 7, 8])]
    peak_temp_open = summer_months['temp_air'].max()
    peak_temp_agri = summer_months['temp_agrivoltaic'].max()
    
    return dli_open, dli_agrivoltaic, peak_temp_open, peak_temp_agri

# --- [MODIFIED v1.1] ---
# Mab9inach kanressmo, wellina kanwejjdo data l'JavaScript
def _prepare_graph_data(data_dict, pitch):
    graph_data = {}

    # --- Graph 1: Summer Solstice Irradiance ---
    june_21_data = data_dict['df_sim'][data_dict['df_sim'].index.strftime('%m-%d') == '06-21']
    graph_data['irradiance'] = {
        'labels': june_21_data.index.strftime('%H:%M').tolist(),
        'datasets': [
            {'label': 'Open Field GHI', 'data': june_21_data['ghi'].tolist(), 'borderColor': 'orange', 'tension': 0.1},
            {'label': f'Agrivoltaic GHI (Pitch = {pitch}m)', 'data': june_21_data['avg_ghi_agrivoltaic'].tolist(), 'borderColor': 'brown', 'tension': 0.1}
        ]
    }

    # --- Graph 2: Monthly Water Savings ---
    monthly_et_open = data_dict['et_open'].resample('ME').sum()
    monthly_et_agri = data_dict['et_agri'].resample('ME').sum()
    monthly_savings = monthly_et_open - monthly_et_agri
    graph_data['monthly_water'] = {
        'labels': monthly_savings.index.strftime('%b').tolist(),
        'datasets': [
            {'label': 'Water Saved (mm)', 'data': monthly_savings.tolist(), 'backgroundColor': 'skyblue'}
        ]
    }
    
    # --- Graph 3: Cumulative Water Savings ---
    cumulative_savings = (data_dict['et_open'] - data_dict['et_agri']).cumsum()
    graph_data['cumulative_water'] = {
        'labels': cumulative_savings.index.strftime('%Y-%m-%d').tolist(),
        'datasets': [
            {'label': 'Total Water Saved (mm)', 'data': cumulative_savings.tolist(), 'borderColor': 'royalblue', 'tension': 0.1}
        ]
    }
    
    # --- Graph 4: Temperature on Hottest Day ---
    hottest_day = data_dict['df_sim']['temp_air'].idxmax().date()
    hottest_day_data = data_dict['df_sim'][data_dict['df_sim'].index.date == hottest_day]
    graph_data['peak_temp'] = {
        'title': f'Temperature Profile on Hottest Day ({hottest_day.strftime("%B %d")})',
        'labels': hottest_day_data.index.strftime('%H:%M').tolist(),
        'datasets': [
            {'label': 'Open Field Temperature', 'data': hottest_day_data['temp_air'].tolist(), 'borderColor': 'red', 'tension': 0.1},
            {'label': 'Agrivoltaic Temperature', 'data': hottest_day_data['temp_agrivoltaic'].tolist(), 'borderColor': 'green', 'tension': 0.1, 'borderDash': [5, 5]}
        ]
    }
    
    return graph_data

def run_single_pitch_analysis(df_env_base, system_params, crop_params, pitch):
    df_sim, water_savings, et_open, et_agri, et_open_series, et_agri_series = _run_shading_and_et_simulation(df_env_base.copy(), system_params, pitch)
    dli_open, dli_agri, peak_temp_open, peak_temp_agri = _calculate_crop_metrics(df_sim)

    results = {
        "water_savings": water_savings, "et_open": et_open, "et_agri": et_agri,
        "dli_open": dli_open, "dli_agri": dli_agri,
        "peak_temp_open": peak_temp_open, "peak_temp_agri": peak_temp_agri
    }
    
    # [MODIFIED v1.1] Kanwejjdo data dyal l'graph, ماشي les images
    plot_data_for_js = {'df_sim': df_sim, 'et_open': et_open_series, 'et_agri': et_agri_series}
    graph_data = _prepare_graph_data(plot_data_for_js, pitch)
    
    return results, graph_data

def run_optimization_analysis(df_env_base, system_params, crop_params):
    pitch_options = np.arange(4.0, 10.5, 0.5)
    results_list = []

    for pitch in pitch_options:
        _, water_savings, _, _, _, _ = _run_shading_and_et_simulation(df_env_base.copy(), system_params, pitch)
        results_list.append({
            'pitch': pitch,
            'water_savings_percent': water_savings
        })
    results_df = pd.DataFrame(results_list)
    optimal_pitch_data = results_df.loc[results_df['water_savings_percent'].idxmax()]

    # [MODIFIED v1.1] Kanwejjdo data dyal l'graph dyal l'optimization
    graph_data = {
        'optimization': {
            'labels': results_df['pitch'].tolist(),
            'datasets': [
                {'label': 'Simulated Savings', 'data': results_df['water_savings_percent'].tolist(), 'borderColor': 'blue', 'tension': 0.1}
            ],
            'optimal_pitch': optimal_pitch_data['pitch'],
            'max_savings': optimal_pitch_data['water_savings_percent']
        }
    }
    
    # Kanwejjdo hta les graphs l'okhrin dyal l'optimal pitch
    _ , single_pitch_graph_data = run_single_pitch_analysis(df_env_base, system_params, crop_params, optimal_pitch_data['pitch'])
    graph_data.update(single_pitch_graph_data)
    
    return optimal_pitch_data.to_dict(), graph_data
