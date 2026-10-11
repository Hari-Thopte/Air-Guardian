// Pure presentation helpers. Stored plans, API permissions and policy stay unchanged.
export function historySeries(rows){
  const sources=new Map();
  for(const row of rows){
    const source=row.source||'Unknown source';
    if(!sources.has(source))sources.set(source,new Map());
    const time=Date.parse(row.observedAt);
    if(!Number.isFinite(row.pm25)||row.pm25<0||!Number.isFinite(time))continue;
    // A repeated retrieval of the same observation is not a new plotted sample.
    const key=JSON.stringify([time,row.pm25]);
    sources.get(source).set(key,row);
  }
  return [...sources].map(([source,unique])=>({source,points:[...unique.values()].sort((a,b)=>Date.parse(a.observedAt)-Date.parse(b.observedAt))}));
}

export function noticeState(workspace,{demoDraft=null,now=Date.now()/1000}={}){
  const notice=workspace.notice,planning=workspace.planning;
  const changedDemo=demoDraft&&demoDraft.noticeId===(notice?.id||null)
    &&demoDraft.reading===workspace.air.fetchedAt&&demoDraft.flag===planning.flag;
  const published=notice&&notice.expiresAt>now&&notice.flag===planning.flag&&!changedDemo;
  let summary=workspace.receiptSummary;
  if(!published&&summary){
    const people=workspace.members?.length?workspace.members.filter(p=>p.active):summary.people;
    summary={total:people.length,confirmed:0,people:people.map(p=>({...p,confirmed:false}))};
  }
  const stage=published?(summary?.total>0&&summary.confirmed===summary.total?'reviewed':'published'):'draft';
  return {stage,notice:published?notice:null,previousNotice:published?null:notice,summary,
    receipts:published?workspace.receipts:[],scenarioDraft:Boolean(changedDemo)};
}

export function receiptGroups(rows,labelFor,formatTime){
  const groups=new Map();
  for(const row of rows){
    const label=labelFor(row),time=formatTime(row.createdAt),key=JSON.stringify([row.kind,label,time]);
    if(!groups.has(key))groups.set(key,{kind:row.kind,label,time,count:0});
    groups.get(key).count++;
  }
  return [...groups.values()];
}

export function morningAnswer(brief){
  if(!brief.available||brief.flag==='unknown')return 'Unknown — check a fresh forecast first.';
  return ['orange','red'].includes(brief.flag)?'Yes — review indoor alternatives.':'No — review the usual or shorter outdoor timetable.';
}
