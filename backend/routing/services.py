import math,os,requests
from datetime import datetime,timedelta,timezone
from django.core.exceptions import ValidationError
from .risk import classify,summarize,ranking_key

SESSION=requests.Session()
TIMEOUT=22
MILES_PER_METER=1/1609.344

def get_json(url,params=None,headers=None):
    r=SESSION.get(url,params=params,headers=headers,timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def geocode_place(query):
    data=get_json('https://nominatim.openstreetmap.org/search',{'q':query,'format':'json','limit':1},headers={'User-Agent':'SpotterRoutingAssessment/1.0 (educational demo)'})
    if not data:raise ValueError(f'Could not find location: {query}')
    return {'name':data[0]['display_name'],'lat':float(data[0]['lat']),'lon':float(data[0]['lon'])}

def interpolate(a,b,t):return [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t]

def route_checkpoints(coordinates,duration_seconds,spacing_miles):
    """Resample the full polyline at equal *distance*, with ETAs proportional to progress."""
    def haversine(a,b):
        lon1,lat1=map(math.radians,a);lon2,lat2=map(math.radians,b)
        dlat=lat2-lat1;dlon=lon2-lon1
        return 3958.7613*2*math.asin(min(1,math.sqrt(math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2)))
    segments=[haversine(a,b) for a,b in zip(coordinates,coordinates[1:])]
    cumulative=[0]
    for segment in segments:cumulative.append(cumulative[-1]+segment)
    total=cumulative[-1]
    targets=[0];m=spacing_miles
    while m<total:targets.append(m);m+=spacing_miles
    if total>0:targets.append(total)
    result=[];j=0
    for target in targets:
        while j<len(segments)-1 and cumulative[j+1]<target:j+=1
        ratio=(target-cumulative[j])/segments[j] if segments and segments[j]>0 else 0
        coordinate=interpolate(coordinates[j],coordinates[j+1],ratio) if segments else coordinates[0]
        result.append({'mile':round(target,2),'lon':coordinate[0],'lat':coordinate[1],'offset_seconds':round(duration_seconds*target/total) if total else 0})
    return result

def fetch_routes(origin,destination):
    """OSRM demo driving API; not truck-restriction-certified. Alternatives may be fewer than three."""
    coords=f"{origin['lon']},{origin['lat']};{destination['lon']},{destination['lat']}"
    data=get_json(f'https://router.project-osrm.org/route/v1/driving/{coords}',{'alternatives':'true','overview':'full','geometries':'geojson','steps':'false'})
    routes=data.get('routes',[])
    if not routes:raise ValueError('No route found. Try different locations.')
    # OSRM does not guarantee three alternatives: never fabricate a route.
    return routes[:3]

def weather_at(points,arrival_times):
    """Batch hourly forecasts for unique checkpoint coordinates to reduce latency."""
    keys=[(round(p['lat'],2),round(p['lon'],2)) for p in points]
    unique=list(dict.fromkeys(keys))
    cache={}
    batch_size=20
    for start in range(0,len(unique),batch_size):
        batch=unique[start:start+batch_size]
        params={
            'latitude':','.join(str(p[0]) for p in batch),
            'longitude':','.join(str(p[1]) for p in batch),
            'hourly':'wind_speed_10m,rain,snowfall',
            'wind_speed_unit':'mph',
            'precipitation_unit':'inch',
            'timezone':'GMT',
            'forecast_days':5,
        }
        data=get_json('https://api.open-meteo.com/v1/forecast',params)
        entries=data if isinstance(data,list) else [data]
        if len(entries)!=len(batch):
            raise ValueError('Weather provider returned incomplete checkpoint forecasts.')
        for key,entry in zip(batch,entries):
            hourly=entry['hourly']
            cache[key]={**hourly,'_index':{t:i for i,t in enumerate(hourly['time'])}}
    out=[]
    for key,eta in zip(keys,arrival_times):
        hourly=cache[key]
        when=eta.astimezone(timezone.utc).replace(minute=0,second=0,microsecond=0).strftime('%Y-%m-%dT%H:00')
        i=hourly['_index'].get(when)
        if i is None:
            raise ValueError('Forecast unavailable for this checkpoint arrival time. Choose a departure within the forecast horizon.')
        out.append({
            'wind_mph':round(float(hourly['wind_speed_10m'][i] or 0),1),
            'rain_inches_hr':round(float(hourly['rain'][i] or 0),3),
            'snow_inches_hr':round(float(hourly['snowfall'][i] or 0)/2.54,3),
        })
    return out

def build_plan(origin_text,destination_text,departure,load_lbs,spacing):
    origin=geocode_place(origin_text);destination=geocode_place(destination_text)
    base=datetime.fromisoformat(departure.replace('Z','+00:00'))
    if base.tzinfo is None:raise ValueError('Departure time must include a timezone offset.')
    now=datetime.now(timezone.utc)
    if base<now-timedelta(minutes=15) or base>now+timedelta(hours=48):raise ValueError('Departure must be within the next 48 hours.')
    paths=fetch_routes(origin,destination);results=[]
    for i,path in enumerate(paths):
        geometry=path['geometry']['coordinates'];duration=path['duration'];distance=path['distance']*MILES_PER_METER
        checkpoints=route_checkpoints(geometry,duration,spacing)
        etas=[base+timedelta(seconds=p['offset_seconds']) for p in checkpoints]
        forecasts=weather_at(checkpoints,etas)
        enriched=[]
        for checkpoint,eta,forecast in zip(checkpoints,etas,forecasts):
            enriched.append({**checkpoint,'eta':eta.isoformat(),'weather':forecast,'risk':classify(forecast['wind_mph'],forecast['rain_inches_hr'],forecast['snow_inches_hr'],load_lbs)})
        results.append({'id':i+1,'distance_miles':round(distance,1),'duration_minutes':round(duration/60),'arrival':(base+timedelta(seconds=duration)).isoformat(),'geometry':geometry,'checkpoints':enriched,'summary':summarize(enriched,distance)})
    results.sort(key=ranking_key)
    for rank,route in enumerate(results):route['recommended']=rank==0 and not route['summary']['no_travel']
    return {'origin':origin,'destination':destination,'departure':base.isoformat(),'load_lbs':load_lbs,'spacing_miles':spacing,'routes':results,'has_safe_route':any(not r['summary']['no_travel'] for r in results),'warning':'Routes use OSRM general driving directions and are NOT validated for truck restrictions. Weather estimates and ETAs are advisory only.'}
