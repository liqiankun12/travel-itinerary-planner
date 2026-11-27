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

 import copy
 baseline=req('/trips/'+trip['id'])[1]['data']
 baseline['baseRevision']=baseline['revision']
 mutations=[
  lambda b:b.update(days=None),
  lambda b:b.update(days={}),
  lambda b:b['days'][0].update(items='bad'),
  lambda b:b['days'][0].update(items=[None]),
  lambda b:b['days'][0].update(expenses=[{'id':'e1','name':'food','amountCents':-1}]),
  lambda b:b['days'][0].update(expenses=[{'id':'e1','name':'food','amountCents':1.5}]),
  lambda b:b['days'][0].update(expenses=[{'id':'e1','name':'food','amountCents':True}]),
  lambda b:b['days'][0].update(expenses=[{'id':'e1','name':'food','amountCents':100000001}]),
  lambda b:b['days'][0].update(startMinutes='09:00'),
  lambda b:b['days'][0]['items'][0].update(durationMinutes=True),
  lambda b:b['days'][1].update(id=b['days'][0]['id']),
  lambda b:b.update(baseRevision=True),
 ]
 for mutation in mutations:
  bad=copy.deepcopy(baseline);mutation(bad)
  status,error=req('/trips/'+trip['id'],bad,'PUT')
  assert status==400,(status,error)
  assert error['code']=='VALIDATION_ERROR'
  assert req('/trips/'+trip['id'])[1]['data']['revision']==baseline['revision']
 assert req('/trips/999999',baseline,'PUT')[0]==404
 valid=copy.deepcopy(baseline)
 valid['days'][0]['expenses']=[{'id':'food','name':'餐费','amountCents':2300}]
 status,saved=req('/trips/'+trip['id'],valid,'PUT')
 assert status==200 and saved['code']=='TRIP_SAVED'
 assert saved['data']['days'][0]['expenses'][0]['amountCents']==2300

 server.should_exit=True;thread.join(5)
print('PASS stability HTTP: baseline plus 12 malformed input cases, rollback, 404/409, valid expenses and TRIP_SAVED')
