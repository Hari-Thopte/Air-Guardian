"""Check the actual regional response at pilot coordinates; never substitutes fixtures."""
import json
import time
from datetime import datetime, timezone
from aws_support import ROOT
from backend.functions.air_engine import openmeteo, timestamp

school = json.loads((ROOT / 'deployment' / 'school.json').read_text())
result = {'retrievedAt': datetime.now(timezone.utc).isoformat(), 'coordinates': [school['lat'], school['lon']],
          'source': 'Open-Meteo / CAMS', 'kind': 'regional model', 'units': 'µg/m³',
          'note': 'A real provider response, not a measured school sensor. This does not verify AWS scheduling.'}
try:
    data = openmeteo(school)
    row = data['stations'][0]
    result.update({'passed': True, 'observedAt': row['observedAt'], 'ageSeconds': round(time.time() - timestamp(row['observedAt'])),
                   'pm25': row['pm25'], 'pm10': row['pm10'], 'forecastHours': len(data['forecast'])})
except Exception as error:
    result.update({'passed': False, 'errorType': type(error).__name__, 'note': 'Provider unavailable or failed timestamp/unit validation; no simulated fallback.'})
target = ROOT / '.test-output' / 'real-air-probe.json'
target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
raise SystemExit(int(not result['passed']))
