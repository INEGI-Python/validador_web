const input=document.querySelector('#fileInput')
const zone = document.querySelector('#dropzone');
const list = document.querySelector('#fileList');
const btn = document.querySelector('#validateBtn');
const form = document.querySelector('#uploadForm');
const statusBox = document.querySelector('#status');
const results = document.querySelector('#results');

document.querySelectorAll('#formatFile, #reprojectFile').forEach((fileInput) => {
    const dropzone = fileInput.closest('.file-dropzone');
    const selection = dropzone.querySelector('.file-selection');
    const form = fileInput.closest('form');
    const status = form.querySelector('.tool-status');
    const picker = form.querySelector('.gpkg-layer-picker');
    const options = picker.querySelector('.gpkg-layer-options');
    let layerRequest = 0;
    let dragDepth = 0;

    async function updateGpkgLayerOptions() {
        const requestId = ++layerRequest;
        const file = [...fileInput.files].find((item) => item.name.toLowerCase().endsWith('.gpkg'));
        const button = form.querySelector('button[type="submit"]');
        options.replaceChildren();
        picker.hidden = !file;

        if (!file) {
            button.disabled = false;
            status.textContent = '';
            status.classList.remove('error');
            return;
        }

        button.disabled = true;
        status.classList.remove('error');
        status.textContent = 'Consultando las capas del GeoPackage…';

        try {
            const data = new FormData();
            data.append('file', file);
            const response = await fetch('/api/gpkg-layers', { method: 'POST', body: data });
            const payload = await response.json();
            if (!response.ok || !payload.ok) {
                throw new Error(payload.message || 'No se pudieron consultar las capas.');
            }
            if (requestId !== layerRequest) return;

            payload.layers.forEach((layerName) => {
                const label = document.createElement('label');
                label.className = 'gpkg-layer-option';
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.name = 'selectedLayers';
                checkbox.value = layerName;
                const name = document.createElement('span');
                name.textContent = layerName;
                label.append(checkbox, name);
                options.append(label);
            });
            status.textContent = payload.layers.length
                ? 'Marca las capas que deseas procesar.'
                : 'El GeoPackage no contiene capas.';
        } catch (error) {
            if (requestId !== layerRequest) return;
            status.classList.add('error');
            status.textContent = error.message || 'No se pudieron consultar las capas.';
            picker.hidden = true;
        } finally {
            if (requestId === layerRequest) button.disabled = false;
        }
    }

    fileInput.addEventListener('change', () => {
        selection.textContent = [...fileInput.files].map((file) => file.name).join(', ');
        updateGpkgLayerOptions();
    });

    dropzone.addEventListener('dragenter', (event) => {
        event.preventDefault();
        dragDepth += 1;
        dropzone.classList.add('drag');
    });

    dropzone.addEventListener('dragover', (event) => event.preventDefault());

    dropzone.addEventListener('dragleave', (event) => {
        event.preventDefault();
        dragDepth = Math.max(0, dragDepth - 1);
        if (!dragDepth) dropzone.classList.remove('drag');
    });

    dropzone.addEventListener('drop', (event) => {
        event.preventDefault();
        dragDepth = 0;
        dropzone.classList.remove('drag');
        fileInput.files = event.dataTransfer.files;
        fileInput.dispatchEvent(new Event('change', { bubbles: true }));
    });
});

$(document).ready(function() {
    $.get("/api/client-user", function(data) {
    $("#userBadge").text(`INEGI · ${data.username || 'Usuario'}`);
    });
    // Check if the browser supports drag and drop
    if (!('draggable' in document.createElement('span'))) {
        zone.classList.add('hidden');
        input.classList.remove('hidden');
    }
  document.querySelectorAll('.side-menu a').forEach(function(link){
        
    link.addEventListener('click',function(){
      document.querySelectorAll('#validador, #convertir-a-geoparquet, #reproyectar-capa, #configurar-reglas').forEach(function(section){
        section.hidden = section.id !== link.hash.slice(1);
      });

      document.querySelectorAll('.side-menu a').forEach(function(item){item.removeAttribute('aria-current')});
      link.setAttribute('aria-current','page');
    });
  });
  loadRuleConfiguration();

});



let selected=[];
function setFiles(files) {
    selected = [...files].filter((file) =>
        file.name.toLowerCase().endsWith('.parquet'),
    );
    list.innerHTML = selected
        .map(
            (file) =>
                `<div class="file"><strong>${file.name}</strong><span>${(
                    file.size / 1048576
                ).toFixed(1)} MB</span></div>`,
        )
        .join('');
    btn.disabled = !selected.length;
}

