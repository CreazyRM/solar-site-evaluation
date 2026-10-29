"""Anonymous bounded HTTP, reusable cache and immutable retrieval provenance."""
import hashlib
import json
import socket
import threading
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, parse_qsl
from urllib.request import Request, urlopen
import assess

MAX_BYTES=20_000_000

def check_url(url):
    parsed=urlparse(url)
    host=(parsed.hostname or '').lower()
    if parsed.scheme not in ('http','https') or not host or parsed.username or parsed.password:
        raise ValueError('Anonymous HTTP(S) URL required.')
    if host=='geowarehouse.ca' or host.endswith('.geowarehouse.ca'):
        raise assess.Unavailable('source_excluded_by_user_geowarehouse')
    if any(k.lower() in ('token','access_token','password','authorization','api_key','apikey') for k,_ in parse_qsl(parsed.query)):
        raise ValueError('Authenticated URL is not supported.')

class EvidenceClient:
    def __init__(self, cache, offline=False, timeout=15):
        if not 0<timeout<=60:
            raise ValueError('Timeout must be positive and at most 60 seconds.')
        self.cache=Path(cache);self.offline=offline;self.timeout=timeout
        self.cache.mkdir(parents=True,exist_ok=True)
        self.lock=threading.Lock()

    def fetch(self,url,params=None,method='GET',ttl=0,binary=False):
        check_url(url)
        params=params or {}
        if method not in ('GET','POST') or ttl<0:
            raise ValueError('Unsupported method or negative cache TTL.')
        if any(k.lower() in ('token','access_token','password','authorization','api_key','apikey') for k in params):
            raise ValueError('Authenticated parameters are not supported.')
        identity=json.dumps([url,params,method,binary],sort_keys=True,separators=(',',':'))
        key=hashlib.sha256(identity.encode()).hexdigest()
        meta_path=self.cache/(key+'.json');blob_path=self.cache/(key+'.bin')
        now=time.time()
        if meta_path.exists():
            cached=json.loads(meta_path.read_text(encoding='utf-8'))
            age=max(0,now-cached['cached_epoch'])
            if (self.offline or (ttl>0 and age<=ttl)) and (not binary or blob_path.exists()):
                record={**cached,'cache_hit':True,'cache_age_seconds':age,'reused_offline':self.offline}
                return record,blob_path.read_bytes() if binary else cached['data']
        if self.offline:
            raise assess.Unavailable('offline_cache_miss')
        encoded=urlencode(params).encode()
        target=url+('' if not params or method=='POST' else ('&' if '?' in url else '?')+encoded.decode())
        request=Request(target,data=encoded if method=='POST' else None,headers={'User-Agent':'OntarioSolarEvaluation/2.0','Accept':'*/*' if binary else 'application/json'})
        for attempt in range(2):
            try:
                with urlopen(request,timeout=self.timeout) as response:
                    final=response.geturl();check_url(final)
                    if any(x in urlparse(final).path.lower() for x in ('/login','/signin')):
                        raise assess.Unavailable('authentication_required')
                    raw=response.read(MAX_BYTES+1)
                    mime=response.headers.get('Content-Type','')
                if len(raw)>MAX_BYTES:
                    raise assess.Unavailable('response_too_large')
                if binary:
                    data=None
                else:
                    try:data=json.loads(raw)
                    except (ValueError,UnicodeError):raise assess.Unavailable('non_json_response')
                    if isinstance(data,dict) and data.get('error'):
                        code=data['error'].get('code') if isinstance(data['error'],dict) else None
                        raise assess.Unavailable('authentication_required' if code in (401,498,499) else 'access_denied' if code==403 else 'service_error')
                record={'source':url,'request':params,'method':method,'retrieved_at':assess.utc_now(),'cached_epoch':time.time(),'content_type':mime,'sha256':hashlib.sha256(raw).hexdigest(),'data':data}
                with self.lock:
                    if binary:
                        temporary=blob_path.with_suffix('.tmp');temporary.write_bytes(raw);temporary.replace(blob_path)
                    temporary=meta_path.with_suffix('.json.tmp');assess.save_json(temporary,record);temporary.replace(meta_path)
                return {**record,'cache_hit':False,'reused_offline':False},raw if binary else data
            except HTTPError as exc:
                raise assess.Unavailable('authentication_required' if exc.code==401 else 'access_denied' if exc.code==403 else f'http_{exc.code}') from exc
            except (TimeoutError,socket.timeout) as exc:
                if attempt:raise assess.Unavailable('timeout') from exc
            except URLError as exc:
                if isinstance(exc.reason,(TimeoutError,socket.timeout)) and attempt==0:continue
                raise assess.Unavailable('timeout' if isinstance(exc.reason,(TimeoutError,socket.timeout)) else 'network_unavailable') from exc

    def json(self,url,params=None,method='GET',ttl=0):
        return self.fetch(url,params,method,ttl,False)

    def download(self,url,destination,params=None,ttl=0):
        record,data=self.fetch(url,params,ttl=ttl,binary=True)
        destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(data)
        assess.save_json(destination.with_suffix(destination.suffix+'.provenance.json'),{k:v for k,v in record.items() if k!='data'})
        return record,str(destination.resolve())
