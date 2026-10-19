"""Validate coverage and high-risk extraction cases against inspected PDF cells."""
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
data=json.loads((root/'public/data/foods.json').read_text(encoding='utf-8'))
foods={f['id']:f for f in data['foods']}
assert len(foods)==722
assert len(data['groups'])==17
keys={c['key'] for c in data['components']}
assert len(keys)==41
for f in foods.values():
    assert set(f['nutrients'])==keys
    assert len(f['raw'])==40
    assert len(f['pages'])==5
    assert all(v is None or isinstance(v,(int,float)) for v in f['nutrients'].values())
    assert f['groupId']==f['code'][:2]
    assert f['name']

# Standard, bracketed, and missing source cells are semantically different.
assert foods['010001']['nutrients']['protein']==14.8
assert foods['010016']['raw']['fat']=='[1.7]'
assert foods['010016']['nutrients']['fat']==1.7
assert 'lower-quality' in foods['010016']['quality']['fat']
assert foods['020007']['raw']['folate']=='[tr]'
assert foods['020007']['nutrients']['folate'] is None
assert set(foods['020007']['quality']['folate'])=={'trace','lower-quality'}
assert foods['010028']['raw']['alpha_tocopherol']=='<LOD'
assert foods['010028']['quality']['alpha_tocopherol']==['below-detection-limit']

# Source section repeats a peanut row before linseed: ordinal matching would
# incorrectly move every remaining fat-soluble vitamin result by one food.
assert foods['060008']['nutrients']['vitamin_e']==8.30
assert foods['060018']['nutrients']['vitamin_e']==36.00
assert foods['060018']['pages']['vitaminsADE']==213

# Page 273 has header geometry different from the actual data cell geometry.
assert {k:foods['100001']['nutrients'][k] for k in ['beta_carotene','retinol','vitamin_a_re','vitamin_a_rae','vitamin_d','vitamin_e','alpha_tocopherol']}=={'beta_carotene':1.0,'retinol':4.0,'vitamin_a_re':4.0,'vitamin_a_rae':4.0,'vitamin_d':0.0,'vitamin_e':0.01,'alpha_tocopherol':0.01}

# Wrapped recipe descriptions must include the line printed above their code.
assert foods['010214']['name'].startswith('Ferfer from fresh white enjera and beef meat sauce')
assert foods['010214']['nutrients']['iron'] is None # source page 66 is blank
assert foods['010224']['nutrients']['iron']==4.6

# The supplied PDF itself omits kcal for these fruits. Do not invent a source
# value or substitute zero for the unknown kcal quantity.
assert foods['050001']['nutrients']['energy_kj']==220
assert foods['050001']['nutrients']['energy_kcal'] is None
assert foods['050001']['state']=='raw'

# The visibly sequential cereal retinol column stays auditable and flagged.
assert foods['010077']['raw']['retinol']=='112'
assert 'source-anomaly' in foods['010077']['quality']['retinol']
assert sum('source-anomaly' in f['quality'].get('retinol',[]) for f in foods.values())==157
audit=json.loads((root/'public/data/data-audit.json').read_text(encoding='utf-8'))
assert all(audit['validation'].values())
print('PASS: 722 food codes, 17 groups, 41 keys; flags, missing values, source errata, wrapped descriptions, section duplicates and cell geometry verified.')
