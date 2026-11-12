# Interaction-inference ablation findings

The ablation executed the same corrected-v2 Prolog policy, facts, observations, candidate sets, ranking, and decision rules while replacing only `c_interaction/3` with failure. The production rule file was not edited. Alternative authored worlds were averaged within each of the 32 scenarios; the 36 worlds were not treated as independent samples.

## Category results

| Category | Full primary accuracy | Ablated primary accuracy | Full false interaction | Ablated false interaction | Full action accuracy | Ablated action accuracy |
|---|---:|---:|---:|---:|---:|---:|
| true_atomic | 100.0% | 100.0% | 0.0% | 0.0% | 100.0% | 100.0% |
| multiple_independent | 75.0% | 75.0% | 0.0% | 0.0% | 75.0% | 75.0% |
| true_conjunction | 100.0% | 100.0% | 0.0% | 0.0% | 100.0% | 100.0% |
| noisy | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |
| contradictory | 100.0% | 100.0% | 0.0% | 0.0% | 100.0% | 100.0% |
| missing_evidence | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |
| ambiguous | 0.0% | 0.0% | 12.5% | 0.0% | 100.0% | 100.0% |
| explicit_correction | 100.0% | 100.0% | 0.0% | 0.0% | 100.0% | 100.0% |

## Causal interpretation

The explanation set changed in **1/32** scenarios; the action type changed in **0/32**, the selected recommendation in **0/32**, and the clarification question in **1/32**. Changed scenario IDs: `ambiguous_albert`.

1. **True conjunctions:** all four robustness cases state their conjunction explicitly. They therefore remain available through `c_explicit/5`; disabling inferred interaction does not remove them. This benchmark cannot attribute their accuracy to `c_interaction/3`.
2. **Independent interests:** the guard against combining separately confirmed interests already prevents inferred conjunctions, so the ablation should have no benefit here.
3. **Ambiguous evidence:** the changed cases show whether the provisional interaction is removed and whether the system asks an atomic rather than conjunctive clarification. This is the main measured effect of the rule.
   In `ambiguous_albert`, the full policy asked whether Expressionist style and portrait genre formed a conjunction; the ablation instead asked about Expressionism movement. Removing the inferred interaction eliminated the category's 12.5% false-interaction rate, but also reduced explanation recall from 100.0% to 87.5% and top-1 relevance from 87.5% to 75.0% under the two-world scenario average.
4. **Non-conjunction categories:** unchanged results are a useful isolation check. Any change outside scenarios containing an inferred interaction would indicate an over-broad ablation.

## Limitations

The 32 scenarios were authored controlled worlds, not observations from museum visitors. The true-conjunction category exercises explicit representation rather than inferred conjunction discovery, so a future independently reviewed benchmark would be required to estimate the accuracy benefit of `c_interaction/3` on genuinely latent conjunctions.
