const $ = (id) => document.getElementById(id);
let csrf = window.VK_CSRF || "";
const body = document.body;
function show(el, yes=true){el.classList.toggle('hidden',!yes)}
function message(text, bad=false){$('result').textContent=text;$('result').classList.toggle('error',bad)}
async function api(url, options={}){
  const headers = {...(options.headers||{})};
  if(options.method && options.method !== 'GET'){headers['X-CSRF-Token']=csrf;}
  if(options.body && options.body instanceof URLSearchParams){headers['Content-Type']='application/x-www-form-urlencoded'}
  else if(options.body && typeof options.body !== 'string'){headers['Content-Type']='application/json';options.body=JSON.stringify(options.body)}
  const res=await fetch(url,{...options,headers,credentials:'same-origin'});
  const data=await res.json().catch(()=>({detail:'Unexpected server response'}));
  if(!res.ok) throw new Error(data.detail||'Request failed');
  return data;
}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}

async function boot(){
  const auth=body.dataset.auth==='true';
  show($('loginPanel'),!auth);show($('appPanel'),auth);show($('logoutBtn'),auth);
  if(auth){await loadHealth();await loadServers();await loadKeepers();}
}

$('loginForm').addEventListener('submit',async e=>{
  e.preventDefault();$('loginError').textContent='';
  try{await api('/api/login',{method:'POST',body:new URLSearchParams({password:$('password').value})});location.reload();}
  catch(err){$('loginError').textContent=err.message}
});
$('logoutBtn').addEventListener('click',async()=>{try{await api('/api/logout',{method:'POST'});location.reload()}catch(e){message(e.message,true)}});

async function loadHealth(){
  try{
    const h=await api('/api/health');
    $('connectionValue').textContent=h.bot_ready?'ONLINE':(h.bot_error?'OFFLINE':'STARTING');
    $('botState').textContent=h.bot_ready?'Bot connected':(h.bot_error?h.bot_error:'Bot connecting');
    document.querySelector('.dot').classList.toggle('ok',h.bot_ready);
    $('keeperCount').textContent=h.keepers;
    $('restoreBadge').textContent=h.restores+' restores';
    $('intervalLabel').textContent=Math.round(h.keeper_interval/60);
    if(h.voice_connections.length)$('botState').textContent=`In voice: ${h.voice_connections.map(v=>v.channel_name).join(', ')}`;
    if(h.keeper_errors.length)message('Keeper: '+h.keeper_errors[0],true);
  }catch(e){$('connectionValue').textContent='OFFLINE';$('botState').textContent='Bot unavailable'}
}

async function loadServers(){
  try{
    const list=await api('/api/servers');
    $('serverCount').textContent=list.length;
    $('guildSelect').innerHTML='<option value="">Select a server</option>'+list.map(g=>`<option value="${g.id}">${escapeHtml(g.name)}</option>`).join('');
  }catch(e){message(e.message,true)}
}

$('guildSelect').addEventListener('change',async()=>{
  const id=$('guildSelect').value;
  $('channelSelect').disabled=true;
  $('channelSelect').innerHTML='<option>Loading channels…</option>';
  $('emojiList').innerHTML='';
  if(!id){$('channelSelect').innerHTML='<option>Choose a server first</option>';$('emojiHint').textContent='Pick a server first';return}
  try{
    const list=await api(`/api/servers/${id}/channels`);
    $('channelSelect').innerHTML='<option value="">Select a voice channel</option>'+list.map(c=>`<option value="${c.id}">${c.type==='Stage'?'🎙️':'🔊'} ${escapeHtml(c.name)}</option>`).join('');
    $('channelSelect').disabled=false;
  }catch(e){$('channelSelect').innerHTML='<option>Could not load channels</option>';message(e.message,true)}
  try{
    const emojis=await api(`/api/servers/${id}/emojis`);
    $('emojiHint').textContent=emojis.length+' available';
    $('emojiList').innerHTML=emojis.length?emojis.map(e=>`<button type="button" class="emoji" title="${escapeHtml(e.name)}" data-md="${escapeHtml(e.markdown)}"><img src="${e.url}" alt="${escapeHtml(e.name)}"><span>${escapeHtml(e.name)}</span></button>`).join(''):'<span class="muted">No custom emojis in this server.</span>';
    document.querySelectorAll('#emojiList .emoji').forEach(b=>b.addEventListener('click',()=>insertEmoji(b.dataset.md)));
  }catch(e){$('emojiHint').textContent='Could not load emojis'}
});

