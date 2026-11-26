import sys,tempfile,threading,time,json,urllib.request,urllib.error
from pathlib import Path
sys.path.insert(0,str((Path(__file__).resolve().parents[1]/'backend')))
import main,uvicorn
with tempfile.TemporaryDirectory() as folder:
 main.DB=Path(folder)/'test.db'
 server=uvicorn.Server(uvicorn.Config(main.app,host='127.0.0.1',port=18001,log_level='error'))
 thread=threading.Thread(target=server.run,daemon=True);thread.start()
 for i in range(100):
  if server.started:break
  time.sleep(.05)
 def req(path,body=None,method=None):
  request=urllib.request.Request('http://127.0.0.1:18001/api/v1'+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'},method=method)
  try:
   with urllib.request.urlopen(request) as r:return r.status,json.load(r)
  except urllib.error.HTTPError as e:return e.code,json.load(e)
 status,response=req('/trips',{'name':'验证旅行','startDate':'2026-12-01','dayCount':3,'budgetLimitCents':10000})
 assert status==201
 trip=response['data'];assert len(trip['days'])==3
 trip['days'][0]['items']=[{'id':'item-1','attractionId':'spot-1','order':0,'durationMinutes':60}]
 trip['baseRevision']=trip['revision']
 assert req('/trips/'+trip['id'],trip,'PUT')[0]==200
 assert req('/trips/'+trip['id'])[1]['data']['days'][0]['items'][0]['id']=='item-1'
 assert req('/trips/'+trip['id'],trip,'PUT')[0]==409
 latest=req('/trips/'+trip['id'])[1]['data'];latest['baseRevision']=latest['revision'];latest['days'][0]['items'][0]['attractionId']='invalid'
 assert req('/trips/'+trip['id'],latest,'PUT')[0]==400
 assert req('/trips/'+trip['id'])[1]['data']['days'][0]['items'][0]['attractionId']=='spot-1'
 server.should_exit=True;thread.join(5)
print('PASS HTTP creation, 3 days, save/reload, stale revision, invalid-reference rollback')
