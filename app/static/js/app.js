const input=document.querySelector('#fileInput')
const zone = document.querySelector('#dropzone');
const list = document.querySelector('#fileList');
const btn = document.querySelector('#validateBtn');
const form = document.querySelector('#uploadForm');
const statusBox = document.querySelector('#status');
const results = document.querySelector('#results');

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

function render(payload) {
    let $status = $("#status");
    $status.removeClass("hidden");

    let $resultados = $("<div>").html("Validación Terminada").addClass("resultados");
    let $totales = $("<div>").html(`Trabajo ${payload.job_id.slice(0, 8)} · ${payload.layers.length} capa(s)`).addClass("totales");
    let $descargar = $("<div>").html($("<a>").attr("href", `/api/download/${payload.job_id}`).text("Descargar errores")).addClass("descargar");
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

/*
    statusBox.innerHTML = `<strong>Validación terminada </strong><p>Trabajo ${payload.job_id.slice(0, 8)} · ${payload.layers.length} capa(s)</p>`;
    statusBox.appendChild(document.createElement('a').setAttribute('href', `/api/download/${payload.job_id}`).setProperty('textContent', 'Descargar errores'));
    const totalRules = payload.results.reduce(
        (total, result) => total + result.rule_count,
        0,
    );
    const totalErrors = payload.results.reduce(
        (total, result) => total + result.error_count,
        0,
    );
    

    results.classList.remove('hidden');
    results.innerHTML =
        `<div class="summary">
            <div class="metric"><span>Capas</span><strong>${payload.results.length}</strong></div>
            <div class="metric"><span>Reglas ejecutadas</span><strong>${totalRules}</strong></div>
            <div class="metric"><span>Errores detectados</span><strong class="${totalErrors ? 'bad' : 'ok'}">${totalErrors}</strong></div>
        </div>` +
        payload.results
            .map(
                (layer) =>
                    `<h2>${layer.layer}</h2>
                    <p>${layer.rule_count} reglas · ${layer.error_count} errores</p>
                  
                    ${layer.rules
                        .map(
                            (rule) =>
                                `<div class="rule">
                                    <strong>${rule.name}</strong>
                                    <span>${rule.time || '—'}</span>
                                    <span class="${rule.count ? 'bad' : 'ok'}">${rule.count} error(es)</span>
                                </div>`,
                        )
                        .join('')}
                    ${(layer.execution_errors || [])
                        .map(
                            (error) =>
                                `<div class="rule bad"><strong>${error.rule}</strong><span>${error.message}</span></div>`,
                        )
                        .join('')}`,
            )
            .join('');


}*/


