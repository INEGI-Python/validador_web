const input=document.querySelector('#fileInput')
const zone = document.querySelector('#dropzone');
const list = document.querySelector('#fileList');
const btn = document.querySelector('#validateBtn');
const form = document.querySelector('#uploadForm');
const statusBox = document.querySelector('#status');
const results = document.querySelector('#results');

$(document).ready(function() {
    // Check if the browser supports drag and drop
    if (!('draggable' in document.createElement('span'))) {
        zone.classList.add('hidden');
        input.classList.remove('hidden');
    }
  document.querySelectorAll('.side-menu a').forEach(function(link){
        
    link.addEventListener('click',function(e){
      $("section").hide();
      $(`${$(e)[0].target.hash}`).show();

      document.querySelectorAll('.side-menu a').forEach(function(item){item.removeAttribute('aria-current')});
      link.setAttribute('aria-current','page');
    });
  });
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

    toolForm.addEventListener('submit', async (event) => {
        event.preventDefault();
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
