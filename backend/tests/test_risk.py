from routing.risk import classify,ranking_key,summarize

def test_thresholds():
 assert classify(24.9,0,0,0)=='Low'
 assert classify(25,0,0,0)=='Moderate'
 assert classify(35,0,0,0)=='High'
 assert classify(45,0,0,0)=='Severe'
 assert classify(55,0,0,0)=='No Travel'
 assert classify(45,0,0,30001)=='No Travel'
 assert classify(45,0,0,30000)=='Severe'
 assert classify(35,0,0,40001)=='Severe'
 assert classify(35,0,0,40000)=='High'
 assert classify(0,1.01,0,0)=='No Travel'
 assert classify(0,0,3.01,0)=='No Travel'

def test_mileage():
 out=summarize([{'mile':0,'risk':'Low'},{'mile':50,'risk':'Severe'},{'mile':100,'risk':'Low'}],100)
 assert out['miles_by_risk']['Severe']==50
 assert out['miles_by_risk']['Low']==50
