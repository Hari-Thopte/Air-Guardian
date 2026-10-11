"""Deterministic examples from the real engine. No live data or dates invented."""
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.functions.air_engine import particle_index, iso
from backend.functions.guardian_rules import POLICY, FLAGS
from cloud.policy import plan
from cloud.contracts import school
from cloud.dayplan import timetable

ROOT = Path(__file__).resolve().parents[1]


def export():
    config=school({'id':'example','name':'Example school','lat':28.6139,'lon':77.209})
    result={'label':"Example day. Not today's school instruction.", 'flags':FLAGS,
            'thresholds':POLICY['5-8'][1], 'ageGroup':'5-8', 'scenarios':[]}
    result['flags'] = [*FLAGS, 'unknown']
    for label, base in [('Green',8),('Yellow',25),('Orange',45),('Red',100),('Stale reading',100)]:
        hours=[]
        for hour in range(8,17):
            pm=round(base*(1.15 if hour in (8,9,15) else .9),1)
            air={'aqi':particle_index(pm),'pm25':pm,'standard':'India particle estimate','observedAt':iso(1760000000),
                 'mode':'demo','source':'Synthetic scenario','forecast':[], 'stale':label=='Stale reading'}
            planning=plan(air,config,now=1760000000)
            hours.append({'hour':hour,'pm25':pm,'flag':planning['flag'],'headline':planning['actions'][0]['text'],
                          'actions':planning['actions'],'blocks':timetable(config,planning)})
        result['scenarios'].append({'name':label,'hours':hours})
    return result


if __name__=='__main__':
    data=export()
    (ROOT/'landing-scenarios.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Non-executable JSON: the landing instrument starts without waiting on a request.
    fallback={**data,'scenarios':[data['scenarios'][2]]}
    block='<script type="application/json" id="default-scenario">'+json.dumps(fallback,ensure_ascii=False).replace('<','\\u003c')+'</script>'
    page=ROOT/'home.html';html=page.read_text(encoding='utf-8')
    if 'id="default-scenario"' in html:
        html=re.sub(r'<script type="application/json" id="default-scenario">.*?</script>',lambda _:block,html,flags=re.S)
    else:html=html.replace('</body>',block+'\n</body>')
    page.write_text(html,encoding='utf-8')
