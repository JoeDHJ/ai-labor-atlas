/* Offline decision calculator; the Python implementation is checked against this function. */
const strategyNames = {baseline:'Current workflow',ai_only:'AI without training',train:'AI + role-specific training',redesign:'AI + training + task reallocation',hire_analyst:'Recruit one analyst',hire_reviewer:'AI + training + recruit one reviewer'};
function runWorkflow(p) {
  for (const [key,value] of Object.entries(p)) if(typeof value!=='number'||!Number.isFinite(value)) throw Error(`${key} must be finite`);
  if(!Number.isInteger(p.weeks)||p.weeks<2||p.weeks>104||!Number.isInteger(p.hiring_lead_weeks)||p.hiring_lead_weeks<0||p.hiring_lead_weeks>104||!Number.isInteger(p.reallocation_delay_weeks)||p.reallocation_delay_weeks<2||p.reallocation_delay_weeks>104) throw Error('Invalid horizon, recruitment or qualification delay');
  if(p.trained_error_rate<0||p.trained_error_rate>1) throw Error('Invalid error rate');
  for(const k of ['demand_per_week','value_per_accepted_case','analyst_hours_per_week','reviewer_hours_per_week','ai_review_hours']) if(p[k]<=0||p[k]>1000000) throw Error(`Invalid ${k}`);
  const strategies=Object.entries(strategyNames).map(([id,label])=>{
    const ai=['ai_only','train','redesign','hire_reviewer'].includes(id), trained=['train','redesign','hire_reviewer'].includes(id);
    const error=trained?p.trained_error_rate:(ai?.25:.10),quality=1-error*.10;
    const requiredA=6+(id==='redesign'?40/p.reallocation_delay_weeks:0),feasible=!trained||(p.analyst_hours_per_week>=requiredA&&p.reviewer_hours_per_week>=4);
    const au=.5+(ai?.9+.8:1.5+2)+error,ru=(trained?p.ai_review_hours:(ai?1.6:1.2))+(trained?.15:(ai?.25:.05))+error*.5;
    const trajectory=[];
    for(let week=1;week<=p.weeks;week++){
      const moved=id==='redesign'&&week>p.reallocation_delay_weeks,analysts=moved?5:6,reviewers=moved?3:2;
      const hired=week>p.hiring_lead_weeks,a=analysts+Number(id==='hire_analyst'&&hired),r=reviewers+Number(id==='hire_reviewer'&&hired);
      const crossTraining=id==='redesign'&&week<=p.reallocation_delay_weeks?40/p.reallocation_delay_weeks:0;
      const ac=Math.max(0,a*p.analyst_hours_per_week-(trained&&week<=2?analysts*6:0)-crossTraining)/au;
      const rc=Math.max(0,r*p.reviewer_hours_per_week-(trained&&week<=2?reviewers*4:0))/ru;
      const attempts=Math.min(ac,rc,p.demand_per_week),bottleneck=p.demand_per_week<=Math.min(ac,rc)?'demand':(ac<=rc?'analyst':'reviewer');
      let cost=8200+(ai?400:0)+(hired&&id.startsWith('hire_')?(id==='hire_analyst'?900:1400):0);
      if(week===1)cost+=(trained?2000:0)+(id.startsWith('hire_')?2500:0);
      trajectory.push({week,analyst_capacity:ac,reviewer_capacity:rc,completed_cases:attempts,accepted_cases:attempts*quality,bottleneck,cash_cost:cost});
    }
    const accepted=trajectory.reduce((s,r)=>s+r.accepted_cases,0),cost=trajectory.reduce((s,r)=>s+r.cash_cost,0);
    return{id,label,quality_pass_rate:quality,quality_eligible:quality>=.98-1e-12,feasibility_eligible:feasible,accepted_cases:accepted,cash_cost:cost,contribution:accepted*p.value_per_accepted_case-cost,analyst_hours_per_case:au,reviewer_hours_per_case:ru,steady_bottleneck:trajectory.at(-1).bottleneck,trajectory};
  });
  const base=strategies[0];for(const r of strategies){r.incremental_accepted_cases=r.accepted_cases-base.accepted_cases;r.incremental_cash_cost=r.cash_cost-base.cash_cost;r.incremental_contribution=r.contribution-base.contribution;r.break_even_value_per_case=r.incremental_accepted_cases>0?r.incremental_cash_cost/r.incremental_accepted_cases:null;}
  const eligible=strategies.filter(r=>r.quality_eligible&&r.feasibility_eligible).sort((a,b)=>b.contribution-a.contribution);
  return{schema:'atlas.workflow.v1',status:'hypothetical_decision_model',parameters:p,strategies,best_strategy:eligible[0]?.id??null,quality_floor:.98};
}
globalThis.runWorkflow=runWorkflow;

