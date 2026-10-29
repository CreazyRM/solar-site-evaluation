/* Browser-local banner preferences. Publishing shared defaults remains a Site edit. */
(()=>{
 const key='solar-atlas:banner-style:v1';
 const defaults={title:'Ontario Solar Site Assessment',x:4,y:15,size:42,shade:85,image:48};
 const ranges={x:[0,70],y:[0,70],size:[24,64],shade:[0,85],image:[0,100]};
 const byId=id=>document.getElementById(id),banner=byId('welcome'),title=byId('solar-hero-title');
 byId('banner-editor-close').addEventListener('click',()=>{byId('banner-customizer').open=false;byId('banner-customizer').querySelector('summary').focus();});
 document.addEventListener('keydown',event=>{if(event.key==='Escape')byId('banner-customizer').open=false;});
 let state={...defaults};
 function clean(value){const result={...defaults};if(!value||typeof value!=='object')return result;if(typeof value.title==='string'&&value.title.trim())result.title=value.title.trim().slice(0,80);for(const[k,[min,max]]of Object.entries(ranges))if(typeof value[k]==='number'&&Number.isFinite(value[k]))result[k]=Math.round(Math.max(min,Math.min(max,value[k])));return result;}
 function load(){try{return clean(JSON.parse(localStorage.getItem(key)));}catch{return{...defaults};}}
 function apply(){title.textContent=state.title;banner.style.setProperty('--hero-title-x',state.x+'%');banner.style.setProperty('--hero-title-y',state.y+'%');banner.style.setProperty('--hero-title-size',state.size+'px');banner.style.setProperty('--hero-shade',state.shade/100);banner.style.setProperty('--hero-image-y',state.image+'%');byId('banner-title-input').value=state.title;for(const k of Object.keys(ranges)){byId('banner-'+k).value=state[k];byId('banner-'+k+'-value').textContent=state[k]+(k==='size'?' px':'%');}}
 function status(text){byId('banner-editor-status').textContent=text;}
 state=load();apply();
 for(const k of Object.keys(ranges))byId('banner-'+k).addEventListener('input',event=>{state[k]=Number(event.target.value);apply();status('Live preview. Save in this browser to keep these settings.');});
 byId('banner-title-input').addEventListener('input',event=>{state.title=event.target.value.slice(0,80);title.textContent=state.title;status('Live preview. Save in this browser to keep these settings.');});
 byId('banner-save').addEventListener('click',()=>{if(!state.title.trim()){status('Enter a title before saving.');return;}try{state=clean(state);localStorage.setItem(key,JSON.stringify(state));apply();status('Saved in this browser. Other visitors still see the published layout.');}catch{status('Browser storage is unavailable. Your preview has not been saved.');}});
 byId('banner-copy').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(JSON.stringify({bannerStyle:clean(state)},null,2));status('Settings copied. Send them to your site editor to publish this layout for everyone.');}catch{status('Clipboard access is unavailable. Save in this browser to keep this preview.');}});
 byId('banner-reset').addEventListener('click',()=>{state={...defaults};apply();try{localStorage.removeItem(key);status('Published defaults restored.');}catch{status('Preview reset. Browser storage could not be cleared.');}});
 window.addEventListener('storage',event=>{if(event.key===key){state=load();apply();status('Settings refreshed from another tab.');}});
})();
