"""Deterministic dependency validation. Never downloads or starts dependencies."""
import re
from .archive import MAX_FILES

ID=re.compile(r"[a-z0-9][a-z0-9-]{0,47}")
VERSION=re.compile(r"[vV]?(0|[1-9][0-9]*)(?:\.(0|[1-9][0-9]*))?(?:\.(0|[1-9][0-9]*))?(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?")
def version_key(value):
    if not isinstance(value,str) or len(value)>64:raise ValueError("invalid version")
    m=VERSION.fullmatch(value)
    if not m:raise ValueError("unsupported dependency version: "+value)
    pre=m[4]
    parts=[]
    if pre:
        for v in pre.split("."):
            if not v or (v.isdigit() and len(v)>1 and v[0]=="0"):
                raise ValueError("invalid prerelease version")
            parts.append((0,int(v)) if v.isdigit() else (1,v))
    return (int(m[1]),int(m[2] or 0),int(m[3] or 0),0 if pre else 1,tuple(parts))
def parse_constraint(value):
    if not isinstance(value,str) or len(value)>128:
        raise ValueError("invalid dependency constraint")
    if value=="*":return []
    result=[]
    for part in value.split(","):
        m=re.fullmatch(r"(>=|<=|==|!=|>|<)\s*(\S+)",part.strip())
        if not m:raise ValueError("unsupported constraint: "+part)
        result.append((m[1],version_key(m[2])))
    return result
def satisfies(version,constraint):
    comparisons=parse_constraint(constraint)
    if not comparisons:return True
    v=version_key(version)
    return all({"==":v==x,"!=":v!=x,">":v>x,"<":v<x,">=":v>=x,"<=":v<=x}[op] for op,x in comparisons)
def validate_dependencies(value):
    if not isinstance(value,list) or len(value)>64:raise ValueError("invalid dependencies")
    seen=set();result=[]
    for item in value:
        if not isinstance(item,dict) or set(item)!={"id","constraint"} or not isinstance(item["id"],str) or not ID.fullmatch(item["id"]):
            raise ValueError("invalid dependency")
        if item["id"] in seen:raise ValueError("duplicate dependency")
        seen.add(item["id"]);parse_constraint(item["constraint"])
        result.append(dict(item))
    return result
def dependency_order(installed,proposed):
    """Check the entire proposed final state, including reverse dependencies."""
    graph={**installed,**proposed}
    if len(graph)>MAX_FILES:raise ValueError("too many packages")
    edges={}
    for app,meta in graph.items():
        if not isinstance(app,str) or not ID.fullmatch(app):raise ValueError("invalid package id")
        deps=validate_dependencies(meta.get("dependencies",[]));edges[app]=[]
        for dep in deps:
            name=dep["id"]
            if name not in graph:raise ValueError("missing dependency: "+app+" -> "+name)
            if not satisfies(graph[name]["version"],dep["constraint"]):
                raise ValueError("incompatible dependency: "+app+" -> "+name)
            edges[app].append(name)
    # Iterative topological ordering; avoids recursion limits.
    done=set();order=[];pending=set(graph)
    while pending:
        ready=sorted(app for app in pending if set(edges[app])<=done)
        if not ready:raise ValueError("dependency cycle: "+", ".join(sorted(pending)))
        order.extend(ready);done.update(ready);pending.difference_update(ready)
    return order
