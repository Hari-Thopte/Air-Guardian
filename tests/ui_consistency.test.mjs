import test from 'node:test';
import assert from 'node:assert/strict';
import {historySeries,noticeState,receiptGroups,morningAnswer} from '../assets/consistency-ui.js';

const reading=(source,time,pm25)=>({source,observedAt:time,pm25});
const workspace=()=>({notice:{id:'old',flag:'red',time:10,expiresAt:1000},planning:{flag:'red'},
  air:{fetchedAt:'fresh'},members:[{sub:'a',active:true},{sub:'b',active:true}],
  receiptSummary:{total:2,confirmed:1,people:[{sub:'a',confirmed:true},{sub:'b',confirmed:false}]},receipts:[{sub:'a'}]});

test('history counts only finite observations, keeps sources separate and deduplicates retrievals',()=>{
  const point=reading('Station A','2026-10-11T01:00:00Z',12);
  const series=historySeries([point,{...point},reading('Station A','bad',40),reading('Station A','2026-10-11T02:00:00Z',null),reading('Station A','2026-10-11T03:00:00Z',-5),reading('Station B','2026-10-11T00:00:00Z',20)]);
  assert.deepEqual(series.map(s=>[s.source,s.points.length]),[['Station A',1],['Station B',1]]);
});
test('history orders supplied points without inventing samples across gaps',()=>{
  const series=historySeries([reading('A','2026-10-11T04:00:00Z',40),reading('A','2026-10-11T01:00:00Z',10)]);
  assert.deepEqual(series[0].points.map(p=>p.pm25),[10,40]);
});
test('published plan keeps its actual unique review count',()=>{
  const w=workspace(),state=noticeState(w,{now:100});
  assert.equal(state.stage,'published');assert.equal(state.summary.confirmed,1);assert.equal(state.notice.id,'old');
});
test('new scenario clears draft review display without mutating the old audit records',()=>{
  const w=workspace(),before=structuredClone(w);
  const state=noticeState(w,{now:100,demoDraft:{noticeId:'old',reading:'fresh',flag:'red'}});
  assert.equal(state.stage,'draft');assert.equal(state.summary.confirmed,0);assert.equal(state.summary.total,2);
  assert.deepEqual(state.receipts,[]);assert.equal(state.previousNotice.id,'old');assert.deepEqual(w,before);
});
test('a new publication replaces the draft marker and starts with its actual reviews',()=>{
  const w=workspace();w.notice.id='new';w.receiptSummary.confirmed=0;w.receipts=[];
  assert.equal(noticeState(w,{now:100,demoDraft:{noticeId:'old',reading:'fresh',flag:'red'}}).stage,'published');
});
test('all confirmed is reviewed; changed or expired instructions become a draft',()=>{
  const w=workspace();w.receiptSummary.confirmed=2;
  assert.equal(noticeState(w,{now:100}).stage,'reviewed');
  w.planning.flag='green';assert.equal(noticeState(w,{now:100}).summary.confirmed,0);
  w.planning.flag='red';assert.equal(noticeState(w,{now:1001}).stage,'draft');
});
test('a draft uses the current active audience; role-restricted summary remains private',()=>{
  const w=workspace();w.members.push({sub:'revoked',active:false});w.planning.flag='green';
  assert.equal(noticeState(w,{now:100}).summary.total,2);
  w.members=[];w.receiptSummary=null;
  assert.equal(noticeState(w,{now:100}).summary,null);
});
test('identical displayed receipts group with a count; classes and roles remain distinct',()=>{
  const rows=[{kind:'review',createdAt:1,role:'parent'},{kind:'review',createdAt:2,role:'parent'},{kind:'review',createdAt:2,role:'staff'}];
  assert.deepEqual(receiptGroups(rows,r=>r.role,()=> '07:30 IST'),[
    {kind:'review',label:'parent',time:'07:30 IST',count:2},{kind:'review',label:'staff',time:'07:30 IST',count:1}]);
});
test('morning answer does not turn a missing forecast into a yes/no clearance',()=>{
  assert.match(morningAnswer({available:false,flag:'red'}),/^Unknown/);
  assert.match(morningAnswer({available:true,flag:'red'}),/^Yes/);
  assert.match(morningAnswer({available:true,flag:'green'}),/^No/);
});