input.addEventListener('change', (event) => setFiles(event.target.files));

['dragenter', 'dragover'].forEach((eventName) =>
    zone.addEventListener(eventName, (event) => {
        event.preventDefault();
        zone.classList.add('drag');
    }),
);

['dragleave', 'drop'].forEach((eventName) =>
    zone.addEventListener(eventName, (event) => {
        event.preventDefault();
        zone.classList.remove('drag');
    }),
);

zone.addEventListener('drop', (event) => setFiles(event.dataTransfer.files));

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!selected.length) return;

    const data = new FormData();
    selected.forEach((file) => data.append('layers', file));
    btn.disabled = true;
    statusBox.classList.remove('hidden');
    statusBox.innerHTML = '<strong>Validando…</strong><p>El motor está cargando las capas y ejecutando sus reglas topológicas.</p>';
    results.classList.add('hidden');

    try {
        const response = await fetch('/api/validate', {
            method: 'POST',
            body: data,
        });
        const payload = await response.json();

        if (!response.ok || !payload.ok) {
            throw new Error(payload.message || 'No fue posible validar.');
        }

        render(payload);
    } catch (error) {
        statusBox.innerHTML = `<strong class="bad">No se completó la validación</strong><p>${error.message}</p>`;
    } finally {
        btn.disabled = false;
    }
});

function connectToolForm(formId, statusId, endpoint, progressMessage, successMessage) {
    const toolForm = document.querySelector(`#${formId}`);
    const toolStatus = document.querySelector(`#${statusId}`);
    const toolButton = toolForm.querySelector('button[type="submit"]');
    const fileInput = toolForm.querySelector('input[type="file"]');
    const layerPicker = toolForm.querySelector('.gpkg-layer-picker');

    toolForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const hasGeopackage = [...fileInput.files].some((file) =>
            file.name.toLowerCase().endsWith('.gpkg'),
        );
        if (hasGeopackage && !layerPicker.querySelector('input:checked')) {
            toolStatus.classList.add('error');
            const options = layerPicker.querySelector('.gpkg-layer-options');
            if (options.childElementCount) {
                toolStatus.textContent = 'Selecciona al menos una capa del GeoPackage.';
            } else if (!toolStatus.textContent) {
                toolStatus.textContent = 'No se pudieron cargar las capas del GeoPackage. Selecciona de nuevo el archivo.';
            }
            return;
        }
        if (!toolForm.reportValidity()) return;

        toolButton.disabled = true;
        toolStatus.classList.remove('error');
        toolStatus.textContent = progressMessage;

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                body: new FormData(toolForm),
            });
            if (!response.ok) {
                let message = `No se completó la operación (HTTP ${response.status}).`;
                try {
                    const payload = await response.json();
                    if (payload.message) message = payload.message;
                } catch {
                    // The server may return a non-JSON error page.
                }
                throw new Error(message);
            }

            const file = await response.blob();
            const disposition = response.headers.get('Content-Disposition') || '';
            const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
            const filename = filenameMatch ? filenameMatch[1] : 'capa-procesada';
            const url = URL.createObjectURL(file);
            const downloadLink = document.createElement('a');
            downloadLink.href = url;
            downloadLink.download = filename;
            document.body.appendChild(downloadLink);
            downloadLink.click();
            downloadLink.remove();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
            toolStatus.textContent = successMessage;
        } catch (error) {
            toolStatus.classList.add('error');
            toolStatus.textContent = error.message || 'No se pudo procesar la capa.';
        } finally {
            toolButton.disabled = false;
        }
    });
}

connectToolForm(
    'convertFormatForm',
    'convertStatus',
    '/api/convert',
    'Convirtiendo capa…',
    'Conversión terminada. La descarga ha comenzado.',
);
connectToolForm(
    'reprojectLayerForm',
    'reprojectStatus',
    '/api/reproject',
    'Reproyectando capa…',
    'Reproyección terminada. La descarga ha comenzado.',
);

