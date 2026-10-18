/* The server remains authoritative: the browser only presents eligible modules. */
(function(){
 const f=document.getElementById('create-offering');
 const floatForm=document.getElementById('float-form');
 async function load(url){const r=await fetch(url,{credentials:'same-origin'});if(!r.ok)throw Error('Unable to load eligible modules');return r.json()}
 function option(select,value,label){const o=document.createElement('option');o.value=value;o.textContent=label;select.appendChild(o)}
 function setMessage(id,message){const el=document.getElementById(id);if(el)el.textContent=message}
 async function refreshOffering(){
  if(!f)return;
  const p=new URLSearchParams({programme:f.elements.programme.value,academic_year:f.elements.academic_year.value,intake:f.elements.intake.value,session_type:f.elements.session_type.value,module_block:f.elements.module.value});
  const sel=f.elements.code;sel.replaceChildren();option(sel,'','Select a floated module');f.querySelector('button[type=submit]').disabled=true;
  if([...p.values()].some(x=>!x.trim())){setMessage('offering-message','Enter the academic year, intake, session and module block to view floated modules.');return}
  try{
   const data=await load('/api/floated-modules?'+p.toString());
   data.floated_modules.forEach(m=>option(sel,m.module_code,m.module_code+' — '+m.module_title));
   setMessage('offering-message',data.count?`${data.count} eligible floated module(s).`:'No floated modules match these settings. Float a module first.');
   sel.dispatchEvent(new Event('change'));
  }catch(e){setMessage('offering-message',e.message)}
 }
 async function refreshCatalogue(){
  if(!floatForm)return;
  const sel=floatForm.elements.module_code;sel.replaceChildren();option(sel,'','Select approved 2023 curriculum module');
  try{const data=await load('/api/curriculum-catalogue?programme='+encodeURIComponent(floatForm.elements.programme.value));data.modules.forEach(m=>option(sel,m.module_code,m.module_code+' — '+m.module_title));setMessage('float-message',`${data.count} approved 2023 curriculum entries available.`)}catch(e){setMessage('float-message',e.message)}
 }
 if(f){['programme','academic_year','intake','session_type','module'].forEach(n=>f.elements[n].addEventListener('change',refreshOffering));f.elements.code.addEventListener('change',async()=>{
  const code=f.elements.code.value;f.querySelector('button[type=submit]').disabled=!code;
  if(!code){f.elements.title.value='';return}
  try{const data=await load('/api/floated-modules?'+new URLSearchParams({programme:f.elements.programme.value,academic_year:f.elements.academic_year.value,intake:f.elements.intake.value,session_type:f.elements.session_type.value,module_block:f.elements.module.value}));const m=data.floated_modules.find(x=>x.module_code===code);f.elements.title.value=m?m.module_title:''}catch(e){setMessage('offering-message',e.message)}
 });refreshOffering()}
 if(floatForm){floatForm.elements.programme.addEventListener('change',refreshCatalogue);refreshCatalogue();floatForm.addEventListener('submit',async e=>{
  e.preventDefault();const data=new FormData(floatForm);const resp=await fetch('/api/float-module',{method:'POST',body:data,credentials:'same-origin'});const result=await resp.json();setMessage('float-message',resp.ok?`Floated ${result.module_code} successfully.`:(result.detail||'Unable to float module'));if(resp.ok)refreshOffering();
 })}
})();
