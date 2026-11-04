const input=document.querySelector('#fileInput'),zone=document.querySelector('#dropzone'),list=document.querySelector('#fileList'),btn=document.querySelector('#validateBtn'),form=document.querySelector('#uploadForm'),statusBox=document.querySelector('#status'),results=document.querySelector('#results');
let selected=[];
function setFiles(files){selected=[...files].filter(f=>f.name.toLowerCase().endsWith('.parquet'));list.innerHTML=selected.map(f=>`<div class="file"><strong>${f.name}</strong><span>${(f.size/1048576).toFixed(1)} MB</span></div>`).join('');btn.disabled=!selected.length;}
input.addEventListener('change',e=>setFiles(e.target.files));
['dragenter','dragover'].forEach(ev=>zone.addEventListener(ev,e=>{e.preventDefault();zone.classList.add('drag')}));
['dragleave','drop'].forEach(ev=>zone.addEventListener(ev,e=>{e.preventDefault();zone.classList.remove('drag')}));
zone.addEventListener('drop',e=>setFiles(e.dataTransfer.files));
form.addEventListener('submit',async e=>{e.preventDefault(); if(!selected.length)return;
    const data=new FormData();
    selected.forEach(f=>data.append('layers',f));
    btn.disabled=true;
    statusBox.classList.remove('hidden');
    statusBox.innerHTML='<strong>Validando…</strong><p>El motor está cargando las capas y ejecutando sus reglas topológicas.</p>';
    results.classList.add('hidden');
    try{
        const r=await fetch('/api/validate',{method:'POST',body:data});
        const payload=await r.json();if(!r.ok||!payload.ok)
            throw new Error(payload.message||'No fue posible validar.');render(payload);}catch(err){statusBox.innerHTML=`<strong class="bad">No se completó la validación</strong><p>${err.message}</p>`;}finally{btn.disabled=false;}});
function render(p){statusBox.innerHTML=`<strong>Validación terminada</strong><p>Trabajo ${p.job_id.slice(0,8)} · ${p.layers.length} capa(s)</p>`;const totalRules=p.results.reduce((a,x)=>a+x.rule_count,0),totalErrors=p.results.reduce((a,x)=>a+x.error_count,0);results.classList.remove('hidden');results.innerHTML=`<div class="summary"><div class="metric"><span>Capas</span><strong>${p.results.length}</strong></div><div class="metric"><span>Reglas ejecutadas</span><strong>${totalRules}</strong></div><div class="metric"><span>Errores detectados</span><strong class="${totalErrors?'bad':'ok'}">${totalErrors}</strong></div></div>`+p.results.map(layer=>`<h2>${layer.layer}</h2><p>${layer.rule_count} reglas · ${layer.error_count} errores</p>${layer.rules.map(r=>`<div class="rule"><strong>${r.name}</strong><span>${r.time||'—'}</span><span class="${r.count?'bad':'ok'}">${r.count} error(es)</span></div>`).join('')}${(layer.execution_errors||[]).map(x=>`<div class="rule bad"><strong>${x.rule}</strong><span>${x.message}</span></div>`).join('')}`).join('');}