const addLayerRulesForm = document.querySelector('#addLayerRulesForm');
addLayerRulesForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!addLayerRulesForm.reportValidity()) return;

    const selectedRules = [...document.querySelectorAll('.rule-option:checked')];
    if (!selectedRules.length) {
        setRulesStatus('Selecciona al menos una regla.', true);
        return;
    }

    const rules = selectedRules.map((checkbox) => {
        const option = checkbox.closest('.available-rule');
        return {
            method: checkbox.value,
            name: option.querySelector('[data-rule-name]').value.trim(),
            layers: option.querySelector('[data-rule-layers]').value
                .split(',')
                .map((layer) => layer.trim())
                .filter(Boolean),
            tolerance: option.querySelector('[data-rule-tolerance]').value,
            exceptions: option.querySelector('[data-rule-exceptions]').value.trim(),
        };
    });

    const button = document.querySelector('#saveLayerRules');
    button.disabled = true;
    setRulesStatus('Guardando configuración…');
    try {
        const response = await fetch('/api/rules', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                layer: document.querySelector('#ruleLayerName').value.trim(),
                rules,
            }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
            throw new Error(payload.message || 'No se pudo guardar la configuración.');
        }

        addLayerRulesForm.reset();
        await loadRuleConfiguration();
        setRulesStatus(`Se guardaron las reglas de ${payload.layer}.`);
    } catch (error) {
        setRulesStatus(error.message || 'No se pudo guardar la configuración.', true);
    } finally {
        button.disabled = false;
    }
});

async function loadRuleConfiguration() {
    const configuredRules = document.querySelector('#configuredRules');
    const availableRules = document.querySelector('#availableRules');
    configuredRules.textContent = 'Cargando reglas…';
    availableRules.replaceChildren();

    try {
        const response = await fetch('/api/rules');
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
            throw new Error(payload.message || 'No se pudieron cargar las reglas.');
        }

        renderConfiguredRules(payload.layers);
        renderAvailableRules(payload.methods);
    } catch (error) {
        configuredRules.textContent = error.message || 'No se pudieron cargar las reglas.';
    }
}

function renderConfiguredRules(layers) {
    const container = document.querySelector('#configuredRules');
    container.replaceChildren();
    const layerNames = Object.keys(layers).sort();
    if (!layerNames.length) {
        container.textContent = 'No hay capas con reglas configuradas.';
        return;
    }

    layerNames.forEach((layerName) => {
        const card = document.createElement('details');
        card.className = 'configured-layer';
        const summary = document.createElement('summary');
        const title = document.createElement('strong');
        title.textContent = layerName;
        const count = document.createElement('span');
        const entries = Object.entries(layers[layerName] || {});
        count.className = 'rule-count';
        count.textContent = `${entries.length} regla${entries.length === 1 ? '' : 's'}`;
        summary.append(title, count);
        card.append(summary);

        const list = document.createElement('ul');
        entries.forEach(([name, rule]) => {
            const item = document.createElement('li');
            const method = rule.metodo || (rule.funcion || '').replace(/^topo\./, '').split('(')[0];
            const details = [];
            if (rule.capas && rule.capas.length) details.push(`capas: ${rule.capas.join(', ')}`);
            if (rule.tolerancia !== undefined) details.push(`tolerancia: ${rule.tolerancia}`);
            if (rule.excepciones || rule.excepcion) details.push(`excepciones: ${rule.excepciones || rule.excepcion}`);
            const description = document.createElement('span');
            description.className = 'configured-rule-description';
            description.textContent = `${name} — ${method}${details.length ? ` (${details.join('; ')})` : ''}`;
            const deleteButton = document.createElement('button');
            deleteButton.className = 'delete-rule';
            deleteButton.type = 'button';
            deleteButton.textContent = 'Eliminar';
            deleteButton.setAttribute('aria-label', `Eliminar regla ${name} de ${layerName}`);
            deleteButton.addEventListener('click', () => removeConfiguredRule(layerName, name));
            item.append(description, deleteButton);
            list.append(item);
        });
        card.append(list);
        container.append(card);
    });
}

async function removeConfiguredRule(layerName, ruleName) {
    if (!window.confirm(`¿Eliminar la regla "${ruleName}" de "${layerName}"?`)) return;

    setRulesStatus('Eliminando regla…');
    try {
        const response = await fetch(
            `/api/rules/${encodeURIComponent(layerName)}/${encodeURIComponent(ruleName)}`,
            {method: 'DELETE'},
        );
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
            throw new Error(payload.message || 'No se pudo eliminar la regla.');
        }

        renderConfiguredRules(payload.layers);
        setRulesStatus(
            payload.layers[layerName]
                ? `Se eliminó la regla ${ruleName}.`
                : `Se eliminó la última regla y la capa ${layerName}.`,
        );
    } catch (error) {
        setRulesStatus(error.message || 'No se pudo eliminar la regla.', true);
    }
}

