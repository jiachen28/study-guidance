'use strict';
const $=id=>document.getElementById(id);
const show=(id,visible)=>$(id).classList.toggle('hidden',!visible);
const put=(id,text)=>$(id).textContent=text ?? '';
const task=$('task');
task.addEventListener('input',()=>put('count',`${task.value.length} / 2500`));
for(const b of document.querySelectorAll('.example')){
  b.addEventListener('click',()=>{task.value=b.dataset.text;task.dispatchEvent(new Event('input'));task.focus();});
}
$('reset').addEventListener('click',()=>{task.value='';task.dispatchEvent(new Event('input'));show('result',false);show('empty',true);task.focus();});
function lines(id,items){const root=$(id);root.replaceChildren();for(const item of items){const li=document.createElement('li');li.textContent=item;root.appendChild(li);}}
function render(r){
  put('recommendation',r.tool.title);put('toolDescription',r.tool.description);put('category',r.category);
  put('riskLevel',r.risk.level);put('riskMessage',r.risk.reasons.join('. '));
  $('riskLevel').parentElement.parentElement.classList.toggle('danger',r.risk.prohibited || r.risk.level==='Not suitable');
  lines('tools',r.tool.examples);lines('steps',r.tool.steps);
  for(const x of ['explanation','verification','limitations'])put(x,r.details[x]);
  put('decisionSource',r.source);put('referenceCount',`(${r.references.length})`);
  const container=$('references');container.replaceChildren();
  for(const ref of r.references){
    const wrapper=document.createElement('div');wrapper.className='references-item';
    const a=document.createElement('a');a.href=ref.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=`${ref.id} · ${ref.title} (${ref.publisher})`;
    const p=document.createElement('p');p.textContent=ref.note;
    wrapper.append(a,p);container.appendChild(wrapper);
  }
}
$('taskForm').addEventListener('submit',async(event)=>{
  event.preventDefault();
  if(!task.value.trim())return;
  $('submit').disabled=true;put('btnText','Processing…');
  for(const id of ['empty','result','error'])show(id,false);show('loading',true);
  try{
    const reply=await fetch('/api/advise',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:task.value})});
    const data=await reply.json();if(!reply.ok)throw Error(data.error||'Request failed');
    render(data);show('result',true);
  }catch(err){put('error',`${err.message}. Check the local server and try again.`);show('error',true);}
  finally{show('loading',false);$('submit').disabled=false;put('btnText','Get recommendation');}
});
