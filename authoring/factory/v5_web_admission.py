#!/usr/bin/env python3
"""Bounded authoring-time Web admission for V5 references and Web sources.

This module fetches at most one explicitly supplied HTTPS resource and follows at
most five redirects. Every destination is syntax-checked, resolved, and proven
public before a socket is opened. The transport connects to one of the approved
IP literals and keeps TLS SNI/Host bound to the original hostname, preventing a
second uncontrolled DNS lookup at connect time.

It is deliberately not a crawler, mirror, archive, link monitor, browser, or
runtime dependency. Tests inject a deterministic resolver/transport and require
no public Internet access.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import http.client
import ipaddress
import socket
import ssl
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urljoin, urlsplit, urlunsplit

from authoring.factory import factory_gate as factory

SCHEMA = "learnit.atlas.v5.web_resource_admission.v1"
PROFILE = "atlas.v5.authoring-web-admission.r1"
PURPOSES = {"learner-reference", "authoring-source"}
PASS = "PASS_V5_WEB_RESOURCE_ADMISSION_R1"
HOLD = "HOLD_V5_WEB_RESOURCE_ADMISSION_R1"
MAX_REDIRECTS = 5
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
CONNECT_TIMEOUT_SECONDS = 8.0
READ_TIMEOUT_SECONDS = 12.0
REDIRECT_STATUSES = {301, 302, 303, 307, 308}
AUTH_STATUSES = {401, 403, 407}
MISSING_STATUSES = {404, 410}
EXECUTABLE_TYPES = {"application/x-msdownload","application/x-executable","application/vnd.microsoft.portable-executable","application/x-sh","application/x-bat","application/java-archive"}
DOWNLOAD_ONLY_TYPES = {"application/octet-stream"}

class WebAdmissionError(ValueError):
    pass

@dataclass(frozen=True)
class Response:
    status: int
    headers: Mapping[str, str]
    body: bytes

def canonical(value: Any) -> bytes:
    return factory.canonical_json_bytes(value)

def digest_bytes(data: bytes) -> str:
    return factory.sha256_bytes(data)

def digest(value: Any) -> str:
    return digest_bytes(canonical(value))

def _normalized_url(url: str) -> tuple[str, str, int]:
    if not isinstance(url, str) or not url or url != url.strip(): raise WebAdmissionError("URL must be a non-empty string without surrounding whitespace")
    if any(ord(ch) <= 0x20 or ord(ch) == 0x7F for ch in url): raise WebAdmissionError("URL whitespace/control characters are forbidden")
    if "\\" in url: raise WebAdmissionError("URL backslashes are forbidden")
    try: parts=urlsplit(url)
    except ValueError as exc: raise WebAdmissionError(f"malformed URL: {exc}") from exc
    if parts.scheme.lower() != "https": raise WebAdmissionError("HTTPS is required")
    if parts.username is not None or parts.password is not None: raise WebAdmissionError("URL credentials/userinfo are forbidden")
    host=parts.hostname
    if not host: raise WebAdmissionError("URL host is required")
    try: host_ascii=host.encode("idna").decode("ascii").lower()
    except UnicodeError as exc: raise WebAdmissionError("URL hostname is not valid IDNA") from exc
    try: port=parts.port or 443
    except ValueError as exc: raise WebAdmissionError(f"invalid URL port: {exc}") from exc
    if not 1 <= port <= 65535: raise WebAdmissionError("URL port out of range")
    netloc=host_ascii if port == 443 else f"{host_ascii}:{port}"
    return urlunsplit(("https",netloc,parts.path or "/",parts.query,parts.fragment)),host_ascii,port

def _public_ip(value: str) -> str:
    try: ip=ipaddress.ip_address(value)
    except ValueError as exc: raise WebAdmissionError(f"resolver returned invalid IP {value!r}") from exc
    if not ip.is_global or ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved:
        raise WebAdmissionError(f"non-public destination rejected: {ip.compressed}")
    return ip.compressed

def system_resolver(host: str, port: int) -> list[str]:
    try: infos=socket.getaddrinfo(host,port,type=socket.SOCK_STREAM)
    except OSError as exc: raise WebAdmissionError(f"DNS resolution failed for {host}: {exc}") from exc
    ips=sorted({_public_ip(str(info[4][0])) for info in infos})
    if not ips: raise WebAdmissionError(f"DNS produced no public destination for {host}")
    return ips

def resolve_public(host: str, port: int, resolver: Callable[[str,int],Sequence[str]]) -> list[str]:
    values=resolver(host,port)
    if not isinstance(values,Sequence) or isinstance(values,(str,bytes)) or not values: raise WebAdmissionError("resolver must return one or more IP strings")
    ips=sorted({_public_ip(str(value)) for value in values})
    if not ips: raise WebAdmissionError("no public destination remains after resolution")
    return ips

class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self,host:str,port:int,approved_ip:str,timeout:float):
        self._approved_ip=approved_ip
        super().__init__(host=host,port=port,timeout=timeout,context=ssl.create_default_context())
    def connect(self)->None:
        raw=socket.create_connection((self._approved_ip,self.port),self.timeout); raw.settimeout(self.timeout)
        self.sock=self._context.wrap_socket(raw,server_hostname=self.host)

def pinned_transport(url:str,approved_ips:Sequence[str],connect_timeout:float,read_timeout:float,max_bytes:int)->Response:
    normalized,host,port=_normalized_url(url); parts=urlsplit(normalized); target=parts.path or "/"
    if parts.query: target += "?"+parts.query
    host_header=host if port==443 else f"{host}:{port}"; last_error=None
    for ip in approved_ips:
        conn=None
        try:
            conn=_PinnedHTTPSConnection(host,port,ip,connect_timeout)
            conn.request("GET",target,headers={"Host":host_header,"User-Agent":"Learnit-V5-Authoring-Admission/1.0","Accept":"text/html,text/plain,application/pdf,application/xhtml+xml,image/*;q=0.8,*/*;q=0.1","Connection":"close"})
            response=conn.getresponse()
            if conn.sock is not None: conn.sock.settimeout(read_timeout)
            body=response.read(max_bytes+1)
            if len(body)>max_bytes: raise WebAdmissionError(f"response exceeds bounded limit {max_bytes} bytes")
            return Response(int(response.status),{str(k).lower():str(v) for k,v in response.getheaders()},body)
        except (OSError,ssl.SSLError,http.client.HTTPException,TimeoutError,WebAdmissionError) as exc: last_error=exc
        finally:
            if conn is not None: conn.close()
    raise WebAdmissionError(f"all approved destinations failed: {last_error}")

def _media_type(headers:Mapping[str,str])->str: return str(headers.get("content-type","")).split(";",1)[0].strip().lower()
def _download_only(headers:Mapping[str,str],media_type:str)->bool: return "attachment" in str(headers.get("content-disposition","")).lower() or media_type in DOWNLOAD_ONLY_TYPES

def _record(*,purpose:str,submitted_url:str,final_url:str|None,checked_at:str,status:int|None,content_type:str|None,redirect_count:int,body:bytes|None,resolution_chain:list[dict[str,Any]],verdict:str,reasons:list[str])->dict[str,Any]:
    content=None if body is None else {"bytes":len(body),"sha256":digest_bytes(body)}
    stable=None if content is None else {"kind":"content-sha256","value":content["sha256"]}
    core={"schema":SCHEMA,"profile":PROFILE,"purpose":purpose,"submittedUrl":submitted_url,"finalUrl":final_url,"checkedAt":checked_at,"httpStatus":status,"contentType":content_type,"redirectCount":redirect_count,"accessClassification":"public-anonymous" if verdict==PASS else "not-admitted","stableIdentifier":stable,"content":content,"resolutionChain":resolution_chain,"decision":{"verdict":verdict,"reasons":sorted(set(reasons))}}
    return {**core,"admissionId":digest(core)}

def admit_with_body(url:str,*,purpose:str,checked_at:str,resolver:Callable[[str,int],Sequence[str]]=system_resolver,transport:Callable[[str,Sequence[str],float,float,int],Response]=pinned_transport,max_redirects:int=MAX_REDIRECTS,max_bytes:int=MAX_RESPONSE_BYTES,connect_timeout:float=CONNECT_TIMEOUT_SECONDS,read_timeout:float=READ_TIMEOUT_SECONDS)->tuple[dict[str,Any],bytes|None]:
    """Admit one bounded Web resource and return the exact admitted bytes on PASS.

    The returned bytes are the same bytes hashed into the admission record. This
    lets a Role B caller materialize the exact admitted payload as an existing
    Factory --source input without performing a second, potentially different,
    network retrieval.
    """
    if purpose not in PURPOSES: raise WebAdmissionError(f"unsupported purpose {purpose!r}")
    if not isinstance(checked_at,str) or not checked_at.strip(): raise WebAdmissionError("checked_at is required")
    if max_redirects!=MAX_REDIRECTS: raise WebAdmissionError("redirect policy is fixed at five redirects for R1")
    submitted=url; current=url; seen=set(); chain=[]; redirects=0
    try:
        while True:
            normalized,host,port=_normalized_url(current)
            if normalized in seen: raise WebAdmissionError("redirect loop detected")
            seen.add(normalized); ips=resolve_public(host,port,resolver); chain.append({"url":normalized,"host":host,"port":port,"approvedIps":ips})
            response=transport(normalized,ips,connect_timeout,read_timeout,max_bytes); status=response.status; headers={str(k).lower():str(v) for k,v in response.headers.items()}; media_type=_media_type(headers)
            if status in REDIRECT_STATUSES:
                location=headers.get("location")
                if not location: raise WebAdmissionError(f"redirect status {status} without Location")
                if redirects>=max_redirects: raise WebAdmissionError("redirect limit exceeded")
                target=urljoin(normalized,location); _normalized_url(target); redirects+=1; current=target; continue
            if status in AUTH_STATUSES: raise WebAdmissionError(f"authentication-required HTTP status {status}")
            if status in MISSING_STATUSES: raise WebAdmissionError(f"missing-resource HTTP status {status}")
            if not 200 <= status < 300: raise WebAdmissionError(f"non-success HTTP status {status}")
            if not response.body: raise WebAdmissionError("empty resource body")
            if media_type in EXECUTABLE_TYPES: raise WebAdmissionError(f"executable content type rejected: {media_type}")
            if _download_only(headers,media_type): raise WebAdmissionError(f"download-only resource rejected: {media_type or 'unknown'}")
            body=bytes(response.body)
            record=_record(purpose=purpose,submitted_url=submitted,final_url=normalized,checked_at=checked_at,status=status,content_type=media_type or "application/octet-stream",redirect_count=redirects,body=body,resolution_chain=chain,verdict=PASS,reasons=[])
            return record,body
    except WebAdmissionError as exc:
        record=_record(purpose=purpose,submitted_url=submitted,final_url=None,checked_at=checked_at,status=None,content_type=None,redirect_count=redirects,body=None,resolution_chain=chain,verdict=HOLD,reasons=[str(exc)])
        return record,None

def admit(url:str,*,purpose:str,checked_at:str,resolver:Callable[[str,int],Sequence[str]]=system_resolver,transport:Callable[[str,Sequence[str],float,float,int],Response]=pinned_transport,max_redirects:int=MAX_REDIRECTS,max_bytes:int=MAX_RESPONSE_BYTES,connect_timeout:float=CONNECT_TIMEOUT_SECONDS,read_timeout:float=READ_TIMEOUT_SECONDS)->dict[str,Any]:
    record,_=admit_with_body(url,purpose=purpose,checked_at=checked_at,resolver=resolver,transport=transport,max_redirects=max_redirects,max_bytes=max_bytes,connect_timeout=connect_timeout,read_timeout=read_timeout)
    return record

def verify(record:Any)->dict[str,Any]:
    if not isinstance(record,dict): raise WebAdmissionError("admission record must be an object")
    keys={"schema","profile","purpose","submittedUrl","finalUrl","checkedAt","httpStatus","contentType","redirectCount","accessClassification","stableIdentifier","content","resolutionChain","decision","admissionId"}
    if set(record)!=keys: raise WebAdmissionError(f"admission fields mismatch: {sorted(set(record)^keys)}")
    if record["schema"]!=SCHEMA or record["profile"]!=PROFILE or record["purpose"] not in PURPOSES: raise WebAdmissionError("unsupported admission schema/profile/purpose")
    core={k:v for k,v in record.items() if k!="admissionId"}
    if record["admissionId"]!=digest(core): raise WebAdmissionError("admissionId mismatch")
    decision=record.get("decision")
    if not isinstance(decision,dict) or set(decision)!={"verdict","reasons"} or decision["verdict"] not in {PASS,HOLD} or not isinstance(decision["reasons"],list): raise WebAdmissionError("invalid decision")
    if decision["verdict"]==PASS:
        _normalized_url(record["submittedUrl"]); _normalized_url(record["finalUrl"])
        if not 0 <= record["redirectCount"] <= MAX_REDIRECTS or record["accessClassification"]!="public-anonymous": raise WebAdmissionError("PASS policy mismatch")
        content=record["content"]; stable=record["stableIdentifier"]
        if not isinstance(content,dict) or set(content)!={"bytes","sha256"}: raise WebAdmissionError("PASS requires exact content evidence")
        if stable!={"kind":"content-sha256","value":content["sha256"]}: raise WebAdmissionError("stableIdentifier/content mismatch")
        if decision["reasons"]: raise WebAdmissionError("PASS cannot contain reasons")
    return record

def parser()->argparse.ArgumentParser:
    p=argparse.ArgumentParser(description="Bounded V5 authoring-time Web admission"); p.add_argument("--url",required=True); p.add_argument("--purpose",choices=sorted(PURPOSES),required=True); p.add_argument("--checked-at",required=True); p.add_argument("--json-out",type=Path); p.add_argument("--capture-out",type=Path,help="Write the exact admitted bytes; authoring-source purpose only."); return p

def main(argv:list[str]|None=None)->int:
    p=parser(); args=p.parse_args(argv)
    if args.capture_out is not None and args.purpose!="authoring-source":
        p.error("--capture-out is allowed only with --purpose authoring-source")
    record,body=admit_with_body(args.url,purpose=args.purpose,checked_at=args.checked_at); verify(record)
    if args.json_out: args.json_out.write_bytes(canonical(record)+b"\n")
    if args.capture_out is not None and record["decision"]["verdict"]==PASS:
        if body is None: raise WebAdmissionError("PASS admission did not return exact capture bytes")
        args.capture_out.write_bytes(body)
    print(canonical(record).decode("utf-8")); return 0 if record["decision"]["verdict"]==PASS else 8

if __name__=="__main__": raise SystemExit(main())
