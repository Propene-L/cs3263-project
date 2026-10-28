# Clarification Selection Complexity

## Search cost

For `n` eligible artworks there are `n(n-1)/2 = O(n²)` unordered candidate
pairs. With `k` active hypotheses, support/prediction construction costs
`O(k)` per pair. Counting opposing determinate predictions can be implemented
as `prefer_a_count × prefer_b_count` after partitioning (`O(k)`), although the
Prolog proof currently materializes hypothesis-pair distinctions and may do
`O(k²)` work per artwork pair.

The exact Python selector therefore uses `O(n²k)` time and stores only the
current best candidate plus cached evidence sets. Its evidence membership
checks are set lookups.

The current Prolog path includes:

- a fresh SWI-Prolog process per selection;
- fact, hypothesis, state, and rule file loading;
- enumeration of `O(n²)` grounded artwork pairs;
- prediction proof records for `k` hypotheses;
- explicit pairwise distinction proof construction, up to `O(k²)` per pair;
- `setof/3` sorting of eligible scored candidates, adding up to
  `O(n² log n²)` comparison work;
- JSON proof serialization and Python subprocess parsing.

Fresh processes provide isolation and avoid stale tables, but startup and fact
loading dominate small candidate universes. Proof construction is a genuine
capability difference from the exact Python baseline.

## Measured scaling

Command:

```powershell
.\.venv\Scripts\python.exe -m evaluation.benchmark_clarification_complexity
```

Six active hypotheses were held constant. Python was repeated five times and
Prolog three times per candidate count. These local wall-clock measurements
are not cross-machine benchmarks.

| Candidates | Unordered pairs | Exact Python mean | Compositional Prolog mean |
|---:|---:|---:|---:|
| 10 | 45 | 0.124 ms | 391.509 ms |
| 20 | 190 | 0.714 ms | 392.493 ms |
| 40 | 780 | 3.553 ms | 479.324 ms |
| 80 | 3,160 | 12.340 ms | 829.325 ms |
| 112 | 6,216 | 55.540 ms | 1,226.075 ms |

The quadratic search becomes visible for both implementations after startup
costs cease to dominate. On the full mixed benchmark, exact Python averaged
24.638 ms per selection and compositional Prolog 829.858 ms. All 128
Prolog selections matched the exact Python optimum, so the runtime difference
does not reflect a different objective.

## Optimization boundaries

Safe optimizations that preserve the objective include memoizing
artwork–hypothesis support, caching prediction partitions for a fixed active
set, counting opposing groups rather than rediscovering equivalent pairs when
proof output is not requested, and keeping initialization timing separate
from inference timing.

The symbolic engine is not replaced by Python in Phase 1.1. A future Prolog
optimization should retain exact scores, stable tie-breaking, proof fact IDs,
response assumptions, and stateless session semantics. Persistent Prolog
processes would need explicit state/table invalidation and isolation tests.
