/* SPDX-License-Identifier: GPL-3.0-or-later */
(function(){
"use strict";
var $=function(id){return document.getElementById(id);};
var token="",ready=false,busy=false,verified=null,observed=null;
var hex=/^[a-f0-9]{64}$/,idPattern=/^[a-z0-9][a-z0-9-]{0,47}$/;
function show(value){$("result").textContent=typeof value==="string"?value:JSON.stringify(value,null,2);}
function refresh(){
 ["verify","status","recovery","catalog","pldmgr-check"].forEach(function(id){$(id).disabled=!ready||busy;});
 ["install","upgrade","downgrade"].forEach(function(id){$(id).disabled=!ready||busy||!verified||!$("package-confirm").checked;});
 ["backup","rollback","uninstall"].forEach(function(id){$(id).disabled=!ready||busy||!$("control-confirm").checked;});
 $("quarantine").disabled=!ready||busy||!observed||!$("control-confirm").checked;
 $("connect").disabled=busy;$("disconnect").disabled=busy;
 Array.prototype.forEach.call(document.querySelectorAll('input, select'),function(el){el.disabled=busy;});
}
function invalidate(){verified=null;$("verified").textContent="No verified package";$("package-confirm").checked=false;refresh();}
function clearSession(){
 token="";ready=false;observed=null;$("pldmgr-status").textContent="Local service not checked.";$("catalog-rows").textContent="";$("catalog-meta").textContent="Connect to view the catalog.";$("token").value="";$("session").textContent="Not connected";
 $("control-confirm").checked=false;invalidate();refresh();
}
function packageId(){var id=$("package-id").value.trim();if(!idPattern.test(id))throw new Error("Enter a valid package ID.");return id;}
function hashValue(id){var value=$(id).value.trim().toLowerCase();if(!hex.test(value))throw new Error("Expected a 64-character SHA-256 in "+id+".");return value;}
function envelope(){
 var m=$("manifest").files[0],a=$("archive").files[0];
 if(!m||!a||!m.size||m.size>2*1024*1024||!a.size||140+m.size+a.size>12*1024*1024)throw new Error("Choose valid manifest and archive files within the upload limits.");
 var mh=hashValue("manifest-hash"),ah=hashValue("archive-hash"),head=new Uint8Array(140),view=new DataView(head.buffer);
 head.set([80,70,85,49]);view.setUint32(4,m.size,false);view.setUint32(8,a.size,false);
 for(var i=0;i<64;i++){head[12+i]=mh.charCodeAt(i);head[76+i]=ah.charCodeAt(i);}
 return new Blob([head,m,a],{type:"application/octet-stream"});
}
async function request(path,method,body){
 if(!hex.test(token))throw new Error("Connect to the local session first.");
 var headers={"Authorization":"Bearer "+token};
 var options={method:method||"GET",headers:headers,cache:"no-store",credentials:"omit",redirect:"error",referrerPolicy:"same-origin"};
 if(options.method==="POST"){headers["X-PayloadForge-Confirm"]="yes";if(body){headers["Content-Type"]="application/octet-stream";options.body=body;}else options.body="";}
 var response=await fetch(path,options);
 var data=await response.json();
 if(response.status===401){clearSession();throw new Error("Session token rejected or expired.");}
 if(!response.ok){throw new Error("HTTP "+response.status+" "+JSON.stringify(data));}
 return data;
}
async function work(fn){
 if(busy)return;
 busy=true;refresh();
 try{await fn();}catch(e){show(String(e.message||e)+"\nInspect the store before retrying a state-changing operation.");}
 finally{busy=false;refresh();}
}
$("connect").addEventListener("click",function(){work(async function(){
 clearSessionAfterCapture();
 try{var health=await request("/api/health");
 if(!health.mutation)throw new Error("Managed development mode is not enabled.");
 ready=true;$("session").textContent="Connected to local managed development runtime";show(health);
 }catch(e){clearSession();throw e;}
});});
function clearSessionAfterCapture(){var value=$("token").value.trim();clearSession();if(!hex.test(value))throw new Error("Invalid session token.");token=value;}
$("disconnect").addEventListener("click",clearSession);
["manifest","archive","manifest-hash","archive-hash"].forEach(function(id){$(id).addEventListener("change",invalidate);});
["manifest-hash","archive-hash"].forEach(function(id){$(id).addEventListener("input",invalidate);});
$("package-confirm").addEventListener("change",refresh);
$("control-confirm").addEventListener("change",refresh);
["snapshot","config","kind","object"].forEach(function(id){$(id).addEventListener("change",function(){$("control-confirm").checked=false;refresh();});});
$("package-id").addEventListener("input",function(){observed=null;$("control-confirm").checked=false;refresh();});
$("verify").addEventListener("click",function(){work(async function(){
 invalidate();var blob=envelope();var info=await request("/api/upload/verify","POST",blob);
 if(!info.ok||!info.integrity_verified)throw new Error("Package verification failed.");
 verified={blob:blob,id:info.id,version:info.version};
 $("verified").textContent="Integrity verified: "+info.id+" / "+info.version+" ("+info.files+" files). Provenance and installed state not verified.";
 $("package-id").value=info.id;observed=null;$("control-confirm").checked=false;show(info);
});});
["install","upgrade","downgrade"].forEach(function(action){$(action).addEventListener("click",function(){work(async function(){
 if(!verified||!$("package-confirm").checked)throw new Error("Verify and confirm the package first.");
 var packageBlob=verified.blob;invalidate();observed=null;var data=await request("/api/upload/"+action,"POST",packageBlob);
 show(data);
});});});
$("pldmgr-check").addEventListener("click",function(){work(async function(){
 var data=await request("/api/pldmgr/version");
 $("pldmgr-status").textContent=data.reachable?"Local endpoint reported version "+data.reported_version+" (identity not verified).":"Local PLDMGR endpoint unavailable or unsupported.";
 show(data);
});});
$("catalog").addEventListener("click",function(){work(async function(){
 var data=await request("/api/catalog"),rows=$("catalog-rows");rows.textContent="";
 if(!Array.isArray(data.items)||data.items.length>4096||data.installable!==false||data.live!==false)throw new Error("Invalid reference catalog.");
 data.items.forEach(function(item){var tr=document.createElement("tr");[item.name,item.id,item.version].forEach(function(value){var td=document.createElement("td");td.textContent=value;tr.appendChild(td);});rows.appendChild(tr);});
 $("catalog-meta").textContent="Snapshot "+data.snapshot_date+" | "+data.pldmgr_count+" reference entries | "+data.companion_count+" companion bundles | source: "+data.source_url+" | Git blob: "+data.source_git_blob;
});});
$("status").addEventListener("click",function(){work(async function(){show(await request("/api/status?id="+packageId()));});});
$("recovery").addEventListener("click",function(){work(async function(){
 var id=packageId();observed=null;var data=await request("/api/recovery?id="+id);
 observed={id:id,marker:data.marker,current:data.current};show(data);$("control-confirm").checked=false;
});});
["backup","rollback","uninstall","quarantine"].forEach(function(action){$(action).addEventListener("click",function(){work(async function(){
 if(!$("control-confirm").checked)throw new Error("Confirm the managed operation first.");
 var id=packageId(),path="/api/control/"+action+"?id="+id;
 if(action==="rollback")path+="&snapshot="+hashValue("snapshot");
 if(action==="uninstall"){var config=$("config").value;if(config!=="keep"&&config!=="drop")throw new Error("Invalid configuration policy.");path+="&config="+config;}
 if(action==="quarantine"){
 if(!observed||observed.id!==id||observed.marker<0||observed.marker>3||!(observed.marker?hex.test(observed.current):observed.current===""))throw new Error("Inspect a valid recovery state first.");
 var kind=$("kind").value;if(!/^[1-5]$/.test(kind))throw new Error("Invalid remnant type.");
 path+="&marker="+observed.marker+"&current="+observed.current+"&kind="+kind+"&object="+hashValue("object");
 }
 $("control-confirm").checked=false;observed=null;var data=await request(path,"POST");
 if(action==="backup"&&data.ok&&hex.test(data.snapshot))$("snapshot").value=data.snapshot;
 show(data);
});});});
$("clear-result").addEventListener("click",function(){show("");});
window.addEventListener("pagehide",function(){token="";verified=null;observed=null;ready=false;});
window.addEventListener("pageshow",function(event){if(event.persisted)clearSession();});
refresh();
})();
