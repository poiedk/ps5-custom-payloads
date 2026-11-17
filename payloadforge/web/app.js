"use strict";
const $=id=>document.getElementById(id);
let token="", reviewed=null;
function output(value){$("output").textContent=typeof value==="string"?value:JSON.stringify(value,null,2);}
async function api(path,body){
  if(!token)throw Error("Connect first.");
  const headers={Authorization:"Bearer "+token};
  if(body!==undefined)headers["Content-Type"]="application/json";
  const res=await fetch(path,{method:body===undefined?"GET":"POST",headers,body:body===undefined?undefined:JSON.stringify(body),cache:"no-store"});
  const result=await res.json();
  if(!res.ok)throw Error(result.error||"Request failed");
  return result;
}
function bind(id,fn){$(id).addEventListener("click",async()=>{try{await fn();}catch(e){output("Error: "+e.message);}});}
function currentId(){const id=$("package-id").value.trim();if(!/^[a-z0-9][a-z0-9-]{0,47}$/.test(id))throw Error("Enter a valid package ID.");return id;}
function invalidate(){reviewed=null;$("apply").disabled=true;}
async function refresh(){
  const data=await api("/api/packages");const list=$("packages");list.replaceChildren();
  if(!data.length)list.textContent="No managed packages.";
  data.forEach(p=>{
    const row=document.createElement("article"),label=document.createElement("div"),title=document.createElement("strong"),version=document.createElement("p"),button=document.createElement("button");
    title.textContent=p.id;version.textContent=p.version;button.textContent="Manage";
    button.addEventListener("click",()=>{$("package-id").value=p.id;$("versions").click();});
    label.append(title,version);row.append(label,button);list.append(row);
  });
}
async function getBundle(){
  const file=$("archive").files[0],manifest=$("manifest").files[0],sha=$("sha").value.trim().toLowerCase();
  if(!file||!manifest||!/^[a-f0-9]{64}$/.test(sha))throw Error("ZIP, manifest and verified SHA-256 required.");
  if(file.size>12*1024*1024||manifest.size>2*1024*1024)throw Error("Host preview size limit.");
  const bytes=new Uint8Array(await file.arrayBuffer());let encoded="";
  for(let i=0;i<bytes.length;i+=16384)encoded+=String.fromCharCode(...bytes.subarray(i,i+16384));
  return {archive:btoa(encoded),sha256:sha,manifest:JSON.parse(await manifest.text())};
}
async function mutation(action,extra){
  if(!window.confirm("Approve "+action+" for "+(extra.id||extra.manifest.id)+"?"))return;
  output(await api("/api/action",{action,...extra,confirm:true}));await refresh();
}
bind("connect",async()=>{token=$("token").value;$("token").value="";try{await api("/api/health");$("connection").textContent="Connected · Host preview";await refresh();}catch(e){token="";$("connection").textContent="Disconnected";throw e;}});
bind("refresh",refresh);
["operation","archive","manifest","sha"].forEach(id=>$(id).addEventListener("input",invalidate));
bind("preview",async()=>{invalidate();const bundle=await getBundle(),action=$("operation").value;const result=await api("/api/action",{action:"plan",...bundle});output(result);reviewed={action,bundle};$("apply").disabled=false;});
bind("apply",async()=>{if(!reviewed)throw Error("Review a package first.");const item=reviewed;invalidate();await mutation(item.action,item.bundle);});
bind("versions",async()=>{const result=await api("/api/versions?id="+encodeURIComponent(currentId()));output(result);$("snapshot").value=result.backups[0]?.snapshot||"";});
bind("backup",()=>mutation("backup",{id:currentId()}));
bind("recovery",async()=>output(await api("/api/recovery?id="+encodeURIComponent(currentId()))));
bind("rollback",()=>{const s=$("snapshot").value.trim();if(!/^[a-f0-9]{32}$/.test(s))throw Error("Valid snapshot ID required.");return mutation("rollback",{id:currentId(),snapshot:s});});
bind("uninstall",()=>mutation("uninstall",{id:currentId(),preserve_config:$("keep").checked}));
bind("logs",async()=>output(await api("/api/logs")));
