"""Durable optimistic per-identity limits; API Gateway additionally limits traffic."""
import hashlib
import time
from cloud.store import change, Conflict
from cloud.contracts import Problem


def reserve(store, subject, action, cap=5, period=60):
    now = time.time()
    bucket = int(now // period)
    key = hashlib.sha256(subject.encode()).hexdigest()
    pk, sk = 'LIMIT#' + key, action + '#' + str(bucket)
    for _ in range(3):
        row = store.get(pk, sk)
        count = (row or {}).get('count', 0)
        if count >= cap:
            raise Problem('Too many requests. Wait a minute and retry.', 429)
        try:
            store.commit([change(pk, sk, {'count': count + 1}, row, expires=now + period * 2)])
            return
        except Conflict:
            continue
    raise Problem('Too many concurrent requests. Retry shortly.', 429)
