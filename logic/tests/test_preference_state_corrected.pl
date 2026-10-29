:- ensure_loaded('../clarification_generated_facts.pl').
:- ensure_loaded('../clarification_hypotheses.pl').
:- dynamic preference_observation/4, allowed_action_artwork/1, preference_state_mode/2.
:- dynamic observation_order/2, observation_components/2, superseded_observation/1.
:- dynamic hidden_fact/1, incomplete_evidence/0.
:- discontiguous preference_observation/4, observation_order/2.
preference_observation(l,v,likes,ag_8416).
preference_observation(d1,v,dislikes,ag_13231).
preference_observation(d2,v,dislikes,ag_8296).
observation_order(l,0). observation_order(d1,1). observation_order(d2,2).
allowed_action_artwork(ag_20804). allowed_action_artwork(ag_8415).
allowed_action_artwork(ag_14531). allowed_action_artwork(ag_8145).
:- ensure_loaded('../preference_state_corrected_rules.pl').

:- begin_tests(preference_state_corrected).

test(flagship_provisional_not_primary,[nondet]) :-
    c_explanations(v,compositional,Es),c_ranking(v,Es,As),c_decision(Es,As,P,D),
    P==null,D.action_type==clarify,
    member(E,Es),E.kind==all_of,E.status==interaction_candidate.

test(mixed_is_not_rejection) :- c_atomic_status(v,h_portrait_genre,mixed).

test(known_missingness_blocks_interaction,
    [setup(assertz(user:incomplete_evidence)),cleanup(retractall(user:incomplete_evidence))]) :-
    \+ c_interaction(v,_,_),
    c_explanations(v,compositional,Es),c_ranking(v,Es,As),c_decision(Es,As,_,D),
    D.action_type==insufficient_evidence.

test(mask_removes_support_not_source_fact,
    [setup(assertz(user:hidden_fact(agf_622844512b2c37462fa9))),cleanup(retractall(user:hidden_fact(_)))]) :-
    \+ c_support(h_portrait_genre,ag_8416,_),
    has_genre(ag_8416,ag_9,agf_622844512b2c37462fa9).

test(explicit_confirmation_survives_dislike,
    [setup((assertz(user:preference_observation(e,v,explicit_interest,h_portrait_genre)),assertz(user:observation_order(e,3)))),
     cleanup((retractall(user:preference_observation(e,_,_,_)),retractall(user:observation_order(e,_))))]) :-
    c_atomic_status(v,h_portrait_genre,explicitly_confirmed).

test(explicit_rejection_blocks_inferred_pair,
    [setup((assertz(user:preference_observation(e,v,explicit_rejection,h_portrait_genre)),assertz(user:observation_order(e,3)))),
     cleanup((retractall(user:preference_observation(e,_,_,_)),retractall(user:observation_order(e,_))))]) :-
    \+ c_interaction(v,_,_).

test(superseded_like_still_exists_but_not_active,
    [setup(assertz(user:superseded_observation(l))),cleanup(retractall(user:superseded_observation(_)))]) :-
    preference_observation(l,v,likes,ag_8416),\+ c_observation(l,v,likes,ag_8416),
    \+ c_interaction(v,_,_).

test(confirmation_changes_action,
    [setup((assertz(user:preference_observation(e,v,explicit_conjunction,preference_pair)),
            assertz(user:observation_components(e,[h_expressionist_style,h_portrait_genre])),assertz(user:observation_order(e,3)))),
     cleanup((retractall(user:preference_observation(e,_,_,_)),retractall(user:observation_components(e,_)),retractall(user:observation_order(e,_))))]) :-
    c_explanations(v,compositional,Es),c_ranking(v,Es,As),c_decision(Es,As,_,D),
    D.action_type==recommend,D.artwork_id==ag_20804.

test(no_evidence_abstains) :-
    c_explanations(empty,compositional,Es),c_ranking(empty,Es,As),c_decision(Es,As,_,D),
    D.action_type==insufficient_evidence.

test(proof_assumptions_and_fact_ids,[nondet]) :-
    c_interaction(v,_,P),memberchk(a_component_rejection_can_suggest_interaction,P.assumption_ids),
    memberchk(agf_bc28f5fe332dea18b2b7,P.artgraph_fact_ids),length(P.not_recorded_components,2).

:- end_tests(preference_state_corrected).