function renderAvailableRules(methods) {
    const container = document.querySelector('#availableRules');
    container.replaceChildren();
    methods.forEach(({method, name}) => {
        const card = document.createElement('div');
        card.className = 'available-rule';
        const heading = document.createElement('label');
        heading.className = 'rule-choice';
        const checkbox = document.createElement('input');
        checkbox.className = 'rule-option';
        checkbox.type = 'checkbox';
        checkbox.value = method;
        const title = document.createElement('strong');
        title.textContent = name;
        const methodName = document.createElement('span');
        methodName.textContent = method;
        heading.append(checkbox, title, methodName);

        const details = document.createElement('div');
        details.className = 'rule-details hidden';
        details.append(
            createRuleField('Nombre de regla', 'rule-name', name),
            createRuleField('Capas relacionadas (separadas por coma)', 'rule-layers', ''),
            createRuleField('Tolerancia', 'rule-tolerance', '', 'number'),
            createRuleField('Excepciones', 'rule-exceptions', ''),
        );
        card.append(heading, details);
        checkbox.addEventListener('change', () => {
            details.classList.toggle('hidden', !checkbox.checked);
            details.querySelector('[data-rule-name]').required = checkbox.checked;
        });
        container.append(card);
    });
}

function createRuleField(labelText, fieldName, value, type = 'text') {
    const label = document.createElement('label');
    label.className = 'tool-field';
    label.append(document.createTextNode(labelText));
    const input = document.createElement('input');
    input.type = type;
    input.setAttribute(`data-${fieldName}`, '');
    input.value = value;
    if (type === 'number') {
        input.min = '0';
        input.step = 'any';
    }
    label.append(input);
    return label;
}

function setRulesStatus(message, isError = false) {
    const status = document.querySelector('#rulesStatus');
    status.textContent = message;
    status.classList.toggle('error', isError);
}

function render(payload) {
    let $status = $("#status");
    $status.removeClass("hidden");

    let $resultados = $("<div>").html("Validación Terminada").addClass("resultados");
    let $totales = $("<div>").html(`Trabajo ${payload.job_id.slice(0, 8)} · ${payload.layers.length} capa(s)`).addClass("totales");
    let $descargar = $("<div>").html($("<a>").attr("href", `/api/download/${payload.job_id}/${payload.layers[0]}`).text("⇩")).append("Descargar").addClass("descargar");
    $status.html($resultados).append($totales).append($descargar);

    const totalRules = payload.results.reduce(
        (total, result) => total + result.rule_count,
        0,
    );
    const totalErrors = payload.results.reduce(
        (total, result) => total + result.error_count,
        0,
    );
    
    $resumen = $("<div>").addClass("summary");
    $resumen.append($("<div>").addClass("metric").html(`<span>Capas</span><strong>${payload.results.length}</strong>`));
    $resumen.append($("<div>").addClass("metric").html(`<span>Reglas ejecutadas</span><strong>${totalRules}</strong>`));
    $resumen.append($("<div>").addClass("metric").html(`<span>Errores detectados</span><strong class="${totalErrors ? 'bad' : 'ok'}">${totalErrors}</strong>`));
    $results = $("<div>").addClass("results").append($resumen);

    payload.results.forEach((layer) => {
        $layerHeader = $("<h2>").text(layer.layer);
        $layerInfo = $("<p>").html(`${layer.rule_count} reglas · ${layer.error_count} errores`);
        $layerRules = $("<div>");
        layer.rules.forEach((rule) => {
            $ruleDiv = $("<div>").addClass("rule");
            $ruleDiv.append($("<strong>").text(rule.name));
            $ruleDiv.append($("<span>").text(rule.time || '—'));
            $ruleDiv.append($("<span>").addClass(rule.count ? 'bad' : 'ok').text(`${rule.count} error(es)`));
            $layerRules.append($ruleDiv);
        });
        (layer.execution_errors || []).forEach((error) => {
            $errorDiv = $("<div>").addClass("rule bad");
            $errorDiv.append($("<strong>").text(error.rule));
            $errorDiv.append($("<span>").text(error.message));
            $layerRules.append($errorDiv);
        });
        $results.append($layerHeader, $layerInfo, $layerRules);
    });

    $("#results").html($results).removeClass("hidden");
}       

