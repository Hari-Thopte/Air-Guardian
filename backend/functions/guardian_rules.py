"""Explainable school planning policy. Not a clinical score or safe-exposure limit."""
from backend.functions.air_engine import finite

FLAGS = ['green', 'yellow', 'orange', 'red']
AGE_GROUPS = ['5-8', '9-12', '13-17']
POLICY = {'5-8': ([40, 80, 140], [15, 35, 60]), '9-12': ([50, 100, 175], [20, 40, 75]),
          '13-17': ([50, 120, 200], [25, 50, 90])}


def child_risk(air, age_group='9-12', caution=False):
    if age_group not in POLICY:
        raise ValueError('Choose a supported age group')
    if air.get('stale') or not finite(air.get('aqi')) or air['aqi'] < 0:
        return {'flag': 'unknown', 'score': None, 'reasons': ['Current air context unavailable. Ask staff to verify conditions.'],
                'ageGroup': age_group, 'caution': caution, 'label': 'Planning priority unavailable'}
    aqi_limits, particle_limits = POLICY[age_group]
    if air.get('standard') == 'US':
        aqi_limits = [min(v, limit) for v, limit in zip(aqi_limits, [40, 80, 125])]
    aqi = air['aqi']
    band = sum(aqi > limit for limit in aqi_limits)
    reasons = [f"Air index {round(aqi)} compared with {age_group} policy boundaries {', '.join(map(str, aqi_limits))}."]
    if finite(air.get('pm25')):
        particle_band = sum(air['pm25'] > limit for limit in particle_limits)
        band = max(band, particle_band)
        reasons.append(f"PM2.5 {air['pm25']} µg/m³ compared with planning boundaries {', '.join(map(str, particle_limits))} µg/m³.")
    if caution:
        band = min(3, band + 1)
        reasons.append('The higher-caution setting raises the planning flag one level.')
    return {'flag': FLAGS[band], 'score': [0, 33, 67, 100][band], 'ageGroup': age_group, 'caution': caution,
            'reasons': reasons, 'label': 'School planning priority — not a medical risk score',
            'policy': 'Illustrative conservative policy; school approval and individual care plans take precedence.'}


def recommendations(air,risk,role='parent',indoor_pm25=None):
    flag=risk['flag'];actions=[]
    if flag=='unknown':
        return [{'id':'verify','text':'Ask school staff to verify conditions before making an activity decision.',
                 'why':'No fresh usable air context is available.'}]
    trigger=' '.join(risk['reasons'])
    def add(key,text,why):actions.append({'id':key,'text':text,'why':why})
    if flag in ('orange','red'):
        add('indoor-pe','Review moving vigorous PE and assembly indoors; check room conditions before confirming.',trigger)
        add('mask','Ask a responsible adult or supervisor about a well-fitting N95/KN95 reminder where school guidance and an existing care plan call for one. Adult respirator fit is not assumed for children.',f'School planning flag is {flag}; mask suitability and fit need individual guidance.')
        add('pickup','Stagger pickup/drop-off and reduce waiting at the gate; ask drivers to avoid unnecessary idling.',f'Outdoor planning flag is {flag}. Traffic at the gate can add local exposure not captured by the estimate.')
        add('route','Discuss avoiding high-traffic roads and unnecessary outdoor stops with an adult. Use route estimates as planning comparisons, not proof that a road is clean.',f'Outdoor planning flag is {flag}; exact road pollution is not measured.')
    elif flag=='yellow':
        add('gentle','Review shorter, gentler outdoor activities and recheck conditions before starting.',trigger)
    else:add('usual','Review the usual timetable and recheck the air before long outdoor sessions.',trigger)
    if flag=='red' and role=='staff':
        add('rotate','Ask the supervisor to rotate outdoor gate and ground duties and provide indoor breaks.',trigger)
    peaks=[p['pm25'] for p in air.get('forecast',[]) if finite(p.get('pm25'))]
    if peaks and finite(air.get('pm25')) and max(peaks)>air['pm25']*1.25:
        add('peak','At the predicted pollution peak, staff should review keeping windows closed if indoor air and ventilation/heat conditions support it; follow the building plan.',f'Forecast PM2.5 peak {max(peaks):.1f} µg/m³ exceeds current {air["pm25"]:.1f} by more than 25%.')
    if finite(indoor_pm25) and finite(air.get('pm25')):
        add('indoor-check','Review the room air before relying on an indoor alternative.',f'Indoor PM2.5 {indoor_pm25} µg/m³ versus outdoor estimate {air["pm25"]} µg/m³; sensor quality and freshness still matter.')
    add('care-plan','Keep following existing school instructions and care plans; tell a trusted adult if you feel unwell.','These are school planning rules, not a diagnosis or activity clearance.')
    return actions
