"""Quick integration test for v1.1 changes."""
import importlib.util, json, shutil, sys
from pathlib import Path

PC = Path('.agents/scripts/plan-check.py')
SCHEMAS = Path('.agents/schemas/planning')
FIX = Path('tests/planning-skills/fixtures')

spec = importlib.util.spec_from_file_location('plan_check', PC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
pc = mod

# good-plan clean
gplan = FIX / 'good-plan'
plan = pc.Plan(gplan, SCHEMAS)
plan.load()
findings = plan.run()
problems = []
for f in findings:
    problems.append(f'good-plan: unexpected {f["severity"]} {f["code"]}')

# bad-plan
bplan = FIX / 'bad-plan'
bplan_obj = pc.Plan(bplan, SCHEMAS)
bplan_obj.load()
bfindings = bplan_obj.run()
got = set()
for f in bfindings:
    got.add(f['code'])
expected = {
    'DAG_CYCLE', 'DAG_UNKNOWN_TASK', 'OWNERSHIP_COLLISION_PARALLEL',
    'CONTRACT_UNKNOWN', 'NO_INTEGRATION_GATE', 'OPEN_BLOCKING_QUESTION',
    'MISSING_TASK_PACKAGE', 'VAGUE_ACCEPTANCE', 'AUDIT_VERDICT_MISMATCH',
}
for code in sorted(expected - got):
    problems.append(f'bad-plan: missing {code}, got {sorted(got)}')

sev = {}
for f in bfindings:
    sev[f['code']] = f['severity']
for code in ('DAG_CYCLE', 'DAG_UNKNOWN_TASK', 'OWNERSHIP_COLLISION_PARALLEL',
             'NO_INTEGRATION_GATE', 'OPEN_BLOCKING_QUESTION', 'MISSING_TASK_PACKAGE',
             'AUDIT_VERDICT_MISMATCH'):
    if sev.get(code) != 'BLOCKER':
        problems.append(f'bad-plan: {code} should be BLOCKER, got {sev.get(code)}')

# tampered
tampered = FIX / 'tampered'
if tampered.exists():
    shutil.rmtree(tampered)
try:
    shutil.copytree(FIX / 'good-plan', tampered)
    dag = tampered / 'dag.json'
    data = json.loads(dag.read_text(encoding='utf-8'))
    data.pop('edges')
    dag.write_text(json.dumps(data), encoding='utf-8')
    res = pc.validate_file(dag, SCHEMAS)
    if res['ok']:
        problems.append('tampered dag accepted')
    sc = json.loads((tampered / 'stage-contract.json').read_text(encoding='utf-8'))
    sc['schema'] = 'planning/stage-contract@999'
    (tampered / 'stage-contract.json').write_text(json.dumps(sc), encoding='utf-8')
    res2 = pc.validate_file(tampered / 'stage-contract.json', SCHEMAS)
    if res2['ok']:
        problems.append('wrong schema accepted')
finally:
    shutil.rmtree(tampered, ignore_errors=True)

if problems:
    for p in problems:
        print(f'FAIL: {p}')
    sys.exit(1)
else:
    print(f'PASS: good-plan clean, bad-plan {len(expected)} codes, tamper rejected')
    sys.exit(0)
