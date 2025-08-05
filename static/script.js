// static/script.js (The Real Final Fix)
// Hada howa l'code l'nqi o l's7i7 100%

document.addEventListener('DOMContentLoaded', () => {
    // --- Get all elements ---
    const runBtn = document.getElementById('run_simulation_btn');
    const modeOptRadio = document.getElementById('mode_opt');
    const modeCustomRadio = document.getElementById('mode_custom');
    const customPitchInput = document.getElementById('custom_pitch');
    const langSelect = document.getElementById('lang_select');

    const welcomeMessage = document.getElementById('welcome_message');
    const loadingIndicator = document.getElementById('loading_indicator');
    const resultsDashboard = document.getElementById('results_dashboard');
    const errorMessageDiv = document.getElementById('error_message');

    let currentLanguageStrings = {};
    let activeCharts = {};

    // --- Event Listeners ---
    runBtn.addEventListener('click', runSimulation);
    modeOptRadio.addEventListener('change', toggleCustomPitch);
    modeCustomRadio.addEventListener('change', toggleCustomPitch);
    langSelect.addEventListener('change', (e) => switchLanguage(e.target.value));

    // --- Initial Setup ---
    switchLanguage(langSelect.value);
    toggleCustomPitch();

    // --- Functions ---
    function toggleCustomPitch() {
        customPitchInput.disabled = modeOptRadio.checked;
    }

    async function switchLanguage(langCode) {
        try {
            const response = await fetch(`/languages/${langCode}.json`);
            currentLanguageStrings = await response.json();
            
            document.querySelectorAll('[data-lang-key]').forEach(elem => {
                const key = elem.getAttribute('data-lang-key');
                if (currentLanguageStrings[key]) {
                    if (elem.tagName === 'INPUT' || elem.tagName === 'SELECT' || elem.tagName === 'BUTTON' || elem.tagName === 'TITLE') {
                        if(elem.placeholder) elem.placeholder = currentLanguageStrings[key];
                        else if (elem.tagName === 'BUTTON' || elem.tagName === 'TITLE') elem.textContent = currentLanguageStrings[key];
                    } else {
                        elem.textContent = currentLanguageStrings[key];
                    }
                }
            });
        } catch (error) {
            console.error('Could not load language file:', error);
        }
    }

    function getInputs() {
        const inputs = [
            document.getElementById('lat').value, document.getElementById('lon').value, document.getElementById('alt').value,
            document.getElementById('panel_width').value, document.getElementById('panel_length').value,
            document.getElementById('pivot_height').value, document.getElementById('max_tilt').value, document.getElementById('axis_azimuth').value,
            document.getElementById('crop_name').value, document.getElementById('dli_min').value, document.getElementById('dli_max').value,
            document.getElementById('temp_min').value, document.getElementById('temp_max').value
        ];
        if (inputs.some(val => val === '')) return null;

        return {
            sys_params: {
                latitude: parseFloat(document.getElementById('lat').value),
                longitude: parseFloat(document.getElementById('lon').value),
                altitude: parseFloat(document.getElementById('alt').value),
                panel_width: parseFloat(document.getElementById('panel_width').value),
                panel_length: parseFloat(document.getElementById('panel_length').value),
                pivot_height: parseFloat(document.getElementById('pivot_height').value),
                max_tilt: parseFloat(document.getElementById('max_tilt').value),
                axis_azimuth: parseFloat(document.getElementById('axis_azimuth').value),
            },
            crop_params: {
                name: document.getElementById('crop_name').value,
                dli_min: parseFloat(document.getElementById('dli_min').value),
                dli_max: parseFloat(document.getElementById('dli_max').value),
                temp_min: parseFloat(document.getElementById('temp_min').value),
                temp_max: parseFloat(document.getElementById('temp_max').value),
            },
            mode: modeOptRadio.checked ? 'Optimization' : 'Custom',
            custom_pitch: parseFloat(document.getElementById('custom_pitch').value)
        };
    }

    async function runSimulation() {
        const inputs = getInputs();
        if (!inputs) {
            displayError("SVP, 3emmer kolchi les champs.");
            return;
        }
        
        welcomeMessage.style.display = 'none';
        resultsDashboard.style.display = 'none';
        errorMessageDiv.style.display = 'none';
        loadingIndicator.style.display = 'block';

        destroyActiveCharts();

        try {
            const response = await fetch('/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(inputs),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Erreur inconnue.');
            }
            
            displayResults(data, inputs);
            loadingIndicator.style.display = 'none';
            resultsDashboard.style.display = 'block';

        } catch (error) {
            console.error('La simulation a échoué:', error);
            displayError(`La simulation a échoué: ${error.message}`);
        }
    }

    function displayError(message) {
        loadingIndicator.style.display = 'none';
        errorMessageDiv.textContent = message;
        errorMessageDiv.style.display = 'block';
    }
    
    function destroyActiveCharts() {
        if (typeof Chart === 'undefined') return;
        Object.values(activeCharts).forEach(chart => chart.destroy());
        activeCharts = {};
    }

    function createChart(canvasId, type, data, options = {}) {
        if (typeof Chart === 'undefined') {
            console.error("Chart.js is not loaded, cannot create chart.");
            return;
        }
        const ctx = document.getElementById(canvasId).getContext('2d');
        activeCharts[canvasId] = new Chart(ctx, {
            type: type,
            data: data,
            options: options
        });
    }

    function displayResults(data, inputs) {
        const { results, graph_data, analysis_comments } = data;
        const { mode, custom_pitch } = inputs;

        const resultsTitle = document.getElementById('results_title');
        const keyMetricsDiv = document.getElementById('key_metrics');
        const commentsDiv = document.getElementById('analysis_comments');
        
        keyMetricsDiv.innerHTML = '';
        commentsDiv.innerHTML = '';

        if (mode === 'Optimization') {
            resultsTitle.textContent = currentLanguageStrings['opt_results_title'];
            addMetric(keyMetricsDiv, `✅ ${currentLanguageStrings['opt_pitch']}`, `${results.pitch.toFixed(1)} m`);
            addMetric(keyMetricsDiv, `💧 ${currentLanguageStrings['max_savings']}`, `${results.water_savings_percent.toFixed(2)} %`);
        } else {
            resultsTitle.textContent = `${currentLanguageStrings['single_results_title']} ${custom_pitch}m`;
            addMetric(keyMetricsDiv, `💧 ${currentLanguageStrings['water_savings']}`, `${results.water_savings.toFixed(2)} %`);
            addMetric(keyMetricsDiv, `☀️ ${currentLanguageStrings['dli_agri']}`, `${results.dli_agri.toFixed(2)} mol/m²/day`);
            addMetric(keyMetricsDiv, `   (${currentLanguageStrings['dli_open']})`, `${results.dli_open.toFixed(2)} mol/m²/day`);
            addMetric(keyMetricsDiv, `🌡️ ${currentLanguageStrings['peak_temp_agri']}`, `${results.peak_temp_agri.toFixed(2)} °C`);
            addMetric(keyMetricsDiv, `   (${currentLanguageStrings['peak_temp_open']})`, `${results.peak_temp_open.toFixed(2)} °C`);
        }
        
        if (analysis_comments && analysis_comments.length > 0) {
            analysis_comments.forEach(comment => {
                const commentBox = document.createElement('div');
                commentBox.className = `comment-${comment.tag}`;
                const title = document.createElement('div');
                title.className = 'comment-title';
                title.textContent = currentLanguageStrings[comment.title_key] || 'Analysis:';
                const text = document.createElement('p');
                text.textContent = comment.text;
                commentBox.appendChild(title);
                commentBox.appendChild(text);
                commentsDiv.appendChild(commentBox);
            });
        }

        const optChartContainer = document.getElementById('optimizationChart').parentElement;
        const otherCharts = ['irradianceChart', 'peakTempChart', 'monthlyWaterChart', 'cumulativeWaterChart'];

        if (mode === 'Optimization' && graph_data.optimization) {
            optChartContainer.style.display = 'block';
            otherCharts.forEach(id => document.getElementById(id).parentElement.style.display = 'block');
            document.getElementById('optimizationTitle').style.display = 'block';
            
            // [THE REAL FIX] Hna fin kan l'ghalat. Ghadi n7eydo l'plugin o nresmo b'tariqa sehla.
            const optData = graph_data.optimization;
            const optimalPitch = optData.optimal_pitch;
            // Nzid point f'dataset dyal l'optimal pitch bach yban l'khett
            optData.datasets.push({
                label: 'Optimal Pitch',
                data: [{x: optimalPitch, y: 0}, {x: optimalPitch, y: optData.max_savings}],
                borderColor: 'red',
                borderWidth: 2,
                borderDash: [6, 6],
                type: 'line', // Kanforciwh ykon line
                pointRadius: 0, // Bla n9ati
                fill: false
            });

            createChart('optimizationChart', 'line', optData, {
                scales: {
                    x: { type: 'linear', position: 'bottom' }
                }
            });

        } else {
            optChartContainer.style.display = 'none';
            document.getElementById('optimizationTitle').style.display = 'none';
            otherCharts.forEach(id => document.getElementById(id).parentElement.style.display = 'block');
        }

        if (graph_data && graph_data.irradiance) createChart('irradianceChart', 'line', graph_data.irradiance);
        if (graph_data && graph_data.peak_temp) {
            document.getElementById('peakTempTitle').textContent = graph_data.peak_temp.title;
            createChart('peakTempChart', 'line', graph_data.peak_temp);
        }
        if (graph_data && graph_data.monthly_water) createChart('monthlyWaterChart', 'bar', graph_data.monthly_water);
        if (graph_data && graph_data.cumulative_water) createChart('cumulativeWaterChart', 'line', graph_data.cumulative_water);
    }
    
    function addMetric(container, label, value) {
        const labelDiv = document.createElement('div');
        labelDiv.className = 'metric-label';
        labelDiv.textContent = label;
        const valueDiv = document.createElement('div');
        valueDiv.className = 'metric-value';
        valueDiv.textContent = value;
        container.appendChild(labelDiv);
        container.appendChild(valueDiv);
    }
});