if(typeof document!=='undefined'){
const data=JSON.parse(document.getElementById('atlasData').textContent),m=data.measurement,b=data.benchmark;
const $=id=>document.getElementById(id),esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=(v,n=1)=>v==null?'Unavailable':Number(v).toLocaleString('en-US',{maximumFractionDigits:n,minimumFractionDigits:n}),money=v=>(v<0?'−':'')+'$'+num(Math.abs(v),0);
const pct=(v,n=1)=>num(100*v,n)+'%',rows=m.occupations,c=m.comparison;
$('heroOverlap').textContent=`${c.top_quartile_overlap_count} / ${c.left_top_quartile_count}`;
$('socCount').textContent=num(rows.length,0);$('massCoverage').textContent=num(m.join.allocated_share_pct,2)+'%';$('rho').textContent='Rank correlation '+num(c.spearman_rho,2);
document.querySelector('.chart-note span:last-child').textContent=`${rows.length} common occupations; equally weighted`;
const selectedDefault=rows.find(r=>r.soc==='19-3011')||rows[0];let selected=selectedDefault.soc;
function drawScatter(){
 const svg=$('scatter'),x=v=>62+v*5.15,y=v=>402-v*3.4;
 let html='<title id="scatterTitle">Occupation ranks across Copilot applicability and Claude task use</title><desc id="scatterDesc">Search and select an occupation for accessible numeric values. The dashed diagonal marks equal ranks.</desc>';
 for(const n of [0,25,50,75,100])html+=`<path d="M62 ${y(n)}H577 M${x(n)} 62V402" stroke="#dfe4dc"/><text x="${x(n)}" y="424" text-anchor="middle">${n}</text><text x="49" y="${y(n)+4}" text-anchor="end">${n}</text>`;
 html+='<text x="320" y="456" text-anchor="middle">Copilot applicability percentile</text><text transform="translate(17 235) rotate(-90)" text-anchor="middle">Claude task-use percentile</text><path d="M62 402L577 62" stroke="#a1b6aa" stroke-dasharray="5 6"/>';
 for(const r of rows.filter(r=>r.soc!==selected))html+=`<circle cx="${x(r.ms_rank)}" cy="${y(r.claude_rank)}" r="3.3" fill="#267d75" opacity=".32" data-soc="${r.soc}" style="cursor:pointer"><title>${esc(r.title)}: applicability rank ${num(r.ms_rank)}, use rank ${num(r.claude_rank)}</title></circle>`;
 const r=rows.find(r=>r.soc===selected);if(r)html+=`<circle cx="${x(r.ms_rank)}" cy="${y(r.claude_rank)}" r="7" fill="#bc5428" stroke="white" stroke-width="2"><title>${esc(r.title)} selected</title></circle>`;
 svg.innerHTML=html;
}
function showOccupation(code){
 const r=rows.find(r=>r.soc===code);if(!r){$('occupationDetail').innerHTML='<p class="empty">No matching occupation. Try another title or SOC code.</p>';$('taskDetail').innerHTML='';$('taskMore').textContent='';return;}
 selected=code;drawScatter();
 $('occupationDetail').innerHTML=`<h3 class="occupation-title">${esc(r.title)}</h3><p class="small">Detailed SOC 2018 · ${r.soc}</p><div class="metric-pair"><div><strong>${num(r.ms_applicability,3)}</strong><span>Copilot applicability, 0–1</span><span>Percentile ${num(r.ms_rank)}</span></div><div><strong>${num(r.claude_share_pct,4)}%</strong><span>Allocated Claude conversation share</span><span>Percentile ${num(r.claude_rank)}</span></div></div><p class="small">Rank difference: ${num(r.rank_gap_pp)} percentage points (task use minus applicability). These measures have different units and observation periods.</p>`;
 const tasks=data.task_examples[code]||[];
 $('taskDetail').innerHTML=tasks.map(t=>`<li>${esc(t.task)}<small>${num(t.allocated_share_pct,4)}% allocated share · ${t.soc_count} linked SOC${t.soc_count===1?'':'s'}</small></li>`).join('');
 $('taskMore').textContent=tasks.length?'Up to three highest-share task links are shown. Full links are in the reproducible SQL database.':'No exact released task-usage link in this source universe. This is not evidence that no one in this occupation uses AI.';
}
function filterOccupations(){const q=$('occupationSearch').value.toLowerCase().trim(),matches=rows.filter(r=>`${r.title} ${r.soc}`.toLowerCase().includes(q));
 $('occupationSelect').innerHTML=matches.map(r=>`<option value="${r.soc}">${esc(r.title)} · ${r.soc}</option>`).join('');
 $('matchCount').textContent=`${matches.length} matching occupation${matches.length===1?'':'s'}`;
 const code=matches.some(r=>r.soc===selected)?selected:matches[0]?.soc;$('occupationSelect').value=code||'';showOccupation(code);}
$('occupationSearch').addEventListener('input',filterOccupations);$('occupationSelect').addEventListener('change',e=>showOccupation(e.target.value));
$('scatter').addEventListener('click',e=>{const code=e.target.dataset.soc;if(code){$('occupationSearch').value='';selected=code;filterOccupations();}});filterOccupations();
const a=m.aioe_summary;
$('measurementDetails').innerHTML=`<p>Microsoft publishes ${m.microsoft_count} SOCs; the source-task crosswalk links ${m.anthropic_soc_count} SOCs. Their intersection contains ${m.common_count}. ${m.zero_use_soc_count} common SOCs have no matched released task share. Missing source coverage is not filled with zero.</p><p>Exact wording matches ${m.join.matched_task_count} of ${m.join.released_task_count} released task labels. ${num(m.join.unmatched_share_pct,4)}% of released conversation share remains unmatched and is retained in the coverage denominator. Shared wording maps to multiple target SOCs for ${m.join.shared_task_count} labels; its share is divided equally across distinct targets.</p><p>Spearman rank correlation is ${num(c.spearman_rho,3)} on ${c.sample_count} occupations and ${num(m.positive_use_comparison.spearman_rho,3)} on ${m.positive_use_comparison.sample_count} positive-use occupations. Keeping only single-target task links gives ${num(m.exclusive_task_sensitivity.spearman_rho,3)}. The unmatched label is the source residual category “none”. These are descriptive source comparisons, without sampling-error estimates.</p>`+(a?`<p>The three-source intersection contains ${a.common_three_count} occupations (${a.excluded_public_common} public-pair occupations lack local AIOE coverage). On that same intersection:</p><div class="table-scroll"><table><thead><tr><th>Indicators</th><th>Spearman correlation</th><th>Common SOCs</th></tr></thead><tbody>${a.comparisons.map(r=>`<tr><td>${esc(r.left)} / ${esc(r.right)}</td><td>${num(r.spearman_rho,3)}</td><td>${r.sample_count}</td></tr>`).join('')}</tbody></table></div><p class="small">AIOE occupation values remain local. Rank association is neither independent validation nor a causal effect.</p>`:'');
$('reconstruction').textContent=`All ${b.score_reconstruction.soc_count} published SOC scores reconstructed within 1e−10 tolerance; maximum absolute difference ${b.score_reconstruction.maximum_absolute_error.toExponential(2)}.`;
$('benchmark').textContent=`A vocabulary learned on ${num(b.train_count,0)} unique task IDs is evaluated on ${num(b.test_count,0)} held-out IDs. Naive Bayes balanced accuracy: ${pct(b.multinomial_nb.balanced_accuracy)}; keyword rule: ${pct(b.keyword_rule.balanced_accuracy)}; majority rule: ${pct(b.majority.balanced_accuracy)}.`;
$('assumptions').innerHTML=`<p>Six analysts and two reviewers, each with 30 usable hours/week; 12 weeks. Fixed payroll is $8,200/week. Reallocation moves one existing analyst to review and holds pay constant, with 40 additional hours of role qualification over weeks 1–2. The move begins in week 3. Qualification after those hours is an assumption that needs a real competency assessment.</p><p>Scope 0.5 h, evidence preparation 1.5 h and drafting 2 h per case. AI reduces preparation to 0.9 h and drafting to 0.8 h. One error triggers 1 analyst hour and 0.5 review hour of rework. Review is 1.2 h + 0.05 h coordination at baseline; untrained AI is 1.6 h + 0.25 h; trained AI uses the input review time + 0.15 h. Initial error rates: 10% baseline, 25% untrained AI, and the trained input.</p><p>One rework pass resolves 90% of errors: expected quality = 1 − initial error rate × 0.10. Alternatives below 98% quality are ineligible. Expected accepted cases = min(analyst capacity, reviewer capacity, demand) × quality. Residual errors remain in the output; this is a stylized quality model.</p><p>Training takes 12 h/analyst and 8 h/reviewer, spread over weeks 1–2; no negative capacity is allowed. Salaries already pay for this time, so it is not added again as a cash expense. Trained alternatives add $2,000 direct training cost; AI tools cost $400/week. Recruitment costs $2,500, with salaries of $900/week for an analyst or $1,400/week for a reviewer starting after the input delay. New hires are assumed prequalified.</p><p>Contribution = expected accepted cases × assumed value − listed cash costs. Compare the change from baseline over the same horizon. No wages, AI savings, error rates or training effects here are estimated from the occupational indicators.</p>`;
let current=null;
function params(){return{demand_per_week:Number($('demand').value),value_per_accepted_case:Number($('caseValue').value),analyst_hours_per_week:30,reviewer_hours_per_week:30,ai_review_hours:Number($('reviewHours').value),trained_error_rate:Number($('errorRate').value)/100,hiring_lead_weeks:Number($('hiringLead').value),reallocation_delay_weeks:2,weeks:12};}
function calculate(){
 try{current=runWorkflow(params());const best=current.strategies.find(r=>r.id===current.best_strategy),base=current.strategies[0];
 $('workflowResult').classList.remove('stale');
 $('workflowResult').innerHTML=`<div class="outcome"><p class="eyebrow">CONDITIONAL MODEL CHOICE / ${current.parameters.weeks} WEEKS</p><h3>${esc(best.label)}</h3><p>${num(best.accepted_cases)} expected accepted cases, versus ${num(base.accepted_cases)} at baseline. Incremental modeled contribution: <b>${money(best.incremental_contribution)}</b>. The choice depends on the stated demand, quality, cross-training and cost assumptions.</p></div><div class="table-scroll"><table><thead><tr><th>Alternative</th><th class="num">Accepted cases</th><th class="num">Quality</th><th class="num">Δ cash cost</th><th class="num">Δ contribution</th><th>Final-week bottleneck</th></tr></thead><tbody>${current.strategies.map(r=>`<tr class="${r.id===best.id?'best-row':''} ${r.quality_eligible?'':'ineligible'}"><td>${esc(r.label)}${r.quality_eligible?'':' · Below quality floor'}</td><td class="num">${num(r.accepted_cases)}</td><td class="num">${pct(r.quality_pass_rate,2)}</td><td class="num">${money(r.incremental_cash_cost)}</td><td class="num">${money(r.incremental_contribution)}</td><td>${esc(r.steady_bottleneck)}</td></tr>`).join('')}</tbody></table></div><p class="small">Expected fractional outputs over the horizon. Δ compares each alternative with the same baseline. Quality is assumed, not measured. An increase in capacity does not imply headcount reductions.</p>`;
 $('workflowStatus').textContent='Current assumptions calculated locally. Results are ready to export.';$('exportWorkflow').disabled=false;
 }catch(e){current=null;$('workflowStatus').textContent=e.message;$('exportWorkflow').disabled=true;}
}
$('workflowForm').addEventListener('submit',e=>{e.preventDefault();calculate();});
$('workflowForm').addEventListener('input',()=>{current=null;$('workflowResult').classList.add('stale');$('workflowStatus').textContent='Assumptions changed. Compare alternatives to update the results.';$('exportWorkflow').disabled=true;});
$('resetWorkflow').addEventListener('click',()=>{$('workflowForm').reset();calculate();});
$('exportWorkflow').addEventListener('click',()=>{if(!current)return;const url=URL.createObjectURL(new Blob([JSON.stringify(current,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='atlas-workflow-decision.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
if(data.local_mode)$('marketLink').href='market.html';calculate();
}
