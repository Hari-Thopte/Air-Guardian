"""Replace transient loopback fixture state; never used by deployed ingestion."""
import time
from backend.functions.air_engine import demo, estimate, iso
from cloud.policy import plan
from cloud.store import change, MemoryStore


def select_scenario(store, readings, config, choice, now=None):
    if not isinstance(store, MemoryStore) or not isinstance(readings, MemoryStore):
        raise ValueError('Fixture selection is restricted to MemoryStore.')
    if choice not in ('green', 'yellow', 'orange', 'red', 'stale'):
        raise ValueError('Unsupported fixture scenario.')
    now = time.time() if now is None else now
    pk = 'SCHOOL#' + config['id']
    # A scenario is an independent example, never another live observation.
    transient = ('CURRENT', 'ALERTSTATE', 'NOTICE', 'RECEIPT#', 'TASK#',
                 'EVENT#', 'PUBLICATION#', 'REMINDER#', 'AUTO_NUDGE#', 'AUDIT#', 'DECISION#')
    for key in list(store.rows):
        if (key[0] == pk and key[1].startswith(transient)) or key[0] == 'OUTBOX':
            del store.rows[key]
    for key in list(readings.rows):
        if key[0] == pk or key[0].startswith(pk + '#'):
            del readings.rows[key]
    fixture = demo(config, True)
    base = {'green': 8, 'yellow': 25, 'orange': 45, 'red': 110, 'stale': 110}[choice]
    for station in fixture['stations']:
        station.update(pm25=base, pm10=base * 1.8)
    fixture.update(estimate(config, fixture['stations']))
    for point in fixture['forecast']:
        point['pm25'] = base
    fixture.update(mode='demo', demoScenario=choice, source='Demo data · synthetic station fixtures',
                   observedAt=iso(now - 10800 if choice == 'stale' else now),
                   stale=choice == 'stale', fetchedAt=iso(now),
                   providers=[{'name': 'Demo fixtures', 'status': 'Not live measurements'}],
                   forecastSource='Synthetic forecast fixture', retentionApproved=True)
    planning = plan(fixture, config, now=now)
    store.commit([change(pk, 'CURRENT', {'air': fixture, 'planning': planning,
                  'lastAttemptAt': now, 'lastSuccessfulAt': now})])
    return {'label': 'Demo data. No messages sent.', 'scenario': choice}
