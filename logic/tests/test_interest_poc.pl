:- begin_tests(interest_poc).

:- ensure_loaded('../interest_generated_facts.pl').
:- ensure_loaded('../interest_poc.pl').
:- ensure_loaded('../interest_scenarios.pl').

test(real_about_is_typed_artwork_attribute, [nondet]) :-
    artwork_attribute(ag_10472, tag, ag_3236,
                      [agf_8e49e33270d2ff0f08d3]),
    source_fact(agf_8e49e33270d2ff0f08d3, about,
                ag_10472, ag_3236,
                'https://www.gennarovessio.com/artgraph-schema#about').

test(scenario_a_single_artwork_requires_two_attributes, [nondet]) :-
    candidate_support(v_single, ag_37634,
                      r_two_distinct_attribute_match,
                      ObservationIDs, FactIDs),
    member(obs_single_known_1, ObservationIDs),
    member(agf_8e49e33270d2ff0f08d3, FactIDs),
    member(agf_6874fdb88122b2574ed8, FactIDs),
    candidate_artwork(v_single, ag_37634).

test(single_direct_match_is_not_a_support_rule, [fail]) :-
    candidate_support(v_single, _, r_single_attribute_match, _, _).

test(scenario_b_repeated_evidence_rule, [nondet]) :-
    repeated_interest_signal(v_multi, tag, ag_3236,
                             obs_multi_known_1, ag_10472,
                             obs_multi_known_2, ag_37634),
    candidate_support(v_multi, ag_70351,
                      r_repeated_signal_plus_distinct_attribute,
                      ObservationIDs, FactIDs),
    member(obs_multi_known_1, ObservationIDs),
    member(obs_multi_known_2, ObservationIDs),
    member(agf_b1e8040472e9dfe602ed, FactIDs),
    candidate_artwork(v_multi, ag_70351).

test(scenario_c_rejection_changes_candidates, [nondet]) :-
    candidate_artwork(v_multi, ag_70351),
    \+ candidate_artwork(v_filtered, ag_70351),
    candidate_artwork(v_filtered, ag_11268).

test(explicit_like_is_strong_and_familiarity_is_weak, [nondet]) :-
    interest_signal(v_positive, tag, ag_3236, strong, _,
                    r_interest_from_like),
    interest_signal(v_single, tag, ag_3236, weak, _,
                    r_weak_interest_from_familiarity).

test(dislike_produces_separate_negative_conflict, [nondet]) :-
    negative_interest_signal(v_negative, tag, ag_3236, _),
    strong_negative_conflict(v_negative, ag_11268,
                             conflict(r_two_negative_attribute_matches,
                                      _, FactIDs)),
    member(agf_b969a266f8d65b33a343, FactIDs),
    \+ candidate_artwork(v_negative, ag_11268).

test(proof_contains_rules_observations_and_artgraph_facts, [nondet]) :-
    candidate_recommendation(v_multi, ag_70351, Score, Proof),
    Score > 0,
    member(r_two_distinct_attribute_match, Proof.rule_ids),
    member(r_repeated_signal_plus_distinct_attribute, Proof.rule_ids),
    member(obs_multi_known_1, Proof.visitor_observation_ids),
    member(agf_b1e8040472e9dfe602ed, Proof.artgraph_fact_ids).

test(ranking_contains_each_eligible_artwork_once) :-
    ranked_recommendations(v_single, Ranked),
    length(Ranked, 163),
    findall(Artwork,
            ( member(Row, Ranked),
              get_dict(artwork_id, Row, Artwork)
            ),
            ArtworkIDs),
    sort(ArtworkIDs, UniqueArtworkIDs),
    length(UniqueArtworkIDs, 163),
    Ranked = [Top|_],
    get_dict(artwork_id, Top, ag_37634),
    get_dict(deterministic_score, Top, 2237).

:- end_tests(interest_poc).