function insertEmoji(markdown){
  const el=$('statusInput'),start=el.selectionStart,end=el.selectionEnd;
  el.value=el.value.slice(0,start)+markdown+el.value.slice(end);
  const pos=start+markdown.length;el.setSelectionRange(pos,pos);el.focus();
  el.dispatchEvent(new Event('input'));
}

$('channelSelect').addEventListener('change',()=>{$('previewChannel').textContent=$('channelSelect').selectedOptions[0]?.textContent||'Choose a channel'});
$('statusInput').addEventListener('input',()=>{$('charCount').textContent=`${$('statusInput').value.length} / 500`;$('previewStatus').textContent=$('statusInput').value||'Your custom status will appear here.'});
document.querySelectorAll('[data-preset]').forEach(b=>b.addEventListener('click',()=>{$('statusInput').value=b.dataset.preset;$('statusInput').dispatchEvent(new Event('input'))}));

async function sendStatus(value){
  const guild_id=$('guildSelect').value,channel_id=$('channelSelect').value;
  if(!guild_id||!channel_id){message('Select a server and voice channel first.',true);return}
  try{
    const d=await api('/api/status',{method:'POST',body:{
      guild_id:guild_id,channel_id:channel_id,status:value,
      keep_status:$('keepToggle').checked,stay_connected:$('connectToggle').checked
    }});
    message(d.warning?d.message+' — '+d.warning:d.message,Boolean(d.warning));await loadKeepers();await loadHealth();
  }catch(e){message(e.message,true)}
}
$('setBtn').addEventListener('click',()=>sendStatus($('statusInput').value.trim()));
$('clearBtn').addEventListener('click',async()=>{
  await sendStatus('');$('statusInput').value='';$('statusInput').dispatchEvent(new Event('input'));
  $('keepToggle').checked=false;$('connectToggle').checked=false;
});

async function loadKeepers(){
  try{
    const list=await api('/api/keepers');
    $('keeperCount').textContent=list.length;
    if(!list.length){$('keeperList').innerHTML='<p class="muted">No keepers yet. Set a status with the toggles enabled to add one.</p>';return}
    $('keeperList').innerHTML=list.map(k=>`<div class="keeper-row">
      <div class="keeper-main"><b>${escapeHtml(k.channel_name)}</b><small>${escapeHtml(k.guild_id)} / ${escapeHtml(k.channel_id)}</small></div>
      <div class="keeper-tags">${k.keep_status?'<span class="tag">STATUS 24/7</span>':''}${k.stay_connected?'<span class="tag green">IN VOICE 24/7</span>':''}${k.connected?'<span class="tag live">CONNECTED</span>':''}</div>
      <div class="keeper-status">${escapeHtml(k.status||'—')}</div>
      <button class="secondary small" data-remove="${k.channel_id}">Remove</button>
    </div>`).join('');
    document.querySelectorAll('[data-remove]').forEach(b=>b.addEventListener('click',async()=>{
      try{await api('/api/keepers/'+b.dataset.remove,{method:'DELETE'});await loadKeepers();await loadHealth();message('Keeper removed.')}
      catch(e){message(e.message,true)}
    }));
  }catch(e){message(e.message,true)}
}
$('refreshKeepers').addEventListener('click',async()=>{await loadKeepers();await loadHealth()});

boot();
