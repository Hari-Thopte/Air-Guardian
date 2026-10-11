"""HTTP smoke test for the fictional loopback preview; never accepts a remote URL."""
import argparse
import json
import re
import uuid
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def check(port=5187):
    base=f'http://127.0.0.1:{port}'
    def request(path,role='admin',body=None):
        headers={'X-Preview-Role':role,'Origin':base,'Content-Type':'application/json'}
        req=Request(base+path,headers=headers,data=json.dumps(body).encode() if body is not None else None)
        with urlopen(req,timeout=15) as response:
            raw=response.read().decode('utf-8')
            return json.loads(raw) if 'json' in response.headers.get('Content-Type','') else raw
    for page in ['/home.html','/cloud.html']:
        html=request(page)
        assert '/assets/guardian-emblem.png' in html
        for asset in re.findall(r'(?:src|href)="(/[^"#]+\.(?:js|css|json|svg))"',html):
            request(asset)
    engine=request('/local-engine')
    assert 'Powertools' in engine['awsOpenSource']
    path='/v1/schools/preview/'
    admin=request(path+'workspace')
    assert admin['air']['mode']=='demo' and len(admin['classes'])>=3
    operations=request(path+'operations')
    assert len(operations['plans'])>=2
    event=request(path+'announce',body={'note':'Demo review: check indoor room arrangements before changing PE.','requestId':'smoke-'+uuid.uuid4().hex})['event']
    parent=request(path+'workspace','parent')
    assert parent['notice']['id']==event['id'] and 'audience' not in parent['notice']
    request(path+'review','parent',{'eventId':event['id']})
    request(path+'review','parent',{'eventId':event['id']})
    admin=request(path+'workspace')
    assert admin['receiptSummary']['confirmed']==1
    staff=request(path+'workspace','staff')
    assert not staff['children'] and not staff['members'] and staff['receiptSummary'] is None
    try:
        request(path+'operations','staff')
        raise AssertionError('Staff operation access was not denied')
    except HTTPError as error:
        assert error.code==403
    request('/v1/demo/scenario',body={'scenario':'stale'})
    stale=request(path+'workspace')
    assert stale['planning']['flag']=='unknown' and stale['dataHealth']['status']=='Stale'
    try:
        request(path+'announce',body={'note':'Must not publish','requestId':'stale-'+uuid.uuid4().hex})
        raise AssertionError('Stale publication was not denied')
    except HTTPError as error:
        assert error.code==400
    request('/v1/demo/scenario',body={'scenario':'red'})
    return {'status':'passed','checks':['static asset delivery','real Powertools resolver','seeded history',
          'publish → parent review → unique admin count','staff privacy','stale publication blocked'],
          'adultCount':admin['receiptSummary']['total'],'label':'Fictional loopback API checks; no browser or external delivery verification.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=5187)
    print(json.dumps(check(parser.parse_args().port),indent=2))
