import os, time, json, re, math, sqlite3, asyncio, hashlib
from datetime import datetime, timezone, timedelta
from typing import Any
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()
FINNHUB=os.getenv('FINNHUB_API_KEY','').strip()
TWELVE=os.getenv('TWELVE_DATA_API_KEY','').strip()
OPENAI=os.getenv('OPENAI_API_KEY','').strip()
MODEL=os.getenv('OPENAI_MODEL','gpt-5.6-luna').strip()
CACHE_SECONDS=int(os.getenv('CACHE_SECONDS','30'))
NEWS_SYNC_MINUTES=max(1,int(os.getenv('NEWS_SYNC_MINUTES','5')))
DB_PATH=os.getenv('NEWS_DB_PATH','cahyonews_ai.db')

app=FastAPI(title='Cahyonews AI API',version='9.0')
origins=[x.strip() for x in os.getenv('CORS_ORIGINS','*').split(',') if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
_cache={}
_sync_lock=asyncio.Lock()

async def get_json(url,params=None):
    async with httpx.AsyncClient(timeout=20,follow_redirects=True) as c:
        r=await c.get(url,params=params); r.raise_for_status(); return r.json()

def cache_get(k):
    v=_cache.get(k)
    return v[1] if v and time.time()-v[0]<CACHE_SECONDS else None

def cache_put(k,v): _cache[k]=(time.time(),v); return v

def num(v):
    try:return float(str(v).replace(',','').replace('%',''))
    except:return None

def db():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c

def init_db():
    c=db(); c.executescript('''
    CREATE TABLE IF NOT EXISTS news_archive(
      uid TEXT PRIMARY KEY, headline TEXT NOT NULL, summary TEXT DEFAULT '', source TEXT DEFAULT '',
      url TEXT DEFAULT '', published_at INTEGER NOT NULL, category TEXT DEFAULT 'general',
      sentiment TEXT DEFAULT '', xau_score REAL DEFAULT 0, raw_json TEXT DEFAULT '{}', first_seen INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_news_time ON news_archive(published_at DESC);
    CREATE INDEX IF NOT EXISTS idx_news_xau ON news_archive(xau_score DESC,published_at DESC);
    CREATE TABLE IF NOT EXISTS economic_archive(
      uid TEXT PRIMARY KEY,name TEXT,country TEXT,timestamp INTEGER,impact TEXT,forecast TEXT,previous TEXT,actual TEXT,raw_json TEXT,first_seen INTEGER
    );
    CREATE INDEX IF NOT EXISTS idx_econ_time ON economic_archive(timestamp DESC);
    CREATE TABLE IF NOT EXISTS market_archive(
      id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp INTEGER,symbol TEXT,price REAL,change REAL,intelligence_json TEXT DEFAULT ''
    );
    CREATE INDEX IF NOT EXISTS idx_market_time ON market_archive(timestamp DESC);
    CREATE TABLE IF NOT EXISTS intelligence_archive(
      id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp INTEGER,signal TEXT,confidence INTEGER,bias TEXT,payload_json TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_intel_time ON intelligence_archive(timestamp DESC);
    '''); c.commit(); c.close()
init_db()

XAU_TERMS={'gold':3,'xau':5,'xauusd':5,'bullion':4,'precious metal':4,'gold price':5}
MACRO_TERMS={'fed':2,'fomc':2,'powell':2,'interest rate':2,'inflation':2,'cpi':3,'ppi':3,'nfp':3,'payroll':2,'jobs':1,'employment':2,'treasury yield':3,'bond yield':3,'dollar':2,'usd':2,'dxy':3,'gdp':2,'retail sales':2,'pce':3,'unemployment':2}
GEO_TERMS={'war':2,'iran':2,'israel':2,'ukraine':2,'russia':2,'tariff':2,'trade war':3,'sanction':2,'geopolit':2,'safe haven':3,'crisis':2}

def news_relevance(h):
    h=h.lower(); return min(10,sum(v for k,v in {**XAU_TERMS,**MACRO_TERMS,**GEO_TERMS}.items() if k in h))

def simple_sentiment(h):
    h=h.lower()
    pos=['hawkish','strong','higher','beat','beats','surge','rises','rise','support','bullish','safe haven','geopolitical risk']
    neg=['dovish','weak','lower','miss','falls','fall','drop','bearish','recession','rate cut']
    p=sum(w in h for w in pos); n=sum(w in h for w in neg)
    return 'bullish_gold' if p>n else 'bearish_gold' if n>p else 'neutral'

def archive_news(rows):
    c=db(); now=int(time.time()); added=0
    for x in rows:
        headline=str(x.get('headline') or x.get('title') or '').strip()
        if not headline: continue
        ts=int(x.get('datetime') or x.get('published_at') or x.get('timestamp') or now)
        source=str(x.get('source') or x.get('domain') or '').strip()
        url=str(x.get('url') or '').strip()
        uid=hashlib.sha256((headline+'|'+source+'|'+url+'|'+str(ts//60)).encode()).hexdigest()
        score=news_relevance(headline)
        sent=simple_sentiment(headline)
        c.execute('''INSERT OR IGNORE INTO news_archive(uid,headline,summary,source,url,published_at,category,sentiment,xau_score,raw_json,first_seen)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?)''',(uid,headline,str(x.get('summary') or x.get('description') or ''),source,url,ts,str(x.get('category') or 'general'),sent,score,json.dumps(x,ensure_ascii=False),now))
        added += c.execute('SELECT changes()').fetchone()[0]
    c.commit(); c.close(); return added

def parse_ts(v):
    try:
        if isinstance(v,(int,float)): return int(v)
        s=str(v).strip().replace('Z','+00:00')
        return int(datetime.fromisoformat(s).timestamp())
    except Exception:
        for fmt in ('%Y-%m-%d %H:%M:%S','%Y-%m-%d','%Y%m%d%H%M%S'):
            try:return int(datetime.strptime(str(v)[:19],fmt).replace(tzinfo=timezone.utc).timestamp())
            except Exception:pass
    return int(time.time())

def norm_event(x):
    ts=parse_ts(x.get('time') or x.get('datetime') or x.get('date'))
    return {'name':x.get('event') or x.get('name') or 'event','date':datetime.fromtimestamp(ts,timezone.utc).strftime('%a, %d %b %Y'),'timestamp':ts,
            'impact':str(x.get('impact') or x.get('importance') or 'MEDIUM').upper(),'forecast':str(x.get('estimate') or x.get('forecast') or ''),
            'previous':str(x.get('prev') or x.get('previous') or ''),'actual':x.get('actual')}

async def calendar_data(days_back=2,days_forward=7):
    if not FINNHUB: raise HTTPException(503,'FINNHUB_API_KEY belum diisi')
    today=datetime.now(timezone.utc).date()
    data=await get_json('https://finnhub.io/api/v1/calendar/economic',{'from':str(today-timedelta(days=days_back)),'to':str(today+timedelta(days=days_forward)),'token':FINNHUB})
    rows=data.get('economicCalendar',data.get('calendar',[]))
    events=[]
    for x in rows:
        country=str(x.get('country','')).upper()
        if country in ('US','UNITED STATES','USD') or not country:
            events.append(norm_event(x))
    events.sort(key=lambda e:e['timestamp']); return events

@app.get('/api/status')
async def status():
    return {
        'app': 'Cahyonews AI API',
        'version': '10.0-rc',
        'providers': {
            'finnhub': bool(FINNHUB),
            'twelve_data': bool(TWELVE),
            'openai': bool(OPENAI),
        },
        'ai': {'enabled': bool(OPENAI), 'model_configured': bool(MODEL)},
        'database': DB_PATH,
        'cache_seconds': CACHE_SECONDS,
        'news_sync_minutes': NEWS_SYNC_MINUTES,
        'ready': bool(FINNHUB and TWELVE),
    }

@app.get('/api/health')
async def health():
    c=db(); counts={'news':c.execute('SELECT COUNT(*) FROM news_archive').fetchone()[0],'economic':c.execute('SELECT COUNT(*) FROM economic_archive').fetchone()[0],'market':c.execute('SELECT COUNT(*) FROM market_archive').fetchone()[0]}; c.close()
    return {'ok':True,'version':'9.0','providers':{'finnhub':bool(FINNHUB),'twelvedata':bool(TWELVE),'openai':bool(OPENAI),'gdelt':True},'archive':counts,'sync_minutes':NEWS_SYNC_MINUTES}

@app.get('/api/xauusd')
async def xauusd():
    if not TWELVE: raise HTTPException(503,'TWELVE_DATA_API_KEY belum diisi')
    hit=cache_get('xauusd');
    if hit:return hit
    data=await get_json('https://api.twelvedata.com/quote',{'symbol':'XAU/USD','apikey':TWELVE})
    if data.get('status')=='error':raise HTTPException(502,data.get('message','Twelve Data error'))
    out={'symbol':'XAUUSD','price':float(data.get('close') or data.get('price') or 0),'change':float(data.get('change') or 0),'timestamp':int(data.get('timestamp') or time.time())}
    c=db(); c.execute('INSERT INTO market_archive(timestamp,symbol,price,change) VALUES(?,?,?,?)',(out['timestamp'],out['symbol'],out['price'],out['change'])); c.commit(); c.close()
    return cache_put('xauusd',out)

@app.get('/api/calendar')
async def calendar(): return await calendar_data()

async def fetch_finnhub_news():
    if not FINNHUB:return []
    try:
        data=await get_json('https://finnhub.io/api/v1/news',{'category':'general','token':FINNHUB})
        return data[:100] if isinstance(data,list) else []
    except Exception:return []

async def fetch_gdelt(query, start=None, end=None, maxrecords=250):
    p={'query':query,'mode':'ArtList','format':'json','maxrecords':maxrecords,'sort':'HybridRel'}
    if start:p['startdatetime']=start.strftime('%Y%m%d%H%M%S')
    if end:p['enddatetime']=end.strftime('%Y%m%d%H%M%S')
    try:return (await get_json('https://api.gdeltproject.org/api/v2/doc/doc',p)).get('articles',[])
    except Exception:return []

NEWS_QUERY='(gold OR XAUUSD OR bullion OR "Federal Reserve" OR FOMC OR CPI OR PPI OR NFP OR payroll OR Treasury OR DXY OR inflation OR "interest rate" OR tariff OR war OR geopolitical)'
async def broad_news(start=None,end=None):
    rows=[]
    if start is None and end is None: rows += await fetch_finnhub_news()
    for x in await fetch_gdelt(NEWS_QUERY,start,end,250):
        rows.append({'headline':x.get('title'),'url':x.get('url'),'source':x.get('domain'),'datetime':parse_ts(x.get('seendate')),'category':'gdelt'})
    archive_news(rows); return rows

async def sync_archive():
    async with _sync_lock:
        await broad_news()
        if FINNHUB:
            try:
                events=await calendar_data(2,7); c=db(); now=int(time.time())
                for x in events:
                    uid=hashlib.sha256((x['name']+'|'+str(x['timestamp'])).encode()).hexdigest()
                    c.execute('INSERT OR REPLACE INTO economic_archive(uid,name,country,timestamp,impact,forecast,previous,actual,raw_json,first_seen) VALUES(?,?,?,?,?,?,?,?,?,?)',
                              (uid,x['name'],'US',x['timestamp'],x['impact'],x['forecast'],x['previous'],str(x['actual'] if x['actual'] is not None else ''),json.dumps(x),now))
                c.commit();c.close()
            except Exception:pass

@app.on_event('startup')
async def startup(): asyncio.create_task(archive_loop())

async def archive_loop():
    while True:
        try: await sync_archive()
        except Exception: pass
        await asyncio.sleep(NEWS_SYNC_MINUTES*60)

@app.get('/api/news/history')
async def news_history(limit:int=100,offset:int=0,q:str='',xau_only:bool=False):
    limit=max(1,min(limit,500)); offset=max(0,offset); c=db(); where=[];args=[]
    if q:where.append('(headline LIKE ? OR summary LIKE ? OR source LIKE ?)');args += [f'%{q}%',f'%{q}%',f'%{q}%']
    if xau_only:where.append('xau_score>0')
    w=(' WHERE '+' AND '.join(where)) if where else ''
    rows=c.execute(f'SELECT headline,summary,source,url,published_at,category,sentiment,xau_score FROM news_archive{w} ORDER BY published_at DESC LIMIT ? OFFSET ?',args+[limit,offset]).fetchall()
    total=c.execute(f'SELECT COUNT(*) FROM news_archive{w}',args).fetchone()[0];c.close()
    return {'total':total,'limit':limit,'offset':offset,'items':[dict(r) for r in rows]}

@app.get('/api/news/xauusd')
async def news_xauusd(limit:int=100):return await news_history(limit=limit,xau_only=True)

@app.post('/api/news/sync')
async def news_sync():
    c=db();before=c.execute('SELECT COUNT(*) FROM news_archive').fetchone()[0];c.close();await sync_archive();c=db();after=c.execute('SELECT COUNT(*) FROM news_archive').fetchone()[0];c.close();return {'ok':True,'added':after-before,'total':after}

@app.post('/api/news/backfill')
async def news_backfill(start:str='2000-01-01',end:str='now'):
    try:
        a=datetime.fromisoformat(start).replace(tzinfo=timezone.utc) if 'T' not in start else datetime.fromisoformat(start).astimezone(timezone.utc)
        b=datetime.now(timezone.utc) if end=='now' else (datetime.fromisoformat(end).replace(tzinfo=timezone.utc) if 'T' not in end else datetime.fromisoformat(end).astimezone(timezone.utc))
    except Exception: raise HTTPException(400,'format tanggal harus YYYY-MM-DD atau ISO8601')
    if b<a:raise HTTPException(400,'end harus >= start')
    total_added=0;cur=a
    # GDELT queries are chunked to reduce missed results and provider timeouts.
    while cur<b:
        nxt=min(cur+timedelta(days=30),b)
        rows=await broad_news(cur,nxt);total_added += len(rows);cur=nxt
        await asyncio.sleep(.15)
    c=db();total=c.execute('SELECT COUNT(*) FROM news_archive').fetchone()[0];c.close()
    return {'ok':True,'requested_start':start,'requested_end':end,'provider':'GDELT'+(' + Finnhub current feed' if FINNHUB else ''),'raw_batches':total_added,'archive_total':total,
            'note':'provider availability limits historical completeness; this is not a claim that every article ever published is recoverable.'}

async def candles(interval='15min',outputsize=180):
    if not TWELVE: raise HTTPException(503,'TWELVE_DATA_API_KEY belum diisi')
    data=await get_json('https://api.twelvedata.com/time_series',{'symbol':'XAU/USD','interval':interval,'outputsize':outputsize,'apikey':TWELVE})
    if data.get('status')=='error':raise HTTPException(502,data.get('message','Twelve Data error'))
    return [{'open':float(x['open']),'high':float(x['high']),'low':float(x['low']),'close':float(x['close'])} for x in reversed(data.get('values',[]))]

def ema(v,p):
    if len(v)<p:return None
    k=2/(p+1);e=sum(v[:p])/p
    for x in v[p:]:e=x*k+e*(1-k)
    return e

def rsi(v,p=14):
    if len(v)<=p:return None
    g=[];l=[]
    for i in range(1,len(v)):
        d=v[i]-v[i-1];g.append(max(d,0));l.append(max(-d,0))
    ag=sum(g[:p])/p;al=sum(l[:p])/p
    for i in range(p,len(g)):ag=(ag*(p-1)+g[i])/p;al=(al*(p-1)+l[i])/p
    return 100 if al==0 else 100-(100/(1+ag/al))

def macd(v):
    a,b=ema(v,12),ema(v,26);return None if a is None or b is None else a-b

def atr(c,p=14):
    if len(c)<p+1:return None
    trs=[]
    for i in range(1,len(c)):
        h,l,pc=c[i]['high'],c[i]['low'],c[i-1]['close'];trs.append(max(h-l,abs(h-pc),abs(l-pc)))
    return sum(trs[-p:])/p

async def technical_snapshot():
    frames={};raw={}
    for tf in ('5min','15min','1h','4h'):
        c=await candles(tf,180);raw[tf]=c;cl=[x['close'] for x in c];last=c[-1]
        hi=max(x['high'] for x in c[-20:]);lo=min(x['low'] for x in c[-20:]);rng=max(hi-lo,1e-9)
        frames[tf]={'close':cl[-1],'ema20':ema(cl,20),'ema50':ema(cl,50),'rsi14':rsi(cl),'macd':macd(cl),'atr14':atr(c),'high20':hi,'low20':lo,
                    'range_position':(last['close']-lo)/rng,'wick_up':last['high']-max(last['open'],last['close']),'wick_down':min(last['open'],last['close'])-last['low']}
    return frames,raw

def psychology_engine(t,raw):
    score=0;reasons=[]
    for tf,w in (('5min',1),('15min',1),('1h',2),('4h',2)):
        x=t.get(tf,{})
        if x.get('ema20') and x.get('ema50'):score += w if x['ema20']>x['ema50'] else -w
        r=x.get('rsi14')
        if r is not None:
            if r>72:score-=w;reasons.append(f'{tf} overbought/exhaustion')
            elif r<28:score+=w;reasons.append(f'{tf} oversold/reversal')
    x=t.get('15min',{});c=raw.get('15min',[])
    if c:
        last=c[-1];hi=x.get('high20',0);lo=x.get('low20',0)
        # use prior 20-candle levels so the current candle can actually sweep them
        prior=c[-21:-1] if len(c)>=21 else c[:-1]
        if prior:
            ph=max(z['high'] for z in prior);pl=min(z['low'] for z in prior)
            if last['high']>ph and last['close']<ph:score-=2;reasons.append('liquidity sweep above resistance')
            if last['low']<pl and last['close']>pl:score+=2;reasons.append('liquidity sweep below support')
        pos=x.get('range_position',.5)
        if pos>.9:reasons.append('price near range high')
        if pos<.1:reasons.append('price near range low')
    score=max(-10,min(10,score))
    return {'score':score,'bias':'bullish psychology' if score>1 else 'bearish psychology' if score<-1 else 'mixed/neutral psychology','reasons':reasons[-8:]}

def fundamental_engine(events):
    now=int(time.time());e=next((x for x in events if x['timestamp']>=now),None) or (events[-1] if events else None);score=0;reasons=[]
    if not e:return {'score':0,'bias':'neutral','event':None,'reason':'no macro event'}
    if e['impact']=='HIGH':reasons.append('high-impact macro risk')
    f,p,a=num(e['forecast']),num(e['previous']),num(e['actual']);ref=a if a is not None and e['timestamp']<=now else f;name=e['name'].lower()
    if ref is not None and p is not None:
        d=ref-p
        if any(k in name for k in ('cpi','ppi','inflation','payroll','nfp','employment','jobs','retail sales','gdp','pce')):
            if d>0:score+=1;reasons.append('macro reading stronger than previous')
            elif d<0:score-=1;reasons.append('macro reading weaker than previous')
        if any(k in name for k in ('fed','fomc','interest rate','policy rate')):
            if d>0:score+=2;reasons.append('rate-policy impulse favors USD')
            elif d<0:score-=2;reasons.append('rate-policy impulse favors gold')
    return {'score':max(-5,min(5,score)),'bias':'USD bullish / gold bearish' if score>0 else 'USD bearish / gold bullish' if score<0 else 'neutral','event':e,'reason':'; '.join(reasons) or 'no strong directional macro differential'}

def news_engine(news):
    score=0;hits=[]
    for n in news[:100]:
        s=n.get('sentiment');w=max(.25,min(2,n.get('xau_score',0)/5))
        if s=='bullish_gold':score+=w;hits.append({'headline':n['headline'],'effect':'gold+'})
        elif s=='bearish_gold':score-=w;hits.append({'headline':n['headline'],'effect':'gold-'})
    score=max(-10,min(10,score/5));return {'score':round(score,2),'bias':'gold bullish' if score>1 else 'gold bearish' if score<-1 else 'mixed/neutral','hits':hits[:8]}

async def intelligence():
    events=await calendar_data();market=await xauusd();await broad_news();c=db();rows=c.execute('SELECT headline,summary,source,url,published_at,category,sentiment,xau_score FROM news_archive ORDER BY published_at DESC LIMIT 100').fetchall();c.close();news=[dict(r) for r in rows]
    f=fundamental_engine(events);n=news_engine(news)
    try:t,raw=await technical_snapshot()
    except Exception:t,raw={},{}
    p=psychology_engine(t,raw);tech=0
    for tf,w in (('5min',.5),('15min',1),('1h',1.5),('4h',2)):
        x=t.get(tf,{})
        if x.get('ema20') and x.get('ema50'):tech += w if x['ema20']>x['ema50'] else -w
        if x.get('rsi14') is not None:tech += .5*w if x['rsi14']>55 else -.5*w if x['rsi14']<45 else 0
        if x.get('macd') is not None:tech += .5*w if x['macd']>0 else -.5*w
    combined=tech+f['score']*.9+p['score']*.35+n['score']*.5
    event=f.get('event');delta=(event['timestamp']-int(time.time())) if event else 999999
    risk='HIGH' if event and event['impact']=='HIGH' and 0<=delta<=1800 else 'MEDIUM' if event and event['impact']=='HIGH' else 'LOW'
    signal='BUY' if combined>=2.5 else 'SELL' if combined<=-2.5 else 'WAIT'
    if risk=='HIGH' and abs(combined)<4:signal='WAIT'
    confidence=min(95,max(50,int(50+min(abs(combined)/10,1)*45)))
    result={'event':'DAILY XAUUSD INTELLIGENCE','signal':signal,'confidence':confidence,'bias':'bullish XAUUSD' if signal=='BUY' else 'bearish XAUUSD' if signal=='SELL' else 'neutral / conflicting evidence',
            'reason':' | '.join([f['reason'],'; '.join(p['reasons'][-2:]) if p['reasons'] else 'psychology mixed',n['bias'],f'technical score {tech:.1f}']),
            'generatedAt':int(time.time()),'technical':t,'fundamental':f,'psychology':p,'news':n,'newsRisk':risk,'aiStatus':'rules'}
    if OPENAI:
        try:
            from openai import AsyncOpenAI
            client=AsyncOpenAI(api_key=OPENAI)
            prompt={'role':'senior XAUUSD quantitative analyst','task':'Return JSON only. Integrate multi-timeframe technicals, macro fundamentals, market psychology and recent news. Conservative decision; WAIT when evidence conflicts or high-impact news is imminent. Never promise profit. Fields: signal BUY/SELL/WAIT, confidence 0-100, bias, reason, invalidation, entryZone, slLogic, tpLogic. Do not invent missing data.','market':market,'technical':t,'fundamental':f,'psychology':p,'news':n,'newsRisk':risk,'preSignal':result}
            r=await client.responses.create(model=MODEL,input=json.dumps(prompt));txt=r.output_text.strip();obj=json.loads(txt[txt.find('{'):txt.rfind('}')+1])
            result.update({'signal':str(obj.get('signal',signal)).upper(),'confidence':max(0,min(100,int(obj.get('confidence',confidence)))),'bias':str(obj.get('bias',result['bias'])),'reason':str(obj.get('reason',result['reason'])),'invalidation':str(obj.get('invalidation','')),'entryZone':str(obj.get('entryZone','')),'slLogic':str(obj.get('slLogic','')),'tpLogic':str(obj.get('tpLogic','')),'aiStatus':'live'})
        except Exception as e:result['aiStatus']='fallback'
    c=db();c.execute('INSERT INTO intelligence_archive(timestamp,signal,confidence,bias,payload_json) VALUES(?,?,?,?,?)',(result['generatedAt'],result['signal'],result['confidence'],result['bias'],json.dumps(result,ensure_ascii=False)));c.commit();c.close();return result

@app.get('/api/technical')
async def technical():return (await technical_snapshot())[0]
@app.get('/api/intelligence')
async def api_intelligence():return await intelligence()
@app.get('/api/daily-signal')
async def daily_signal():return await intelligence()

@app.get('/api/intelligence/history')
async def intelligence_history(limit:int=50):
    c=db();rows=c.execute('SELECT timestamp,signal,confidence,bias,payload_json FROM intelligence_archive ORDER BY timestamp DESC LIMIT ?',(max(1,min(limit,200)),)).fetchall();c.close();return [dict(r) for r in rows]

async def event_signal():
    events=await calendar_data();market=await xauusd()
    if not events:return None
    f=fundamental_engine(events);base={'event':events[0]['name'],'signal':'WAIT','confidence':50,'bias':f['bias'],'reason':f['reason'],'generatedAt':int(time.time())}
    if OPENAI:
        try:
            from openai import AsyncOpenAI
            r=await AsyncOpenAI(api_key=OPENAI).responses.create(model=MODEL,input=json.dumps({'task':'Assess immediate XAUUSD reaction risk to this US macro event. JSON only: signal BUY/SELL/WAIT, confidence, bias, reason. Conservative, never guarantee profit.','event':events[0],'market':market,'fundamental':f}))
            txt=r.output_text.strip();o=json.loads(txt[txt.find('{'):txt.rfind('}')+1]);base.update({'signal':str(o.get('signal','WAIT')).upper(),'confidence':int(o.get('confidence',50)),'bias':str(o.get('bias',f['bias'])),'reason':str(o.get('reason',f['reason']))})
        except Exception:pass
    return base
@app.get('/api/signal')
async def signal():return await event_signal()
@app.get('/api/dashboard')
async def dashboard():
    events=await calendar_data();market=await xauusd();sig=await event_signal();intel=await intelligence();return {'nextEvent':events[0] if events else None,'market':market,'signal':sig,'daily':intel,'events':events[:10]}
