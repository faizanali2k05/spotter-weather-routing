"""Deterministic, auditable application of Spotter's weather/load thresholds."""
LEVELS=['Low','Moderate','High','Severe','No Travel']
def classify(wind_mph:float,rain_inches_hr:float,snow_inches_hr:float,load_lbs:float)->str:
    def wind_level(v):
        return 0 if v<25 else 1 if v<35 else 2 if v<45 else 3 if v<55 else 4
    def rain_level(v):
        return 0 if v<.10 else 1 if v<.25 else 2 if v<.50 else 3 if v<=1 else 4
    def snow_level(v):
        return 0 if v<.5 else 1 if v<1 else 2 if v<2 else 3 if v<=3 else 4
    level=max(wind_level(wind_mph),rain_level(rain_inches_hr),snow_level(snow_inches_hr))
    if wind_mph>=55 or (45<=wind_mph<55 and load_lbs>30000):level=4
    elif 35<=wind_mph<45 and load_lbs>40000:level=max(level,3)
    return LEVELS[level]

def summarize(checkpoints, distance_miles):
    """Approximate exposed mileage using midpoint-sized segments per sample."""
    totals={name:0. for name in LEVELS}
    for i,point in enumerate(checkpoints):
        left=0 if i==0 else (checkpoints[i-1]['mile']+point['mile'])/2
        right=distance_miles if i==len(checkpoints)-1 else (point['mile']+checkpoints[i+1]['mile'])/2
        totals[point['risk']]+=max(0,right-left)
    total=sum(totals.values())
    mean=sum(i*totals[level] for i,level in enumerate(LEVELS))/total if total else 0
    return {'miles_by_risk':{k:round(v,1) for k,v in totals.items()},'average_risk':round(mean,3),'no_travel':totals['No Travel']>0}

def ranking_key(route):
    risk=route['summary']
    miles=risk['miles_by_risk']
    return (risk['no_travel'],miles['Severe'],miles['High'],risk['average_risk'],route['duration_minutes'])
