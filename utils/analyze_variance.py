import json
import sys

with open('cost_estimates/7-report_cost_estimates.json') as f:
    data = json.load(f)

print('🔍 VARIANCE ANALYSIS\n')
print('='*70)

# Calculate variance for each estimate
variances = []
for est in data['cost_estimates']:
    low = est['estimated_low']
    high = est['estimated_high']
    variance = high - low
    variance_pct = ((high - low) / low * 100) if low > 0 else 0
    variances.append({
        'desc': est['description'][:60],
        'low': low,
        'high': high,
        'variance': variance,
        'variance_pct': variance_pct,
        'category': est['category']
    })

# Sort by absolute variance
variances.sort(key=lambda x: x['variance'], reverse=True)

print('\nTOP 10 ISSUES DRIVING THE VARIANCE:\n')
for i, v in enumerate(variances[:10], 1):
    print(f'{i}. ${v["low"]:,} - ${v["high"]:,} (${v["variance"]:,} spread, {v["variance_pct"]:.0f}%)')
    print(f'   {v["desc"]}...')
    print()

total_variance = sum(v['variance'] for v in variances)
top10_variance = sum(v['variance'] for v in variances[:10])

print('='*70)
print(f'Total variance: ${total_variance:,}')
print(f'Top 10 issues account for: ${top10_variance:,} ({top10_variance/total_variance*100:.1f}%)')
print()
print('📊 By category:')
cats = {}
for v in variances:
    cat = v['category']
    if cat not in cats:
        cats[cat] = {'count': 0, 'variance': 0}
    cats[cat]['count'] += 1
    cats[cat]['variance'] += v['variance']

for cat, info in sorted(cats.items(), key=lambda x: x[1]['variance'], reverse=True):
    print(f'  {cat}: ${info["variance"]:,} variance across {info["count"]} issues')

