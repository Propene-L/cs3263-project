:- ensure_loaded('../clarification_generated_facts.pl').
:- ensure_loaded('../clarification_hypotheses.pl').

:- dynamic preference_observation/4.
:- dynamic allowed_action_artwork/1.
:- dynamic preference_state_mode/2.
:- discontiguous preference_state_mode/2.
:- discontiguous preference_observation/4.

preference_state_mode(v_flagship, compositional).
preference_observation(obs_like_albert, v_flagship, likes, ag_8416).
preference_observation(obs_dislike_bird, v_flagship, dislikes, ag_13231).
preference_observation(obs_dislike_boy, v_flagship, dislikes, ag_8296).

preference_state_mode(v_contrastive, compositional).
preference_observation(obs_like_cellist, v_contrastive, likes, ag_10472).
preference_observation(obs_dislike_albert, v_contrastive, dislikes, ag_8416).

allowed_action_artwork(ag_20804).
allowed_action_artwork(ag_8415).
allowed_action_artwork(ag_14531).
allowed_action_artwork(ag_42361).

:- ensure_loaded('../preference_state_rules.pl').

:- begin_tests(preference_state).

test(flagship_interaction_is_derived_once_with_named_assumptions) :-
    findall(Proof,
            interaction_candidate(
                v_flagship,
                h_expressionist_style,
                h_portrait_genre,
                Proof),
            Proofs),
    Proofs = [Proof],
    Proof.rule_id == r_component_rejection_suggests_interaction,
    memberchk(a_bounded_recorded_support_contrast, Proof.assumption_ids),
    memberchk(a_component_rejection_can_suggest_interaction, Proof.assumption_ids),
    Proof.observation_ids == [obs_dislike_bird, obs_dislike_boy, obs_like_albert].

test(flagship_interaction_proof_has_real_fact_ids, [nondet]) :-
    interaction_candidate(
        v_flagship,
        h_expressionist_style,
        h_portrait_genre,
        Proof),
    forall(member(Fact, [
               agf_8a4cce07ba2a1ca7c617,
               agf_622844512b2c37462fa9,
               agf_bc28f5fe332dea18b2b7,
               agf_b9a2ae950dd18cec4bac
           ]),
           memberchk(Fact, Proof.artgraph_fact_ids)).

test(flagship_ranks_baby_above_adam_and_eve, [nondet]) :-
    ranked_actions(v_flagship, compositional, [Baby|Actions]),
    Baby.artwork_id == ag_20804,
    Baby.score =:= 1000,
    memberchk(agf_7f54f5f65b1cedf3fe4f, Baby.proof.artgraph_fact_ids),
    memberchk(agf_373d77fbb313b7f40e0d, Baby.proof.artgraph_fact_ids),
    member(Adam, Actions),
    Adam.artwork_id == ag_8415,
    Adam.score =:= 0.

test(shared_liked_disliked_attributes_are_mixed) :-
    atomic_status(v_contrastive, h_expressionist_style, mixed),
    atomic_status(v_contrastive, h_portrait_genre, mixed),
    atomic_status(v_contrastive, h_oil_medium, mixed).

test(musical_subject_is_contrastive_and_clean_probe_ranks_first) :-
    contrastive_atomic_candidate(v_contrastive, h_musical_subject),
    ranked_actions(v_contrastive, compositional, [Probe|_]),
    Probe.artwork_id == ag_14531,
    Probe.score =:= 200.

test(not_recorded_is_not_a_negative_source_fact) :-
    not_recorded_support(h_portrait_genre, ag_13231),
    \+ source_fact(_, not_recorded_support, _, _, _).

:- end_tests(preference_state).
