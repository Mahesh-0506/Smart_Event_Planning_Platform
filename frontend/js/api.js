const API='/api';
async function api(path,options={}){const r=await fetch(API+path,{headers:{'Content-Type':'application/json',...(options.headers||{})},...options});let d={};try{d=await r.json()}catch{}if(!r.ok)throw new Error(d.error||`Request failed (${r.status})`);return d}
const get=p=>api(p); const post=(p,b)=>api(p,{method:'POST',body:JSON.stringify(b)}); const put=(p,b)=>api(p,{method:'PUT',body:JSON.stringify(b)}); const del=p=>api(p,{method:'DELETE'});
function money(v){return new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(Number(v||0))}
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function toast(msg){const e=document.querySelector('#toast');if(e){e.textContent=msg;e.style.display='block';setTimeout(()=>e.style.display='none',2600)}}
function activeNav(){const page=location.pathname.split('/').pop()||'index.html';document.querySelectorAll('.nav a').forEach(a=>a.classList.toggle('active',a.getAttribute('href')===page))}
