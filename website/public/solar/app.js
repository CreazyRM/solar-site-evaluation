/* Presentation of the separately dated saved example report. */
const data = window.SOLAR_REPORT;
const $ = (id) => document.getElementById(id);
const deletionKey = 'solar-atlas:deleted-saved-highway6:v1';
let savedReportDeleted = false;
try { savedReportDeleted = localStorage.getItem(deletionKey) === 'true'; } catch { /* Storage errors are reported if a change is attempted. */ }
function updateReportLibrary() {
  $('open-example').hidden = savedReportDeleted;
  $('delete-saved-report').hidden = savedReportDeleted;
  $('try-example').hidden = savedReportDeleted;
  $('library-empty').hidden = !savedReportDeleted;
  $('saved-count').textContent = savedReportDeleted ? '0 saved assessments' : '1 saved assessment';
  document.querySelector('.nav-count').textContent = savedReportDeleted ? '0' : '1';
}
function persistReportDeletion(deleted) {
  try {
    if (deleted) localStorage.setItem(deletionKey, 'true'); else localStorage.removeItem(deletionKey);
  } catch {
    $('library-feedback').textContent = 'Browser storage is unavailable. The report was not changed.';
    return false;
  }
  savedReportDeleted = deleted; updateReportLibrary(); return true;
}
const escapeText = (value) => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const canonical = (text) => text.toLowerCase().replace(/geogrian/g, 'georgian').replace(/\bhighway\b/g, 'hwy').replace(/\bontario\b/g,'on').replace(/[^a-z0-9]/g, '');
function matches(address) {
  const value = canonical(address);
  return data.aliases.some(alias => canonical(alias) === value);
}
function showOverview(scroll = true) {
  $('welcome').hidden = false; $('library').hidden = false; $('report').hidden = true;
  document.querySelectorAll('.report-nav').forEach(el => el.hidden = true);
  $('overview-nav').classList.add('active'); $('library-nav').classList.remove('active');

  if (scroll) window.scrollTo({top:0, behavior:'smooth'});
}
function showReport() {
  if (savedReportDeleted) { showOverview(); return; }
  $('welcome').hidden = true; $('library').hidden = true; $('report').hidden = false;
  document.querySelectorAll('.report-nav').forEach(el => el.hidden = false);
  $('overview-nav').classList.remove('active'); $('library-nav').classList.add('active');

  $('address').value = data.address; $('clear-address').hidden = false; $('search-status').hidden = true;
  $('report').scrollIntoView({behavior:'smooth', block:'start'});
  history.replaceState(null, '', '#report');window.dispatchEvent(new Event('solar:saved-report-open'));
}
$('address').addEventListener('input',() => { $('address').setCustomValidity(''); $('clear-address').hidden = !$('address').value; });
$('clear-address').addEventListener('click',() => { $('address').value=''; $('clear-address').hidden=true; $('address').focus(); });
$('try-example').addEventListener('click',showReport); $('open-example').addEventListener('click',showReport);
$('back-overview').addEventListener('click',() => {showOverview(); history.replaceState(null,'',location.pathname);});
$('overview-nav').addEventListener('click',() => {showOverview(); history.replaceState(null,'',location.pathname);});
$('home-brand').addEventListener('click',e => {e.preventDefault();showOverview();history.replaceState(null,'',location.pathname);});
$('library-nav').addEventListener('click',() => {showOverview(false);$('library').scrollIntoView({behavior:'smooth'});$('overview-nav').classList.remove('active');$('library-nav').classList.add('active');});
$('metrics-grid').innerHTML = data.metrics.map(m=>`<div class="metric"><span class="metric-label">${escapeText(m.label)}</span><strong>${escapeText(m.value)} <small>${escapeText(m.unit)}</small></strong><p>${escapeText(m.note)}</p></div>`).join('');
$('report-sections').innerHTML = data.sections.map(s=>`<section class="detail-section" id="${escapeText(s.id)}"><div class="detail-header"><span class="section-number">${escapeText(s.number)}</span><div><h2>${escapeText(s.title)}</h2></div><span class="section-status ${s.review?'review':''}">${escapeText(s.status)}</span></div><p class="section-intro">${escapeText(s.intro)}</p><dl class="facts">${s.facts.map(f=>`<div class="fact"><dt>${escapeText(f[0])}</dt><dd>${escapeText(f[1])}</dd></div>`).join('')}</dl>${s.table?`<table class="capacity-table"><caption class="sr-only">Historical candidate feeder capacity tests</caption><thead><tr><th>Candidate feeder</th><th>2,000 kW</th><th>Highest tested pass</th><th>Next tested fail</th></tr></thead><tbody>${s.table.map(r=>`<tr>${r.map(c=>`<td>${escapeText(c)}</td>`).join('')}</tr>`).join('')}</tbody></table>`:''}<div class="callout">${escapeText(s.callout)}</div><details><summary>Method, source dates & limitations</summary><p>${escapeText(s.method)}</p><div class="source-links">${s.sources.map(i=>`<a href="${escapeText(data.sources[i].url)}" target="_blank" rel="noopener noreferrer">${escapeText(data.sources[i].name)} ↗</a>`).join('')}</div></details></section>`).join('');
$('sources-list').innerHTML = data.sources.map(s=>`<div class="source-row"><div><strong>${escapeText(s.name)}</strong><small>${escapeText(s.note)}</small></div><a href="${escapeText(s.url)}" target="_blank" rel="noopener noreferrer">View source ↗</a></div>`).join('');
function toggleReportExpansion(force){const classes=document.querySelector('#report .map-panel').classList;const expanded=force===undefined?classes.toggle('expanded-report-map'):classes.toggle('expanded-report-map',force);$('expand-map').textContent=expanded?'Close expanded map ×':'Expand map ↗';$('expand-map').setAttribute('aria-expanded',String(expanded));window.dispatchEvent(new Event('solar:map-resize'));}
$('expand-map').addEventListener('click',()=>toggleReportExpansion());
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&document.querySelector('#report .map-panel').classList.contains('expanded-report-map'))toggleReportExpansion(false);});
$('print-report').addEventListener('click',()=>window.print());
$('download-data').addEventListener('click',()=>{const blob=new Blob([JSON.stringify(data.structured,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='019471-highway-6-assessment.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
function requestReportDeletion() {
  $('delete-report-dialog').showModal();
  $('cancel-report-delete').focus();
}
$('delete-saved-report').addEventListener('click', requestReportDeletion);
$('delete-open-report').addEventListener('click', requestReportDeletion);
$('cancel-report-delete').addEventListener('click', () => $('delete-report-dialog').close());
$('confirm-report-delete').addEventListener('click', () => {
  if (!persistReportDeletion(true)) { $('delete-report-dialog').close(); return; }
  $('delete-report-dialog').close();
  $('boundary-workspace').hidden = true; $('live-report').hidden = true;
  showOverview(false); history.replaceState(null, '', location.pathname);
  $('library-feedback').textContent = 'Report deleted from this browser. You can undo below.';
  $('restore-saved-report').focus();
});
$('restore-saved-report').addEventListener('click', () => {
  if (persistReportDeletion(false)) { $('library-feedback').textContent = 'Report restored.'; $('open-example').focus(); }
});
updateReportLibrary();
if(location.hash==='#report')showReport();
