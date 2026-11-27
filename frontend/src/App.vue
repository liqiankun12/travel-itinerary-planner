<script setup lang="ts">
import { ref,computed,onMounted,onBeforeUnmount } from 'vue'
interface ItineraryItem { id:string; attractionId:string; order:number; durationMinutes:number }
interface DayPlan { id:string; dayIndex:number; startMinutes:number; endMinutes:number; items:ItineraryItem[]; expenses:unknown[] }
interface Trip { id:string; name:string; startDate:string; dayCount:number; budgetLimitCents:number; revision:number; days:DayPlan[] }
interface Spot { id:string; name:string; ticketCents:number; defaultDurationMinutes?:number; category?:string; image?:string; description?:string; openMinutes?:number; closeMinutes?:number }
const trips=ref<Trip[]>([]), spots=ref<Spot[]>([]), trip=ref<Trip|null>(null), selected=ref(0)
const query=ref(''), category=ref('全部'), detail=ref<Spot|null>(null), dialog=ref<HTMLDialogElement|null>(null)
const categories=computed(()=>['全部',...new Set(spots.value.map(s=>s.category).filter((c):c is string=>Boolean(c)))])
const filteredSpots=computed(()=>spots.value.filter(s=>s.name.includes(query.value.trim()) && (category.value==='全部'||s.category===category.value)))
const currentItems=computed(()=>trip.value?.days[selected.value]?.items ?? [])
const totalItems=computed(()=>trip.value?.days.reduce((n,d)=>n+d.items.length,0) ?? 0)
const dayMinutes=computed(()=>currentItems.value.reduce((n,item)=>n+item.durationMinutes,0))
const ticketSubtotal=computed(()=>currentItems.value.reduce((n,item)=>n+(spots.value.find(s=>s.id===item.attractionId)?.ticketCents ?? 0),0))
const saveLabel=computed(()=>busy.value?'正在处理':dirty.value?'有未保存修改':'已同步')
function money(cents:number){return (cents/100).toFixed(2)}
function clock(minutes:number){return String(Math.floor(minutes/60)).padStart(2,'0')+':'+String(minutes%60).padStart(2,'0')}
function dayDate(index:number){
 if(!trip.value)return ''
 const date=new Date(trip.value.startDate+'T12:00:00')
 date.setDate(date.getDate()+index)
 return (date.getMonth()+1)+'月'+date.getDate()+'日'
}
function findSpot(id:string){return spots.value.find(s=>s.id===id)}
function showDetails(spot:Spot){detail.value=spot;dialog.value?.showModal()}
function imageFor(spot:Spot){return spot.image || '/images/lake.jpg'}

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
function add(spot:Spot){if(busy.value)return;const items=trip.value.days[selected.value].items;if(items.some((i:ItineraryItem)=>i.attractionId===spot.id)){status.value='当天已有该景点';return}items.push({id:crypto.randomUUID(),attractionId:spot.id,order:items.length,durationMinutes:spot.defaultDurationMinutes ?? 60});dirty.value=true;status.value='未保存'}
function move(index:number,delta:number){if(busy.value)return;const items=trip.value.days[selected.value].items;const target=index+delta;if(target<0||target>=items.length)return;[items[index],items[target]]=[items[target],items[index]];items.forEach((i:ItineraryItem,n:number)=>i.order=n);dirty.value=true;status.value='未保存'}
function remove(index:number){if(busy.value)return;const items=trip.value.days[selected.value].items;items.splice(index,1);items.forEach((i:ItineraryItem,n:number)=>i.order=n);dirty.value=true;status.value='未保存'}
async function save(){
 if(busy.value || !trip.value)return
 const sequence=++requestSequence
 const tripId=trip.value.id
 const snapshot=JSON.stringify({...trip.value,baseRevision:trip.value.revision})
 busy.value=true
 status.value='保存中'
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
<div class="app-shell">
  <header class="topbar">
    <button class="brand" @click="trip && back()" :disabled="busy" aria-label="返回旅行列表"><span class="brand-mark">行</span><strong>拾途</strong><span class="brand-caption">旅行行程规划</span></button>
    <span class="topbar-note">计划有序，旅行从容</span>
  </header>
  <main>
    <div v-if="status" class="notice" role="status" aria-live="polite">{{ status }}</div>
    <div v-else class="status-placeholder" role="status" aria-live="polite"></div>

    <section v-if="!trip" class="home">
      <div class="hero">
        <div class="hero-copy"><p class="eyebrow">从一个想去的地方开始</p><h1>把期待，<br>排进每一天。</h1><p class="hero-description">选好目的地，安排喜欢的风景。<br>你的下一段旅程，在这里慢慢成形。</p><a href="#new-trip" class="text-link">开始规划 <span>↗</span></a></div>
        <div class="hero-image"><img src="/images/lake.jpg" alt="湖泊与山间旅行风景示意"><span class="photo-caption">留一点时间，给沿途的风景</span></div>
      </div>
      <section id="new-trip" class="create-panel">
        <div><p class="eyebrow">新的出发</p><h2>创建一份旅行</h2></div>
        <form class="create-form" @submit.prevent="create">
          <label>旅行名称<input v-model="name" maxlength="50" placeholder="例如，周末城市漫游" required :disabled="busy"></label>
          <label>出发日期<input v-model="start" type="date" required :disabled="busy"></label>
          <button class="button primary" :disabled="busy">{{busy?'正在创建':'创建三日旅行'}} <span>↗</span></button>
        </form>
      </section>
      <section class="my-trips">
        <div class="section-heading"><div><p class="eyebrow">继续你的计划</p><h2>我的旅行</h2></div><span class="muted">{{trips.length}} 份行程</span></div>
        <div v-if="trips.length" class="trip-grid">
          <button v-for="t in trips" :key="t.id" class="trip-card" @click="open(t.id)" :disabled="busy">
            <span class="trip-thumb"><img src="/images/lake.jpg" alt="" loading="lazy"></span>
            <span class="trip-card-body"><span class="muted">{{t.startDate}} 出发 · {{t.dayCount}} 天</span><strong>{{t.name}}</strong><span class="trip-card-bottom">打开行程 <span>↗</span></span></span>
          </button>
        </div>
        <div v-else class="empty-state"><span class="empty-symbol">↗</span><h3>旅行从第一份计划开始</h3><p>填写上面的名称和日期，收藏你的下一段旅程。</p></div>
      </section>
    </section>

    <section v-else class="editor">
      <button class="back-link" @click="back" :disabled="busy">← 返回列表</button>
      <div class="editor-heading"><div><p class="eyebrow">{{trip.startDate}} 出发 · {{trip.dayCount}} 天 · 已安排 {{totalItems}} 站</p><h1>{{trip.name}}</h1></div><div class="save-actions"><span class="save-state" :class="{unsaved:dirty}"><span></span>{{saveLabel}}</span><button class="button primary" @click="save" :disabled="busy">{{busy?'保存中':'保存旅行'}}</button></div></div>
      <div class="workspace">
        <aside class="discovery">
          <div class="section-heading"><h2>发现景点</h2><span class="muted">{{filteredSpots.length}} 处</span></div>
          <label class="search-label"><span>搜索景点</span><input v-model="query" type="search" placeholder="想去哪里？" aria-label="搜索景点"></label>
          <div class="filters" aria-label="景点分类"><button v-for="c in categories" :key="c" @click="category=c" :class="{active:category===c}" :aria-pressed="category===c">{{c}}</button></div>
          <article v-for="spot in filteredSpots" :key="spot.id" class="spot-card">
            <button class="spot-image" @click="showDetails(spot)" :aria-label="'查看'+spot.name+'详情'"><img :src="imageFor(spot)" :alt="spot.name+'风景示意'" loading="lazy"><span>{{spot.category || '景点'}}</span></button>
            <div class="spot-body"><div class="spot-title"><h3>{{spot.name}}</h3><strong>{{spot.ticketCents===0?'免费':'¥'+money(spot.ticketCents)}}</strong></div><p class="muted">建议停留 {{spot.defaultDurationMinutes || 60}} 分钟</p><div class="spot-actions"><button class="text-link" @click="showDetails(spot)">查看详情 ↗</button><button class="button compact" @click="add(spot)" :disabled="busy">加入当天 +</button></div></div>
          </article>
          <div v-if="!filteredSpots.length" class="empty-state small"><h3>还没有找到</h3><p>换个关键词，或选择其他分类。</p><button class="text-link" @click="query='';category='全部'">清除筛选</button></div>
        </aside>

        <section class="day-planner">
          <nav class="day-tabs" aria-label="旅行日期"><button v-for="(day,index) in trip.days" :key="day.id" @click="selected=Number(index)" :class="{active:selected===Number(index)}" :aria-pressed="selected===Number(index)"><strong>第{{day.dayIndex}}天</strong><span>{{dayDate(Number(index))}}</span><small>{{day.items.length}} 站</small></button></nav>
          <div class="day-heading"><div><p class="eyebrow">{{dayDate(selected)}}</p><h2>今天，慢慢走。</h2></div><span class="day-hours">{{clock(trip.days[selected].startMinutes)}} — {{clock(trip.days[selected].endMinutes)}}</span></div>
          <div v-if="currentItems.length" class="timeline">
            <article v-for="(item,index) in currentItems" :key="item.id" class="itinerary-card">
              <span class="stop-number">{{Number(index)+1}}</span><div class="itinerary-content"><div class="itinerary-title"><span class="muted">{{findSpot(item.attractionId)?.category || '景点'}}</span><span class="muted">停留 {{item.durationMinutes}} 分钟</span></div><h3>{{findSpot(item.attractionId)?.name || item.attractionId}}</h3><p>{{findSpot(item.attractionId)?.description || '给这一站留一段充裕的时间。'}}</p><div class="item-toolbar"><button @click="move(Number(index),-1)" :disabled="busy || index===0" :aria-label="'上移'+findSpot(item.attractionId)?.name">↑ 上移</button><button @click="move(Number(index),1)" :disabled="busy || index===currentItems.length-1" :aria-label="'下移'+findSpot(item.attractionId)?.name">↓ 下移</button><button @click="remove(Number(index))" :disabled="busy" class="danger">删除</button></div></div>
            </article>
          </div>
          <div v-else class="empty-state day-empty"><span class="empty-symbol">＋</span><h3>给今天选一个起点</h3><p>从左侧加入喜欢的景点，<br>再用上下移动调整访问顺序。</p></div>
          <p class="planner-footnote">调整后记得保存，下一次打开时继续规划。</p>
        </section>

        <aside class="day-overview">
          <p class="eyebrow">当日概览</p><h2>第{{selected+1}}天</h2><div class="overview-stats"><div><strong>{{currentItems.length}}</strong><span>个景点</span></div><div><strong>{{dayMinutes}}</strong><span>分钟游览</span></div></div>
          <div class="ticket-total"><span>门票参考小计</span><strong>¥{{money(ticketSubtotal)}}</strong></div><p class="overview-note">仅汇总当天已安排景点的参考门票。</p>
          <div class="route-list"><h3>访问顺序</h3><ol v-if="currentItems.length"><li v-for="item in currentItems" :key="item.id">{{findSpot(item.attractionId)?.name || item.attractionId}}</li></ol><p v-else class="muted">加入景点后在这里查看。</p></div>
        </aside>
      </div>
    </section>
    <footer>拾途 · 旅行行程规划<span>合成景点与参考价格，照片为风景示意</span></footer>
  </main>
  <dialog ref="dialog" class="detail-dialog"><template v-if="detail"><img :src="imageFor(detail)" :alt="detail.name+'风景示意'"><div class="detail-body"><div class="section-heading"><p class="eyebrow">{{detail.category || '景点详情'}}</p><form method="dialog"><button class="icon-button" aria-label="关闭详情">×</button></form></div><h2>{{detail.name}}</h2><p>{{detail.description || '景点参考资料。'}}</p><dl><div><dt>参考门票</dt><dd>{{detail.ticketCents===0?'免费':'¥'+money(detail.ticketCents)}}</dd></div><div><dt>建议停留</dt><dd>{{detail.defaultDurationMinutes || 60}} 分钟</dd></div><div v-if="detail.openMinutes!==undefined && detail.closeMinutes!==undefined"><dt>参考开放时间</dt><dd>{{clock(detail.openMinutes)}}–{{clock(detail.closeMinutes)}}</dd></div></dl><p class="muted">资料用于课程演示，图片为风景示意。</p></div></template></dialog>
</div>
</template>
<style>
:root{font-family:"Microsoft YaHei","PingFang SC",sans-serif;color:#263e36;background:#f7f7f2;font-synthesis:none;--green:#254d3d;--muted:#7c857d;--line:#dfe4da}
*{box-sizing:border-box}body{margin:0}button,input{font:inherit}button,a,input{outline-offset:4px}button{cursor:pointer}button:disabled{cursor:default;opacity:.45}a{color:inherit}button{color:inherit}button:focus-visible,a:focus-visible{outline:2px solid #588d6b}h1,h2,h3,p{margin:0}h2{font-size:21px;letter-spacing:-.5px}h3{font-size:16px}p{line-height:1.8}.topbar{height:83px;padding:0 5%;display:flex;align-items:center;justify-content:space-between;background:#fff;border-bottom:1px solid var(--line)}.brand{border:0;background:none;display:flex;align-items:center;gap:12px;padding:0}.brand-mark{display:grid;place-items:center;width:34px;height:36px;background:var(--green);color:white;border-radius:11px 4px 11px 4px;font-size:19px}.brand strong{font-size:23px;letter-spacing:3px}.brand-caption{border-left:1px solid var(--line);padding-left:15px;font-size:12px;letter-spacing:1px;margin-left:8px}.topbar-note{font-size:12px;color:var(--muted);letter-spacing:2px}main{max-width:1480px;margin:auto;padding:0 5%}.notice{margin-top:18px;padding:10px 16px;background:#eef2e9;border-left:3px solid #668068;font-size:13px}.status-placeholder{height:24px}.hero{display:grid;grid-template-columns:.85fr 1.15fr;min-height:420px;gap:30px;margin-top:15px}.hero-copy{padding:45px 0 32px}.eyebrow{font-size:11px;letter-spacing:2px;color:#788573}.hero h1{font-size:clamp(38px,4.6vw,65px);line-height:1.3;letter-spacing:2px;font-weight:500;margin:18px 0}.hero-description{font-size:13px;color:#6d786f;margin-bottom:24px}.text-link{border:0;padding:0;background:transparent;text-decoration:none;font-size:12px;line-height:1.7}.hero .text-link{border-bottom:1px solid #849b86;padding-bottom:7px}.hero .text-link span{margin-left:34px}.hero-image{position:relative;overflow:hidden;border-radius:120px 8px 8px 8px;min-height:380px}.hero-image img{width:100%;height:100%;position:absolute;object-fit:cover}.hero-image:after{content:"";position:absolute;inset:50% 0 0;background:linear-gradient(transparent,#142c2780)}.photo-caption{position:absolute;bottom:25px;left:30px;color:white;font-size:12px;letter-spacing:2px;z-index:1}.create-panel{display:flex;align-items:center;justify-content:space-between;gap:25px;margin:35px 0 46px;padding:27px 30px;background:white;border:1px solid var(--line);border-radius:12px}.create-panel h2{margin-top:7px}.create-form{display:flex;align-items:end;gap:14px;flex-wrap:wrap}label{font-size:11px;color:#6c776f;display:flex;flex-direction:column;gap:8px}input{padding:11px 13px;border:1px solid #dfe4db;border-radius:6px;background:#fcfcf9;color:#253b32;min-width:0}.button{border:1px solid #ccd8c9;border-radius:6px;background:#f2f6ee;padding:10px 14px;font-size:12px;white-space:nowrap}.button.primary{background:var(--green);color:white;border-color:var(--green);padding:13px 22px}.button:hover:not(:disabled){filter:brightness(.93)}.create-form .primary{height:43px}.section-heading{display:flex;align-items:center;justify-content:space-between;gap:15px;margin-bottom:19px}.section-heading h2{margin-top:6px}.muted{color:var(--muted);font-size:11px}.trip-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}.trip-card{background:white;padding:0;border:1px solid var(--line);border-radius:10px;overflow:hidden;text-align:left;transition:transform .2s}.trip-card:hover{transform:translateY(-3px)}.trip-thumb{display:block;height:135px;overflow:hidden}.trip-thumb img{width:100%;height:100%;object-fit:cover}.trip-card-body{display:flex;flex-direction:column;padding:20px;gap:10px}.trip-card-body strong{font-size:19px}.trip-card-bottom{display:flex;justify-content:space-between;font-size:11px;border-top:1px solid var(--line);padding-top:13px;margin-top:8px}.empty-state{text-align:center;border:1px dashed #d6ded1;border-radius:10px;padding:40px 15px;background:#fafbf6}.empty-symbol{font-size:30px;color:#8f9f87;display:block;margin-bottom:15px}.empty-state p{font-size:12px;color:var(--muted);margin-top:9px}.back-link{border:0;background:none;padding:12px 0;font-size:11px;color:var(--muted)}.editor-heading{display:flex;justify-content:space-between;align-items:center;margin:18px 0 32px;gap:20px}.editor-heading h1{font-size:31px;margin-top:10px;overflow-wrap:anywhere}.save-actions{display:flex;align-items:center;gap:20px}.save-state{font-size:11px;color:#6c7f6c;white-space:nowrap}.save-state>span{display:inline-block;width:6px;height:6px;border-radius:50%;background:#78916d;margin-right:6px}.save-state.unsaved>span{background:#c69d5a}.workspace{display:grid;grid-template-columns:270px minmax(300px,1fr) 215px;gap:26px;align-items:start}.discovery{border-right:1px solid var(--line);padding-right:24px}.search-label>span{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}.search-label input{width:100%;font-size:12px;background:white}.filters{display:flex;gap:6px;flex-wrap:wrap;margin:13px 0 20px}.filters button{background:transparent;border:1px solid transparent;color:#7c877b;border-radius:5px;padding:6px 9px;font-size:10px}.filters button.active{background:#e5eddf;color:var(--green);border-color:#d5dfce}.spot-card{border:1px solid var(--line);border-radius:8px;overflow:hidden;background:white;margin-bottom:16px}.spot-image{position:relative;display:block;width:100%;height:135px;border:0;padding:0;background:#e4eadf}.spot-image img{width:100%;height:100%;object-fit:cover}.spot-image>span{position:absolute;bottom:10px;left:10px;background:#ffffffeb;border-radius:3px;padding:4px 7px;font-size:9px}.spot-body{padding:15px}.spot-title{display:flex;justify-content:space-between;align-items:center;gap:10px}.spot-title strong{font-size:12px;font-weight:500}.spot-body>p{margin:8px 0 14px}.spot-actions{display:flex;align-items:center;justify-content:space-between;gap:8px}.spot-actions .text-link{font-size:10px}.compact{font-size:10px;padding:7px 10px}.day-tabs{display:flex;border-bottom:1px solid var(--line);gap:8px}.day-tabs button{flex:1;display:flex;flex-direction:column;align-items:center;gap:6px;background:transparent;border:0;border-bottom:2px solid transparent;padding:10px 3px 17px;color:#899083}.day-tabs button.active{color:var(--green);border-bottom-color:var(--green)}.day-tabs strong{font-size:13px}.day-tabs span{font-size:10px}.day-tabs small{font-size:9px}.day-heading{display:flex;align-items:center;justify-content:space-between;margin:30px 0;gap:10px}.day-heading h2{font-size:20px;margin-top:8px}.day-hours{font-size:10px;color:var(--muted);white-space:nowrap}.timeline{padding-left:28px;border-left:1px solid #d5dfcf;margin-left:11px}.itinerary-card{position:relative;margin-bottom:20px}.stop-number{position:absolute;left:-40px;top:18px;background:var(--green);border:4px solid #f7f7f2;color:white;width:25px;height:25px;box-sizing:content-box;display:grid;place-items:center;border-radius:50%;font-size:11px}.itinerary-content{border:1px solid var(--line);background:white;border-radius:8px;padding:20px}.itinerary-title{display:flex;justify-content:space-between;gap:8px}.itinerary-content h3{font-size:20px;margin:12px 0}.itinerary-content>p{font-size:11px;color:#8b9188}.item-toolbar{display:flex;gap:8px;margin-top:20px;border-top:1px solid #edf0e8;padding-top:12px}.item-toolbar button{border:0;background:transparent;font-size:10px;color:#6f7e6e;padding:5px}.item-toolbar .danger{margin-left:auto;color:#a47667}.planner-footnote{font-size:10px;text-align:center;color:#9bA193;margin-top:25px}.day-overview{background:#edf1e8;border:1px solid #e1e7d9;border-radius:9px;padding:23px;position:sticky;top:20px}.day-overview h2{margin-top:10px;font-size:25px}.overview-stats{display:flex;gap:25px;margin:28px 0}.overview-stats div{display:flex;flex-direction:column;gap:8px}.overview-stats strong{font-size:25px;font-weight:500}.overview-stats span{font-size:10px;color:#84907c}.ticket-total{display:flex;justify-content:space-between;align-items:center;padding-top:19px;border-top:1px solid #dbe2d2;gap:8px}.ticket-total span{font-size:10px}.ticket-total strong{font-size:17px;font-weight:500}.overview-note{font-size:10px;color:#8b9584;margin-top:10px}.route-list{margin-top:25px;border-top:1px solid #dbe2d2;padding-top:20px}.route-list h3{font-size:12px;margin-bottom:14px}.route-list ol{padding-left:20px;font-size:11px;color:#6c7c64;line-height:2.5}.day-empty{padding:65px 15px}.small{padding:25px 10px}.small .text-link{margin-top:12px}footer{display:flex;justify-content:space-between;border-top:1px solid var(--line);padding:25px 0;margin-top:55px;color:#929a8b;font-size:10px;gap:15px}.detail-dialog{border:0;padding:0;border-radius:13px;width:min(500px,90vw);max-height:90vh;color:#263e36;box-shadow:0 20px 80px #12251d30}.detail-dialog::backdrop{background:#1b30285c}.detail-dialog>img{width:100%;height:210px;object-fit:cover}.detail-body{padding:25px}.detail-body h2{font-size:27px;margin:12px 0}.detail-body>p{font-size:12px;color:#7d8879}.icon-button{border:0;background:#edf1e8;border-radius:50%;width:29px;height:29px;font-size:20px}.detail-body dl{font-size:12px;margin:24px 0}.detail-body dl>div{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--line)}.detail-body dt{color:#85907e}.detail-body dd{margin:0}
@media(min-width:1500px){.workspace{grid-template-columns:290px minmax(350px,1fr) 245px;gap:35px}}
@media(max-width:1100px){.workspace{grid-template-columns:240px minmax(0,1fr)}.day-overview{grid-column:2;position:static}.hero{min-height:350px}.hero-image{min-height:340px}.create-panel{align-items:start;flex-direction:column}.create-form{width:100%}.create-form label:first-child{flex:1}.trip-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:700px){.topbar{height:68px}.brand-caption,.topbar-note{display:none}main{padding:0 5%}.hero{grid-template-columns:1fr;gap:0}.hero-copy{padding:25px 0}.hero h1{font-size:40px}.hero-image{min-height:220px;border-radius:65px 7px 7px 7px}.create-panel{padding:20px;margin-top:25px}.create-form{flex-direction:column;align-items:stretch}.trip-grid{grid-template-columns:1fr}.editor-heading{align-items:start;flex-direction:column;gap:15px}.editor-heading h1{font-size:27px}.save-actions{width:100%;justify-content:space-between}.workspace{grid-template-columns:1fr;gap:25px}.day-planner{order:1}.discovery{order:2;border-right:0;padding-right:0}.spot-card{display:grid;grid-template-columns:110px minmax(0,1fr)}.spot-image{height:100%;min-height:140px}.spot-body{padding:13px}.spot-title{align-items:start}.day-overview{grid-column:auto;order:3}.day-heading{margin:22px 0}.itinerary-content{padding:16px}.itinerary-title .muted{font-size:10px}footer{flex-direction:column}.hero-description{font-size:12px}}
</style>
