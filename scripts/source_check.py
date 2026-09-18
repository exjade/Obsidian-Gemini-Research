"""Bounded public-web retrieval, independent of provider declarations."""
import datetime as dt
import hashlib
from html.parser import HTMLParser
import http.client
import ipaddress
import json
from pathlib import Path
import re
import socket
import ssl
import unicodedata
import uuid
from urllib.parse import urlsplit, urljoin

POLICY = 'public-get-excerpt-v1'
MAX_BYTES = 524288

class PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]; self.hidden=0; self.in_title=False; self.title=[]
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style','noscript'): self.hidden+=1
        if tag=='title': self.in_title=True
    def handle_endtag(self, tag):
        if tag in ('script','style','noscript'): self.hidden=max(0,self.hidden-1)
        if tag=='title': self.in_title=False
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)
        if self.in_title: self.title.append(data)

def normalize(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC',text)).strip()

def public_target(url):
    p=urlsplit(url)
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password:
        raise ValueError('URL pública HTTP(S) sin credenciales requerida')
    if p.port not in (None,80 if p.scheme=='http' else 443):
        raise ValueError('Puerto no permitido')
    port=p.port or (443 if p.scheme=='https' else 80)
    addresses=socket.getaddrinfo(p.hostname,port,type=socket.SOCK_STREAM)
    ips=list(dict.fromkeys(a[4][0] for a in addresses))
    if not ips or any(not ipaddress.ip_address(ip).is_global or ipaddress.ip_address(ip).is_multicast for ip in ips):
        raise ValueError('Destino privado, local o reservado bloqueado')
    return p,port,ips

def fetch(url):
    redirects=[]
    for _ in range(6):
        p,port,ips=public_target(url)
        conn=(http.client.HTTPSConnection(p.hostname,port,timeout=8,context=ssl.create_default_context())
              if p.scheme=='https' else http.client.HTTPConnection(p.hostname,port,timeout=8))
        # Pin to the already validated address; TLS still verifies the original hostname.
        conn._create_connection=lambda address,timeout,*args: socket.create_connection((ips[0],port),timeout)
        try:
            target=(p.path or '/')+('?' + p.query if p.query else '')
            conn.request('GET',target,headers={'User-Agent':'ObsidianResearch-SourceCheck/1.0','Accept-Encoding':'identity'})
            response=conn.getresponse();status=response.status
            if status in (301,302,303,307,308):
                location=response.getheader('Location')
                if not location: raise ValueError('Redirección sin destino')
                next_url=urljoin(url,location)
                redirects.append({'url':url,'http_status':status,'destination':next_url})
                url=next_url;continue
            content_type=response.getheader('Content-Type','')
            encoding=response.getheader('Content-Encoding','identity')
            body=response.read(MAX_BYTES+1)
            return {'final_url':url,'http_status':status,'content_type':content_type,
                    'content_encoding':encoding,'redirects':redirects,'body':body[:MAX_BYTES],
                    'truncated':len(body)>MAX_BYTES}
        finally:conn.close()
    raise ValueError('Demasiadas redirecciones')

def inspect(url, excerpt, transport=fetch):
    record={'policy':POLICY,'id':uuid.uuid4().hex,'original_url':url,
            'checked_at':dt.datetime.now(dt.timezone.utc).isoformat(),'method':'GET',
            'excerpt_sha256':hashlib.sha256(excerpt.encode()).hexdigest(),
            'availability':'ERROR','excerpt_match':False,'eligible':False}
    try:
        result=transport(url);body=result.pop('body');record.update(result)
        record['body_sha256']=hashlib.sha256(body).hexdigest()
        status=result['http_status']
        if status in (404,410):record['availability']='NOT_FOUND'
        elif status in (401,403,429):record['availability']='RESTRICTED'
        elif status!=200:record['availability']='HTTP_ERROR'
        elif result.get('content_encoding','identity') not in ('','identity'):
            record['availability']='UNSUPPORTED_ENCODING'
        elif not any(t in result['content_type'].lower() for t in ('text/html','text/plain','application/xhtml')):
            record['availability']='UNSUPPORTED_FORMAT'
        else:
            charset=re.search(r'charset=([\w-]+)',result['content_type'],re.I)
            decoded=body.decode(charset[1] if charset else 'utf-8',errors='replace')
            parser=PageText();parser.feed(decoded)
            text=normalize(' '.join(parser.parts)) if 'html' in result['content_type'].lower() else normalize(decoded)
            title=normalize(' '.join(parser.title))
            record['page_title']=title
            if re.search(r'(^|\b)(404|page not found|page cannot be found)(\b|$)',title,re.I):
                record['availability']='SOFT_NOT_FOUND'
            else:
                record['availability']='AVAILABLE'
                record['excerpt_match']=len(normalize(excerpt))>=40 and normalize(excerpt) in text
                record['eligible']=record['excerpt_match']
            record['retrieved_text']=text
        return record,body
    except (OSError,ValueError,LookupError,http.client.HTTPException) as exc:
        record['error']=str(exc);return record,b''

def record_check(evidence, directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    record,body=inspect(evidence['url'],evidence.get('excerpt',''))
    ident=record['id'];snapshot=directory/(ident+'.bin')
    snapshot.write_bytes(body)
    record['snapshot_sha256']=hashlib.sha256(body).hexdigest()
    (directory/(ident+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    pointer=directory/(key(evidence)+'.latest')
    temp=pointer.with_name(pointer.name+'.'+ident+'.tmp')
    temp.write_text(json.dumps({'id':ident}),encoding='utf-8')
    temp.replace(pointer)
    return record

def trusted(evidence,directory):
    ident=evidence.get('source_check_id','')
    if not re.fullmatch('[a-f0-9]{32}',ident):return None
    try:
        directory=Path(directory)
        record=json.loads((directory/(ident+'.json')).read_text(encoding='utf-8'))
        snapshot=(directory/(ident+'.bin')).read_bytes()
        if record['policy']!=POLICY or record['original_url']!=evidence['url']:return None
        if record['excerpt_sha256']!=hashlib.sha256(evidence.get('excerpt','').encode()).hexdigest():return None
        if record['snapshot_sha256']!=hashlib.sha256(snapshot).hexdigest():return None
        return record
    except (OSError,ValueError,KeyError):return None

def key(e):
    return hashlib.sha256((e['url']+'\n'+e.get('excerpt','')).encode()).hexdigest()

def latest(e,directory):
    try:
        pointer=json.loads((Path(directory)/(key(e)+'.latest')).read_text(encoding='utf-8'))
        return trusted({**e,'source_check_id':pointer['id']},directory)
    except (OSError,ValueError,KeyError):return None
