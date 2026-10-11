"""Durable school unlink cleanup. Operational receipts use their retention policy."""
from cloud.store import change


def erase_private(store, job):
    upk, sid = 'USER#' + job['sub'], job['school']
    for prefix in ('EXPOSURE#' + sid + '#', 'CHECKIN#' + sid + '#', 'DELIVERY#' + sid + '#'):
        while True:
            rows = store.query(upk, prefix, limit=50)
            if not rows:
                break
            store.commit([change(upk, r['_sk'], None, r) for r in rows])
    active = [r for r in store.query(upk, 'SCHOOL#')
              if (store.get('SCHOOL#' + r['school'], 'MEMBER#' + job['sub']) or {}).get('active')]
    if not active:
        for prefix in ('PUSH#', 'CONTACT', 'PREFERENCES'):
            rows = store.query(upk, prefix, limit=50)
            if rows:
                store.commit([change(upk, r['_sk'], None, r) for r in rows])
    current = store.get('ERASURE', job['school'] + '#' + job['sub'])
    if current:
        store.commit([change('ERASURE', job['school'] + '#' + job['sub'], None, current)])
