// static/script.js (v1.3 Final - With LIVE Dark Theme Chart Fix)

document.addEventListener('DOMContentLoaded', () => {
    // --- Dark Theme Logic ---
    const themeSwitch = document.getElementById('theme_switch');
    const currentTheme = localStorage.getItem('theme');

    if (currentTheme) {
        document.body.classList.add(currentTheme);
        if (currentTheme === 'dark-theme') {
            themeSwitch.checked = true;
        }
    }

    // --- [THE FIX IS HERE] ---
    // This listener now updates existing charts in real-time
    themeSwitch.addEventListener('change', function() {
        // 1. Toggle the theme on the body and save the preference
        document.body.classList.toggle('dark-theme', this.checked);
        localStorage.setItem('theme', this.checked ? 'dark-theme' : 'light-theme');
        
        // 2. Define the new colors based on the new theme
        const isDark = this.checked;
        const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
        const textColor = isDark ? '#e0e0e0' : '#333';

        // 3. Loop through all active charts and update their options
        for (const chartId in activeCharts) {
            const chart = activeCharts[chartId];
            
            // Update legend colors
            if (chart.options.plugins && chart.options.plugins.legend) {
                chart.options.plugins.legend.labels.color = textColor;
            }
            
            // Update scale (axes) colors
            if (chart.options.scales) {
                if(chart.options.scales.x) {
                    chart.options.scales.x.ticks.color = textColor;
                    chart.options.scales.x.grid.color = gridColor;
                }
                if(chart.options.scales.y) {
                    chart.options.scales.y.ticks.color = textColor;
                    chart.options.scales.y.grid.color = gridColor;
                }
            }
            
            // 4. Tell the chart to redraw itself with the new colors
            chart.update();
        }
    });


    // --- Get all other elements ---
    const runBtn = document.getElementById('run_simulation_btn');
    const modeOptRadio = document.getElementById('mode_opt');
    const modeCustomRadio = document.getElementById('mode_custom');
    const customPitchInput = document.getElementById('custom_pitch');
    const langSelect = document.getElementById('lang_select');
    const getLocationBtn = document.getElementById('get_location_name_btn');
    const openGmapsBtn = document.getElementById('open_gmaps_btn');
    const locationNameDisplay = document.getElementById('location_name_display');
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
    getLocationBtn.addEventListener('click', getLocationName);
    openGmapsBtn.addEventListener('click', openGoogleMaps);

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
            if (!response.ok) {
                throw new Error(`Could not load language file: ${response.statusText}`);
            }
            currentLanguageStrings = await response.json();
            
            document.querySelectorAll('[data-lang-key]').forEach(elem => {
                const key = elem.getAttribute('data-lang-key');
                if (currentLanguageStrings[key]) {
                    if (elem.placeholder) {
                        elem.placeholder = currentLanguageStrings[key];
                    } else {
                        elem.textContent = currentLanguageStrings[key];
                    }
                }
            });
            document.getElementById('run_simulation_btn').textContent = currentLanguageStrings['run_simulation'];
        } catch (error) {
            console.error('Could not load language file:', error);
        }
    }

    function getInputs() {
        // This function is unchanged
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
            custom_pitch: parseFloat(document.getElementById('custom_pitch').value),
            lang: document.getElementById('lang_select').value
        };
    }

    async function runSimulation() {
        // This function is unchanged
        const inputs = getInputs();
        if (!inputs) {
            displayError("Please fill in all required fields.");
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
                throw new Error(data.error || 'Unknown error occurred.');
            }
            
            displayResults(data, inputs);
            
        } catch (error) {
            console.error('Simulation failed:', error);
            displayError(`Simulation failed: ${error.message}`);
        } finally {
            loadingIndicator.style.display = 'none';
        }
    }

    function displayError(message) {
        // This function is unchanged
        loadingIndicator.style.display = 'none';
        resultsDashboard.style.display = 'none';
        errorMessageDiv.textContent = message;
        errorMessageDiv.style.display = 'block';
    }
    
    function destroyActiveCharts() {
        // This function is unchanged
        if (typeof Chart === 'undefined') return;
        Object.values(activeCharts).forEach(chart => chart.destroy());
        activeCharts = {};
    }

    function createChart(canvasId, type, data, options = {}) {
        // This function sets the colors on INITIAL creation
        if (typeof Chart === 'undefined') {
            console.error("Chart.js is not loaded, cannot create chart.");
            return;
        }
        const ctx = document.getElementById(canvasId).getContext('2d');
        
        const isDark = document.body.classList.contains('dark-theme');
        const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
        const textColor = isDark ? '#e0e0e0' : '#333';

        const defaultOptions = {
            plugins: {
                legend: {
                    labels: { color: textColor }
                }
            },
            scales: {
                x: {
                    grid: { color: gridColor },
                    ticks: { color: textColor }
                },
                y: {
                    grid: { color: gridColor },
                    ticks: { color: textColor }
                }
            }
        };

        const mergedOptions = { ...defaultOptions, ...options };

        activeCharts[canvasId] = new Chart(ctx, {
            type: type,
            data: data,
            options: mergedOptions
        });
    }

    function displayResults(data, inputs) {
        // This function is unchanged
        resultsDashboard.style.display = 'block';
        const { results, graph_data, analysis_comments } = data;
        const { mode, custom_pitch } = inputs;

        const resultsTitle = document.getElementById('results_title');
        const keyMetricsDiv = document.getElementById('key_metrics');
        const commentsDiv = document.getElementById('analysis_comments');
        
        keyMetricsDiv.innerHTML = '';
        commentsDiv.innerHTML = '';

        if (mode === 'Optimization') {
            resultsTitle.textContent = currentLanguageStrings['opt_results_title'];
            addMetric(keyMetricsDiv, currentLanguageStrings['metric_opt_pitch'], `${results.pitch.toFixed(1)} m`);
            addMetric(keyMetricsDiv, currentLanguageStrings['metric_max_savings'], `${results.water_savings_percent.toFixed(2)} %`);
        } else {
            resultsTitle.textContent = `${currentLanguageStrings['single_results_title']} ${custom_pitch}m`;
            addMetric(keyMetricsDiv, currentLanguageStrings['metric_water_savings'], `${results.water_savings.toFixed(2)} %`);
            addMetric(keyMetricsDiv, currentLanguageStrings['metric_dli_agri'], `${results.dli_agri.toFixed(2)} mol/m²/day`);
            addMetric(keyMetricsDiv, currentLanguageStrings['metric_dli_open'], `${results.dli_open.toFixed(2)} mol/m²/day`);
            addMetric(keyMetricsDiv, currentLanguageStrings['metric_peak_temp_agri'], `${results.peak_temp_agri.toFixed(2)} °C`);
            addMetric(keyMetricsDiv, currentLanguageStrings['metric_peak_temp_open'], `${results.peak_temp_open.toFixed(2)} °C`);
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

        document.getElementById('optimizationTitle').textContent = currentLanguageStrings['graph_title_opt'];
        document.getElementById('irradianceTitle').textContent = currentLanguageStrings['graph_title_irradiance'];
        document.getElementById('monthlyWaterTitle').textContent = currentLanguageStrings['graph_title_monthly_water'];
        document.getElementById('cumulativeWaterTitle').textContent = currentLanguageStrings['graph_title_cumulative_water'];

        function translateDataset(dataset) {
            if (dataset.label_key) {
                let label = currentLanguageStrings[dataset.label_key] || dataset.label_key;
                if (dataset.pitch) {
                    label = label.replace('{pitch}', dataset.pitch);
                }
                dataset.label = label;
            }
        }
        
        for (const graphKey in graph_data) {
            if (graph_data[graphKey] && graph_data[graphKey].datasets) {
                graph_data[graphKey].datasets.forEach(translateDataset);
            }
        }
        
        if (graph_data.peak_temp && graph_data.peak_temp.title_key) {
            const titleWithDate = currentLanguageStrings[graph_data.peak_temp.title_key] || "Temperature on {date}";
            document.getElementById('peakTempTitle').textContent = titleWithDate.replace('{date}', graph_data.peak_temp.title_date);
        } else {
             document.getElementById('peakTempTitle').textContent = currentLanguageStrings['graph_title_peak_temp'];
        }

        const optChartContainer = document.getElementById('optimizationChart').parentElement;
        const otherCharts = ['irradianceChart', 'peakTempChart', 'monthlyWaterChart', 'cumulativeWaterChart'];

        if (mode === 'Optimization' && graph_data.optimization) {
            optChartContainer.style.display = 'block';
            otherCharts.forEach(id => document.getElementById(id).parentElement.style.display = 'block');
            document.getElementById('optimizationTitle').style.display = 'block';
            
            const optData = graph_data.optimization;
            const optimalPitch = optData.optimal_pitch;
            
            const optimalPitchDataset = {
                label_key: 'graph_legend_opt_pitch',
                data: [{x: optimalPitch, y: 0}, {x: optimalPitch, y: optData.max_savings}],
                borderColor: 'red', borderWidth: 2, borderDash: [6, 6],
                type: 'line', pointRadius: 0, fill: false
            };
            translateDataset(optimalPitchDataset);
            optData.datasets.push(optimalPitchDataset);

            createChart('optimizationChart', 'line', optData, { scales: { x: { type: 'linear', position: 'bottom', title: { display: true, text: 'Pitch (m)' } } } });

        } else {
            optChartContainer.style.display = 'none';
            document.getElementById('optimizationTitle').style.display = 'none';
            otherCharts.forEach(id => document.getElementById(id).parentElement.style.display = 'block');
        }

        if (graph_data && graph_data.irradiance) createChart('irradianceChart', 'line', graph_data.irradiance);
        if (graph_data && graph_data.peak_temp) createChart('peakTempChart', 'line', graph_data.peak_temp);
        if (graph_data && graph_data.monthly_water) createChart('monthlyWaterChart', 'bar', graph_data.monthly_water);
        if (graph_data && graph_data.cumulative_water) createChart('cumulativeWaterChart', 'line', graph_data.cumulative_water);
    }
    
    function addMetric(container, label, value) {
        // This function is unchanged
        const labelDiv = document.createElement('div');
        labelDiv.className = 'metric-label';
        labelDiv.textContent = label;
        const valueDiv = document.createElement('div');
        valueDiv.className = 'metric-value';
        valueDiv.textContent = value;
        container.appendChild(labelDiv);
        container.appendChild(valueDiv);
    }
    
    async function getLocationName() {
        // This function is unchanged
        const lat = document.getElementById('lat').value;
        const lon = document.getElementById('lon').value;

        if (!lat || !lon) {
            locationNameDisplay.textContent = 'Please enter Latitude and Longitude first.';
            locationNameDisplay.style.color = 'red';
            return;
        }
        
        locationNameDisplay.textContent = 'Fetching name...';
        locationNameDisplay.style.color = '#555';

        try {
            const response = await fetch('/get_location_name', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lat: lat, lon: lon }),
            });
            const data = await response.json();
            if (!response.ok) { throw new Error(data.error || 'Unknown server error'); }
            locationNameDisplay.textContent = data.location_name;
            locationNameDisplay.style.color = '#005f73';

        } catch (error) {
            console.error('Failed to get location name:', error);
            locationNameDisplay.textContent = `Error: ${error.message}`;
            locationNameDisplay.style.color = 'red';
        }
    }

    function openGoogleMaps() {
        // This function is unchanged
        const lat = document.getElementById('lat').value;
        const lon = document.getElementById('lon').value;
        if (!lat || !lon) { alert('Please enter Latitude and Longitude first.'); return; }
        const url = `http://googleusercontent.com/maps/google.com/1{lat},${lon}`;
        window.open(url, '_blank');
    }
});