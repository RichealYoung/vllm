"""Read-only aggregation of timed samples; may run locally after download."""
import hashlib
import json
import statistics as stat
from pathlib import Path

root=Path(__file__).resolve().parent
data=json.loads((root/'results.json').read_text())
assert data['passed']
rows=data['rows']
assert len(rows)==486
assert all(len(r['samples_ns'])==120 and r['verified_samples']==120 for r in rows)
assert json.loads((root/'correctness.json').read_text())['passed']
assert (root/'run.exit').read_text().strip()=='0'
env=json.loads((root/'environment.json').read_text())
for name,expected in env['source_files'].items():
    if name=='README.md':
        continue  # Final result prose is added after measurement.
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,name
table=[]
for length in (4096,16384,65536):
    for case in ('same','append','head','middle','tail','shorten'):
        cells={}
        methods=list(dict.fromkeys(r['method'] for r in rows))
        for method in methods:
            subset=[r for r in rows if r['length']==length and r['case']==case and r['method']==method]
            assert len(subset)==3
            vals=[stat.median(r['samples_ns'])/1000 for r in subset]
            cells[method]={'median_us':stat.median(vals),'range_us':[min(vals),max(vals)],
                           'runs_us':vals,'p95_us':stat.median(r['p95_us'] for r in subset)}
        native=cells['native']['median_us']
        maximum=cells['max_or_native']['median_us']
        winner=min(cells,key=lambda x:cells[x]['median_us'])
        for cell in cells.values():
            cell['saved_vs_native_us']=native-cell['median_us']
            cell['change_vs_native_pct']=(cell['median_us']/native-1)*100
        table.append({'length':length,'case':case,'methods':cells,'winner':winner,
                      'winner_gain_vs_max_pct':(1-cells[winner]['median_us']/maximum)*100})
out={'passed':True,'verified_timed_calls':len(rows)*120,
     'boundary_checks':json.loads((root/'correctness.json').read_text())['checks'],
     'table':table}
(root/'analysis.json').write_text(json.dumps(out,indent=2))
print('Verified timed calls:',out['verified_timed_calls'])
print('length case native max gallop_list c_list_equal c_list_unbox packed_word packed_avx2 winner')
for item in table:
    print(item['length'],item['case'],*[round(item['methods'][x]['median_us'],2)
          for x in ('native','max_or_native','gallop_list','c_list_equal','c_list_unbox','packed_word','packed_avx2')],item['winner'])
