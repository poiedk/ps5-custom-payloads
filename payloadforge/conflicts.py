"""Conservative declared resource and version conflict checking."""
from .archive import safe_name
from .dependencies import validate_dependencies,satisfies,dependency_order

def validate_resources(resources):
    if not isinstance(resources,list) or len(resources)>128:raise ValueError("invalid resources")
    seen=set();result=[]
    for item in resources:
        if not isinstance(item,dict) or set(item)!={"type","value"}:raise ValueError("invalid resource")
        kind=item["type"];value=item["value"]
        if kind in ("tcp","udp"):
            if type(value) is not int or not 1<=value<=65535:raise ValueError("invalid port")
            key=(kind,value)
        elif kind=="path":
            if not isinstance(value,str) or not value.startswith("/data/") or len(value)>512 or value.endswith("/"):
                raise ValueError("invalid claimed path")
            normalized="/"+safe_name(value[1:])
            if normalized!=value:raise ValueError("noncanonical path")
            key=(kind,normalized.casefold())
        else:raise ValueError("unsupported resource")
        if key in seen:raise ValueError("duplicate resource")
        seen.add(key);result.append(dict(item))
    return result
def overlap(a,b):
    if a["type"]!=b["type"]:return False
    if a["type"]!="path":return a["value"]==b["value"]
    x,y=a["value"].casefold(),b["value"].casefold()
    return x==y or x.startswith(y+"/") or y.startswith(x+"/")
def validate_state(installed,proposed):
    order=dependency_order(installed,proposed)
    graph={**installed,**proposed}
    resources={}
    for app,meta in graph.items():
        resources[app]=validate_resources(meta.get("resources",[]))
        for conflict in validate_dependencies(meta.get("conflicts",[])):
            other=conflict["id"]
            if other==app:raise ValueError("self conflict")
            if other in graph and satisfies(graph[other]["version"],conflict["constraint"]):
                raise ValueError("declared version conflict: "+app+" vs "+other)
    for i,app in enumerate(order):
        for other in order[:i]:
            for a in resources[app]:
                for b in resources[other]:
                    if overlap(a,b):raise ValueError("resource conflict: "+app+" vs "+other+" "+str(a))
    return order
