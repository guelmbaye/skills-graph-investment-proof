'use strict';
const $ = (id) => document.getElementById(id);
const slider = $('capacity');
let nonce = 0;
const names = { 'CLOUD-ENG':'Cloud security engineer', 'SOC-ANALYST':'SOC analyst', 'DATA-ANALYST':'Data analyst' };
const kinds = ['Resource','Program','Skill','Occupation'];
const colors = { Resource:'#bba9fa',Program:'#63baf4',Skill:'#e3b86e',Occupation:'#8ce6c7' };
const esc = s => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function signed(v){return v===0?'±0':v>0?'+'+v:String(v)}
function text(id,s){$(id).textContent=s}
function empty(el){while(el.firstChild)el.removeChild(el.firstChild)}
function svg(tag,attrs){ const n=document.createElementNS('http://www.w3.org/2000/svg',tag); for(const [k,v] of Object.entries(attrs||{}))n.setAttribute(k,String(v));return n }
function nodeLayout(nodes){
  const by={};for(const k of kinds)by[k]=nodes.filter(n=>n.kind===k).sort((a,b)=>a.id.localeCompare(b.id));
  const xs=[94,345,598,863], rows={};
  kinds.forEach((kind,i)=>{const group=by[kind],count=group.length;group.forEach((n,j)=>{rows[n.id]={x:xs[i],y:110+(j+(count===1?0:0))*(250/Math.max(1,count-1)),n};if(count===1)rows[n.id].y=240})});
  return rows;
}
function renderGraph(network,cap){
  const root=$('graph');empty(root);
  const coords=nodeLayout(network.nodes);
  // Network preview is derived exclusively from graph_model read with Cypher.
  for(const e of network.edges){const a=coords[e.from],b=coords[e.to];if(!a||!b)continue;
    const path=svg('path',{d:`M ${a.x+72} ${a.y} C ${a.x+121} ${a.y}, ${b.x-117} ${b.y}, ${b.x-72} ${b.y}`,
      fill:'none',stroke:'#526881','stroke-width':'1.7','stroke-opacity':'.72'});
    root.appendChild(path);
  }
  for(const kind of kinds){
    const x={Resource:94,Program:345,Skill:598,Occupation:863}[kind];
    const title=svg('text',{x,y:34,'text-anchor':'middle',fill:'#96aabe','font-size':14,'font-weight':700,'letter-spacing':1});title.textContent=kind.toUpperCase();root.appendChild(title);
  }
  for(const n of network.nodes){const p=coords[n.id],g=svg('g',{});let fill='#172a40',stroke=colors[n.kind];
    if(n.affected){stroke='#ff8994';fill='#4e2739'}
    if(n.id==='LAB-SOC'){stroke='#7dece2';fill='#18454a'}
    const r=svg('rect',{x:p.x-72,y:p.y-25,width:144,height:50,rx:11,fill,stroke,'stroke-width':n.affected?2.7:1.5});g.appendChild(r);
    const label=svg('text',{x:p.x,y:p.y-4,'text-anchor':'middle','font-size':12,'font-weight':700,fill:'#f5f8ff'});
    label.textContent=n.id;g.appendChild(label);
    const subtitle=svg('text',{x:p.x,y:p.y+13,'text-anchor':'middle','font-size':10,fill:'#b6c6d8'});
    subtitle.textContent=n.label.length>22?n.label.slice(0,20)+'…':n.label;g.appendChild(subtitle);
    const tooltip=svg('title',{});tooltip.textContent=`${n.kind}: ${n.label}${n.affected?' — measured proxy change':''}`;g.appendChild(tooltip);root.appendChild(g);
  }
}
function renderPrograms(data){const wrap=$('programs');empty(wrap);
 for(const p of data.programs){const el=document.createElement('div');el.className='program';
  el.innerHTML=`<header><strong>${esc(p.name)}</strong><span class="delta ${p.delta<0?'negative':p.delta>0?'positive':''}">${signed(p.delta)}</span></header>
    <div class="bar"><span></span></div>
    <div class="sub"><span>Baseline ${p.a} / ${p.planned}</span><span>Scenario ${p.b} / ${p.planned}</span></div>`;
  el.querySelector(".bar > span").style.width = `${p.planned>0?Math.min(100,Math.max(0,100*p.b/p.planned)):0}%`;
  wrap.appendChild(el);
 }
}
function renderRoles(data){const wrap=$('roles');empty(wrap);
  for(const r of data.occupation_proxies){const el=document.createElement('div');el.className='role';
  const change=r.delta_b_minus_a;el.innerHTML=`<span class="job">${esc(names[r.occupation]||r.occupation)}</span>
      <span class="amount">${r.bottleneck_proxy_a} → ${r.bottleneck_proxy_b}</span>
      <span class="change ${change<0?'down':change>0?'up':''}">${signed(change)}</span>`;
  el.title=`Bottleneck of required-skill seat opportunities, NOT number of graduates. Required skills: ${r.required_skills.join(', ')}`;
  // Role rows contain no progress bar. The previous .bar query was null and
  // aborted UI rendering, incorrectly suggesting the Relate backend had failed.
  wrap.appendChild(el);
 }}
function render(data){
  text('db-version',data.relate_version);
  text('seats-a',data.feasible_a);text('seats-b',data.feasible_b);text('seats-r',data.feasible_restored);
  const change=data.feasible_b-data.feasible_a;
  text('seats-delta',`${signed(change)} planned-feasible seats compared with A`);
  text('restored',data.restored?'Exact A/B/A restoration':'RESTORATION FAILED');
  text('parity',data.baseline_parity?'Same outcome · PASS':'BASELINE MISMATCH');
  text('restore-proof',data.restored?'A/B/A restoration · PASS':'RESTORATION FAILED');
  text('parity-icon',data.baseline_parity?'✓':'×');text('restore-icon',data.restored?'✓':'×');
  renderPrograms(data);renderRoles(data);renderGraph(data.graph,data.capacity_b);
  text('status',`Relate ${data.relate_version} · connected`);
}
async function evaluate(value){const current=++nonce;slider.value=value;text('capacity-value',value);$('error').hidden=true;
  text('status','Querying embedded Relate…');
  let phase='Relate/API';
  try{const r=await fetch(`/api/evaluate?capacity=${value}`,{cache:'no-store'});const json=await r.json();if(!r.ok)throw new Error(json.error||`HTTP ${r.status}`);
    if(current!==nonce)return;
    phase='Verification';
    if(json.baseline_parity!==true||json.restored!==true)throw new Error('Verification FAILED. No success claim.');
    phase='UI rendering';
    render(json);
  }catch(err){if(current!==nonce)return;$('error').hidden=false;text('error',String(err));text('status',`${phase} FAILED`);}
}
let timer=null;slider.addEventListener('input',()=>{text('capacity-value',slider.value);clearTimeout(timer);timer=setTimeout(()=>evaluate(Number(slider.value)),160)});
$('btn-a').addEventListener('click',()=>{clearTimeout(timer);evaluate(140)});
$('btn-b').addEventListener('click',()=>{clearTimeout(timer);evaluate(100)});
evaluate(100);
