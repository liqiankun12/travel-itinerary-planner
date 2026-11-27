<script setup lang="ts">
import { ref,onMounted,onBeforeUnmount } from 'vue'
const trips=ref<any[]>([]), spots=ref<any[]>([]), trip=ref<any>(null), selected=ref(0)
const dirty=ref(false)
let requestSequence=0
function leaveAllowed(){return !busy.value && (!dirty.value || window.confirm('行程尚未保存，确认放弃编辑？'))}
function back(){if(leaveAllowed()){requestSequence++;trip.value=null;dirty.value=false;status.value=''}}
function unload(event:BeforeUnloadEvent){if(dirty.value || busy.value){event.preventDefault();event.returnValue=''}}
window.addEventListener('beforeunload',unload)
onBeforeUnmount(()=>window.removeEventListener('beforeunload',unload))
const name=ref('我的三日旅行'), start=ref('2026-12-01'), status=ref(''), busy=ref(false)
async function api(path:string,options:any={}) {
 const response=await fetch('/api/v1'+path,{...options,headers:{'Content-Type':'application/json'}})
 const body=await response.json()
 if(!response.ok) throw new Error(body.message || (typeof body.detail==='string'?body.detail:'请求失败，请检查输入'))
 return body.data
}
async function refresh(){ trips.value=await api('/trips');spots.value=await api('/attractions') }
async function create(){
 if(!leaveAllowed())return
 const sequence=++requestSequence
 busy.value=true
 try{
  const data=await api('/trips',{method:'POST',body:JSON.stringify({name:name.value,startDate:start.value,dayCount:3,budgetLimitCents:100000})})
  if(sequence!==requestSequence)return
  trip.value=data;selected.value=0;dirty.value=false;status.value='已创建'
  await refresh()
 }catch(e:any){if(sequence===requestSequence)status.value=e.message}
 finally{if(sequence===requestSequence)busy.value=false}
}
async function open(id:string){
 if(!leaveAllowed())return
 const sequence=++requestSequence
 busy.value=true
 try{
  const data=await api('/trips/'+id)
  if(sequence!==requestSequence)return
  trip.value=data;selected.value=0;dirty.value=false;status.value='已加载'
 }catch(e:any){if(sequence===requestSequence)status.value=e.message}
 finally{if(sequence===requestSequence)busy.value=false}
}
function add(spot:any){if(busy.value)return;const items=trip.value.days[selected.value].items;if(items.some((i:any)=>i.attractionId===spot.id)){status.value='当天已有该景点';return}items.push({id:crypto.randomUUID(),attractionId:spot.id,order:items.length,durationMinutes:60});dirty.value=true;status.value='未保存'}
function move(index:number,delta:number){if(busy.value)return;const items=trip.value.days[selected.value].items;const target=index+delta;if(target<0||target>=items.length)return;[items[index],items[target]]=[items[target],items[index]];items.forEach((i:any,n:number)=>i.order=n);dirty.value=true;status.value='未保存'}
function remove(index:number){if(busy.value)return;const items=trip.value.days[selected.value].items;items.splice(index,1);items.forEach((i:any,n:number)=>i.order=n);dirty.value=true;status.value='未保存'}
async function save(){
 if(busy.value || !trip.value)return
 const sequence=++requestSequence
 const tripId=trip.value.id
 const snapshot=JSON.stringify({...trip.value,baseRevision:trip.value.revision})
 busy.value=true
 try{
  const data=await api('/trips/'+tripId,{method:'PUT',body:snapshot})
  if(sequence!==requestSequence || trip.value?.id!==tripId)return
  trip.value=data;dirty.value=false;status.value='已保存'
  try{await refresh()}catch{status.value='已保存，列表刷新失败，可稍后重试'}
 }catch(e:any){if(sequence===requestSequence)status.value=e.message+'；当前编辑已保留'}
 finally{if(sequence===requestSequence)busy.value=false}
}
onMounted(()=>refresh().catch((e)=>status.value=e.message))
</script>
<template>
<main><header><span>旅行行程规划</span><small>把每一天安排清楚</small></header>
<p role="status">{{status}}</p>
<section v-if="!trip"><h1>下一站，去哪里？</h1><input v-model="name" aria-label="旅行名称"><input v-model="start" type="date" aria-label="开始日期"><button @click="create" :disabled="busy">创建三日旅行</button>
<h2>我的旅行</h2><button v-for="t in trips" :key="t.id" @click="open(t.id)" :disabled="busy">{{t.name}} · {{t.startDate}}</button></section>
<section v-else><nav><button @click="back" :disabled="busy">返回列表</button><h1>{{trip.name}}</h1><button @click="save" :disabled="busy">{{busy?'保存中':'保存旅行'}}</button></nav>
<div class="workspace"><aside><h2>发现景点</h2><article v-for="s in spots" :key="s.id"><h3>{{s.name}}</h3><p>参考门票 ¥{{s.ticketCents/100}}</p><button @click="add(s)" :disabled="busy">加入当天</button></article></aside>
<div><nav><button v-for="(d,i) in trip.days" :key="d.id" @click="selected=Number(i)">第{{d.dayIndex}}天</button></nav>
<p>09:00 出发 · 21:00 结束</p><article v-for="(item,i) in trip.days[selected].items" :key="item.id"><h3>{{Number(i)+1}} · {{spots.find(s=>s.id===item.attractionId)?.name}}</h3><p>停留 {{item.durationMinutes}} 分钟</p><button @click="move(Number(i),-1)" :disabled="busy">上移</button><button @click="move(Number(i),1)" :disabled="busy">下移</button><button @click="remove(Number(i))" :disabled="busy">删除</button></article><p v-if="!trip.days[selected].items.length">从左侧加入第一个景点。</p></div></div></section>
</main>
</template>
<style>
body{margin:0;background:#f5f3ec;color:#223e39;font-family:Arial,'Microsoft YaHei',sans-serif}main{max-width:1100px;margin:auto;padding:36px}header,nav{display:flex;align-items:center;gap:20px}header{border-bottom:1px solid #ccc;padding-bottom:20px}small{color:#667}h1{font-size:32px}button,input{padding:12px;margin:5px;border:1px solid #b9c9c0;border-radius:8px;background:white;color:#223e39}button{cursor:pointer}button:disabled{opacity:.5}.workspace{display:grid;grid-template-columns:300px 1fr;gap:32px}article{background:white;border-radius:12px;padding:18px;margin:14px 0}button:hover{background:#dbe9dc}@media(max-width:700px){.workspace{grid-template-columns:1fr}main{padding:15px}}
</style>
