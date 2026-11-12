% Evaluation-only ablation of inferred conjunctions.
% Load the production corrected-v2 policy, then replace only c_interaction/3.
% Explicit conjunctions remain represented by c_record/5 via c_explicit/5.
:- ensure_loaded('../../logic/preference_state_corrected_rules.pl').

:- abolish(c_interaction/3).
c_interaction(_, _, _) :- fail.

