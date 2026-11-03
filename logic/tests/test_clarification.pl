:- ensure_loaded('../clarification_generated_facts.pl').
:- ensure_loaded('../clarification_hypotheses.pl').
:- ensure_loaded('../clarification_test_scenarios.pl').
:- ensure_loaded('../clarification_rules.pl').

:- begin_tests(clarification).

test(real_indirect_movement_attribute_has_two_source_facts, [nondet]) :-
    artwork_attribute(ag_8415, movement, ag_124670, FactIDs),
    FactIDs = [CreatedByFact, MovementFact],
    source_fact(CreatedByFact, created_by, ag_8415, _, _),
    source_fact(MovementFact, belongs_to_movement, _, ag_124670, _).

test(liked_artwork_suggests_multiple_typed_hypotheses, [nondet]) :-
    hypothesis_evidence(v_like, h_musical_subject, obs_like_cello, strong,
                        ag_10472, MusicFacts,
                        r_like_suggests_attribute_hypothesis),
    hypothesis_evidence(v_like, h_expressionist_style, obs_like_cello, strong,
                        ag_10472, StyleFacts,
                        r_like_suggests_attribute_hypothesis),
    MusicFacts \= StyleFacts.

test(competing_hypotheses_predict_opposite_choices, [nondet]) :-
    hypothesis_prediction(h_musical_subject, ag_8966, ag_8388,
                          prefer_a, MusicPrediction),
    hypothesis_prediction(h_expressionist_style, ag_8966, ag_8388,
                          prefer_b, StylePrediction),
    MusicPrediction.option_a_fact_ids = [agf_8311ec557e70c76e928c],
    StylePrediction.option_b_fact_ids = [agf_1736790c2cb4048d6d8a].

test(selected_question_is_discriminative_and_proven, [nondet]) :-
    selected_question(v_pair, ArtworkA, ArtworkB, Score, Statistics),
    Score > 0,
    ArtworkA @< ArtworkB,
    Statistics.distinguished_hypothesis_pair_count >= 1,
    question_dict(v_pair, ArtworkA, ArtworkB, Score, Statistics, Question),
    Question.proof.observation_ids == [obs_pair_expression, obs_pair_music],
    Question.proof.artgraph_fact_ids \= [],
    Question.proof.children \= [].

test(prefer_a_contradicts_opposite_prediction, [nondet]) :-
    active_hypothesis(v_response, h_musical_subject),
    \+ active_hypothesis(v_response, h_expressionist_style),
    contradicted_hypothesis(v_response, h_expressionist_style,
                            obs_response_choice,
                            r_response_contradicts_prediction).

test(unsure_does_not_eliminate_hypotheses, [nondet]) :-
    active_hypothesis(v_unsure, h_musical_subject),
    active_hypothesis(v_unsure, h_expressionist_style).

test(previously_asked_artworks_are_ineligible, [nondet]) :-
    \+ eligible_option(v_response, ag_8966),
    \+ eligible_option(v_response, ag_8388).

test(one_hypothesis_has_no_discriminative_question, [fail]) :-
    selected_question(v_single, _, _, _, _).

test(question_proof_is_a_tree_not_flat_ids, [nondet]) :-
    selected_question(v_pair, ArtworkA, ArtworkB, Score, Statistics),
    question_dict(v_pair, ArtworkA, ArtworkB, Score, Statistics, Question),
    Question.proof.children = [Eligibility, Discrimination],
    Eligibility.predicate == eligible_question,
    Discrimination.predicate == hypothesis_discrimination,
    Discrimination.children = [FirstDistinction|_],
    FirstDistinction.children = [_, _].

:- end_tests(clarification).
