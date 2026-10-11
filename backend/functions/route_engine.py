"""Station-based path comparison, not navigation or a measured road pollution map."""
from backend.functions.air_engine import interpolate,distance,finite


def route_exposure(school,stations,path,minutes):
    if not isinstance(path,list) or not 2<=len(path)<=20 or not finite(minutes) or not 1<=minutes<=180:
        raise ValueError('Use 2–20 coordinate points and 1–180 minutes.')
    points=[]
    for point in path:
        if not isinstance(point,list) or len(point)!=2 or not all(finite(x) for x in point) or abs(point[0])>90 or abs(point[1])>180:
            raise ValueError('Use latitude, longitude pairs.')
        p={'lat':point[0],'lon':point[1]}
        if distance(school,p)>25:raise ValueError('Routes must stay within 25 km of the school.')
        points.append(p)
    measured=[s for s in stations if s.get('kind')=='station']
    total_length=0;integral=0
    for a,b in zip(points,points[1:]):
        length=distance(a,b)
        if length<.001:continue
        samples=[]
        for t in (0,.25,.5,.75,1):
            p={'lat':a['lat']+(b['lat']-a['lat'])*t,'lon':a['lon']+(b['lon']-a['lon'])*t}
            concentration,_=interpolate(p,measured)
            if concentration is None:return {'available':False,'reason':'No fresh station coverage along the path.'}
            samples.append(concentration)
        average=(samples[0]/2+sum(samples[1:-1])+samples[-1]/2)/4
        integral+=average*length;total_length+=length
    if total_length==0:raise ValueError('A route must contain different locations.')
    concentration=integral/total_length
    return {'available':True,'pm25':round(concentration,2),'proxy':round(concentration*minutes,2),'minutes':minutes,
            'lengthKm':round(total_length,2),'unit':'µg·min/m³','path':path,
            'note':'IDW concentrations weighted by segment length and entered travel time. No traffic, actual road directions or personal inhaled dose is measured.'}
