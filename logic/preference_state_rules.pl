% Phase 1.2 visitor-state reasoning over the frozen Phase 1 ArtGraph snapshot.
% Missing support is always reported as not_recorded under a bounded-snapshot
% assumption; it is never asserted as a negative museum fact.

:- use_module(library(http/json)).
:- use_module(library(lists)).
:- use_module(library(pairs)).

preference_model_assumption(a_bounded_recorded_support_contrast,
    'Within the bounded snapshot, recorded support on liked versus disliked examples may indicate diagnostic evidence; unrecorded support is not factual absence.').
preference_model_assumption(a_component_rejection_can_suggest_interaction,
    'A liked conjunction plus separate disliked component-only examples may provisionally suggest an interaction explanation.').
preference_model_assumption(a_positive_cooccurrence_suggests_atomic_interest,
    'A liked artwork attribute may provisionally suggest an atomic interest.').

preference_artwork_support(Hypothesis, Artwork, FactIDs) :-
    hypothesis_definition(Hypothesis, tag, Value, _),
    about(Artwork, Value, Fact),
    FactIDs = [Fact].
preference_artwork_support(Hypothesis, Artwork, FactIDs) :-
    hypothesis_definition(Hypothesis, style, Value, _),
    has_style(Artwork, Value, Fact),
    FactIDs = [Fact].
preference_artwork_support(Hypothesis, Artwork, FactIDs) :-
    hypothesis_definition(Hypothesis, genre, Value, _),
    has_genre(Artwork, Value, Fact),
    FactIDs = [Fact].
preference_artwork_support(Hypothesis, Artwork, FactIDs) :-
    hypothesis_definition(Hypothesis, medium, Value, _),
    made_of(Artwork, Value, Fact),
    FactIDs = [Fact].
preference_artwork_support(Hypothesis, Artwork, FactIDs) :-
    hypothesis_definition(Hypothesis, movement, Movement, _),
    created_by(Artwork, Artist, CreationFact),
    belongs_to_movement(Artist, Movement, MovementFact),
    FactIDs = [CreationFact, MovementFact].

not_recorded_support(Hypothesis, Artwork) :-
    hypothesis_definition(Hypothesis, _, _, _),
    topic(Artwork, artwork, _, _),
    \+ preference_artwork_support(Hypothesis, Artwork, _).

positive_cooccurrence(Visitor, Hypothesis, Artwork, Observation, Facts) :-
    preference_observation(Observation, Visitor, likes, Artwork),
    preference_artwork_support(Hypothesis, Artwork, Facts).

negative_cooccurrence(Visitor, Hypothesis, Artwork, Observation, Facts) :-
    preference_observation(Observation, Visitor, dislikes, Artwork),
    preference_artwork_support(Hypothesis, Artwork, Facts).

positive_observation_count(Visitor, Hypothesis, Count) :-
    findall(Observation,
            positive_cooccurrence(Visitor, Hypothesis, _, Observation, _),
            Raw),
    sort(Raw, Observations),
    length(Observations, Count).

negative_observation_count(Visitor, Hypothesis, Count) :-
    findall(Observation,
            negative_cooccurrence(Visitor, Hypothesis, _, Observation, _),
            Raw),
    sort(Raw, Observations),
    length(Observations, Count).

mixed_atomic_evidence(Visitor, Hypothesis) :-
    positive_observation_count(Visitor, Hypothesis, Positive),
    negative_observation_count(Visitor, Hypothesis, Negative),
    Positive > 0,
    Negative > 0.

contrastive_atomic_candidate(Visitor, Hypothesis) :-
    positive_observation_count(Visitor, Hypothesis, Positive),
    negative_observation_count(Visitor, Hypothesis, 0),
    Positive > 0.

interaction_type_pair(tag, style).
interaction_type_pair(tag, genre).
interaction_type_pair(style, genre).

allowed_interaction(HypothesisA, HypothesisB) :-
    hypothesis_definition(HypothesisA, TypeA, _, _),
    hypothesis_definition(HypothesisB, TypeB, _, _),
    interaction_type_pair(TypeA, TypeB).

interaction_candidate(Visitor, HypothesisA, HypothesisB, Proof) :-
    allowed_interaction(HypothesisA, HypothesisB),
    preference_observation(LikedObservation, Visitor, likes, LikedArtwork),
    preference_artwork_support(HypothesisA, LikedArtwork, LikedFactsA),
    preference_artwork_support(HypothesisB, LikedArtwork, LikedFactsB),
    preference_observation(DislikedObservationA, Visitor, dislikes, DislikedArtworkA),
    preference_artwork_support(HypothesisA, DislikedArtworkA, DislikedFactsA),
    not_recorded_support(HypothesisB, DislikedArtworkA),
    preference_observation(DislikedObservationB, Visitor, dislikes, DislikedArtworkB),
    DislikedArtworkA \= DislikedArtworkB,
    preference_artwork_support(HypothesisB, DislikedArtworkB, DislikedFactsB),
    not_recorded_support(HypothesisA, DislikedArtworkB),
    append([LikedFactsA, LikedFactsB, DislikedFactsA, DislikedFactsB], RawFacts),
    sort(RawFacts, FactIDs),
    sort([LikedObservation, DislikedObservationA, DislikedObservationB], ObservationIDs),
    Proof = proof{
        predicate:interaction_candidate,
        rule_id:r_component_rejection_suggests_interaction,
        assumption_ids:[
            a_bounded_recorded_support_contrast,
            a_component_rejection_can_suggest_interaction
        ],
        observation_ids:ObservationIDs,
        artgraph_fact_ids:FactIDs,
        liked_artwork:LikedArtwork,
        disliked_component_examples:[DislikedArtworkA, DislikedArtworkB],
        not_recorded_components:[
            not_recorded{artwork_id:DislikedArtworkA, hypothesis_id:HypothesisB},
            not_recorded{artwork_id:DislikedArtworkB, hypothesis_id:HypothesisA}
        ]
    }.

atomic_status(Visitor, Hypothesis, explicitly_rejected) :-
    preference_observation(_, Visitor, explicit_rejection, Hypothesis), !.
atomic_status(Visitor, Hypothesis, explicitly_confirmed) :-
    preference_observation(_, Visitor, explicit_interest, Hypothesis), !.
atomic_status(Visitor, Hypothesis, reinforced) :-
    positive_observation_count(Visitor, Hypothesis, Positive),
    Positive >= 2,
    negative_observation_count(Visitor, Hypothesis, 0), !.
atomic_status(Visitor, Hypothesis, mixed) :-
    mixed_atomic_evidence(Visitor, Hypothesis), !.
atomic_status(Visitor, Hypothesis, candidate) :-
    contrastive_atomic_candidate(Visitor, Hypothesis).

atomic_status_rank(explicitly_confirmed, 0).
atomic_status_rank(reinforced, 1).
atomic_status_rank(candidate, 2).
atomic_status_rank(mixed, 3).
atomic_status_rank(explicitly_rejected, 4).

atomic_evidence_proof(Visitor, Hypothesis, Status, Proof) :-
    findall(Observation-Facts,
            positive_cooccurrence(Visitor, Hypothesis, _, Observation, Facts),
            PositiveRows),
    findall(Observation-Facts,
            negative_cooccurrence(Visitor, Hypothesis, _, Observation, Facts),
            NegativeRows),
    findall(Observation,
            ( member(Observation-_, PositiveRows)
            ; member(Observation-_, NegativeRows)
            ; preference_observation(Observation, Visitor, explicit_interest, Hypothesis)
            ; preference_observation(Observation, Visitor, explicit_rejection, Hypothesis)
            ),
            RawObservations),
    sort(RawObservations, ObservationIDs),
    findall(Fact,
            ( member(_-Facts, PositiveRows), member(Fact, Facts)
            ; member(_-Facts, NegativeRows), member(Fact, Facts)
            ),
            RawFacts),
    sort(RawFacts, FactIDs),
    positive_observation_count(Visitor, Hypothesis, PositiveCount),
    negative_observation_count(Visitor, Hypothesis, NegativeCount),
    Proof = proof{
        predicate:atomic_evidence_status,
        rule_id:r_signed_recorded_cooccurrence_status,
        assumption_ids:[a_bounded_recorded_support_contrast],
        observation_ids:ObservationIDs,
        artgraph_fact_ids:FactIDs,
        positive_observation_count:PositiveCount,
        negative_observation_count:NegativeCount,
        status:Status
    }.

atomic_explanation_record(Visitor, Hypothesis, Record) :-
    atomic_status(Visitor, Hypothesis, Status),
    atomic_evidence_proof(Visitor, Hypothesis, Status, Proof),
    Record = explanation{
        kind:atomic,
        components:[Hypothesis],
        status:Status,
        proof:Proof
    }.

interaction_explanation_record(Visitor, HypothesisA, HypothesisB, Record) :-
    interaction_candidate(Visitor, HypothesisA, HypothesisB, Proof),
    Record = explanation{
        kind:all_of,
        components:[HypothesisA, HypothesisB],
        status:interaction_candidate,
        proof:Proof
    }.

explanation_key(Explanation, 0-Components) :-
    get_dict(kind, Explanation, all_of),
    get_dict(components, Explanation, Components).
explanation_key(Explanation, Rank-Components) :-
    get_dict(kind, Explanation, atomic),
    get_dict(components, Explanation, Components),
    get_dict(status, Explanation, Status),
    atomic_status_rank(Status, AtomicRank),
    Rank is AtomicRank + 1.

preference_explanations(Visitor, compositional, Explanations) :-
    findall(Key-Explanation,
            ( interaction_explanation_record(Visitor, _, _, Explanation),
              explanation_key(Explanation, Key)
            ),
            InteractionRows),
    findall(Key-Explanation,
            ( hypothesis_definition(Hypothesis, _, _, _),
              atomic_explanation_record(Visitor, Hypothesis, Explanation),
              explanation_key(Explanation, Key)
            ),
            AtomicRows),
    append(InteractionRows, AtomicRows, RawRows),
    keysort(RawRows, SortedRows),
    pairs_values(SortedRows, Explanations).
preference_explanations(Visitor, atomic, Explanations) :-
    findall(Hypothesis, positive_cooccurrence(Visitor, Hypothesis, _, _, _), Raw),
    sort(Raw, Hypotheses),
    findall(explanation{
                kind:atomic,
                components:[Hypothesis],
                status:candidate,
                proof:proof{
                    predicate:positive_atomic_interest,
                    rule_id:r_like_suggests_attribute_hypothesis,
                    assumption_ids:[a_positive_cooccurrence_suggests_atomic_interest],
                    observation_ids:ObservationIDs,
                    artgraph_fact_ids:FactIDs
                }
            },
            ( member(Hypothesis, Hypotheses),
              findall(Observation,
                      positive_cooccurrence(Visitor, Hypothesis, _, Observation, _),
                      RawObservations),
              sort(RawObservations, ObservationIDs),
              findall(Fact,
                      ( positive_cooccurrence(Visitor, Hypothesis, _, _, Facts),
                        member(Fact, Facts)
                      ),
                      RawFacts),
              sort(RawFacts, FactIDs)
            ),
            Explanations).

has_interaction(Visitor) :- interaction_candidate(Visitor, _, _, _), !.

compositional_support_score(Visitor, Artwork, 1000, Explanation, FactIDs) :-
    interaction_explanation_record(Visitor, A, B, Explanation),
    preference_artwork_support(A, Artwork, FactsA),
    preference_artwork_support(B, Artwork, FactsB),
    append(FactsA, FactsB, RawFacts),
    sort(RawFacts, FactIDs).
compositional_support_score(Visitor, Artwork, Score, Explanation, FactIDs) :-
    \+ has_interaction(Visitor),
    atomic_explanation_record(Visitor, Hypothesis, Explanation),
    Explanation.status \= explicitly_rejected,
    preference_artwork_support(Hypothesis, Artwork, FactIDs),
    ( contrastive_atomic_candidate(Visitor, Hypothesis) -> Score = 200
    ; Explanation.status = reinforced -> Score = 100
    ; Explanation.status = explicitly_confirmed -> Score = 100
    ; Explanation.status = candidate -> Score = 50
    ; Score = -10
    ).

atomic_support_score(Visitor, Artwork, 100, Explanation, FactIDs) :-
    positive_cooccurrence(Visitor, Hypothesis, _, _, _),
    preference_artwork_support(Hypothesis, Artwork, FactIDs),
    Explanation = explanation{kind:atomic, components:[Hypothesis], status:candidate}.

action_score(Visitor, compositional, Artwork, Score, Supports) :-
    findall(Value-Support,
            compositional_support_score(Visitor, Artwork, Value, Support, _),
            Rows),
    findall(Value, member(Value-_, Rows), Values),
    sum_list(Values, Score),
    findall(Support, member(_-Support, Rows), RawSupports),
    sort(RawSupports, Supports).
action_score(Visitor, atomic, Artwork, Score, Supports) :-
    findall(Value-Support,
            atomic_support_score(Visitor, Artwork, Value, Support, _),
            Rows),
    findall(Value, member(Value-_, Rows), Values),
    sum_list(Values, Score),
    findall(Support, member(_-Support, Rows), RawSupports),
    sort(RawSupports, Supports).

action_fact_ids(Visitor, compositional, Artwork, FactIDs) :-
    findall(Fact,
            ( compositional_support_score(Visitor, Artwork, _, _, Facts),
              member(Fact, Facts)
            ),
            Raw),
    sort(Raw, FactIDs).
action_fact_ids(Visitor, atomic, Artwork, FactIDs) :-
    findall(Fact,
            ( atomic_support_score(Visitor, Artwork, _, _, Facts),
              member(Fact, Facts)
            ),
            Raw),
    sort(Raw, FactIDs).

observed_artwork(Visitor, Artwork) :-
    preference_observation(_, Visitor, Kind, Artwork),
    memberchk(Kind, [likes, dislikes]).

ranked_actions(Visitor, Mode, Actions) :-
    findall(Key-Action,
            ( allowed_action_artwork(Artwork),
              \+ observed_artwork(Visitor, Artwork),
              action_score(Visitor, Mode, Artwork, Score, Supports),
              action_fact_ids(Visitor, Mode, Artwork, FactIDs),
              topic(Artwork, artwork, Label, _),
              NegativeScore is -Score,
              Key = NegativeScore-Artwork,
              Action = action{
                  artwork_id:Artwork,
                  label:Label,
                  score:Score,
                  supports:Supports,
                  proof:proof{
                      predicate:ranked_preference_action,
                      rule_id:r_rank_by_preference_explanation_support,
                      artgraph_fact_ids:FactIDs
                  }
              }
            ),
            RawRows),
    keysort(RawRows, SortedRows),
    pairs_values(SortedRows, Actions).

observation_evidence(Visitor, Evidence) :-
    findall(Row,
            ( preference_observation(Observation, Visitor, Kind, Artwork),
              memberchk(Kind, [likes, dislikes]),
              preference_artwork_support(Hypothesis, Artwork, FactIDs),
              Row = evidence{
                  observation_id:Observation,
                  kind:Kind,
                  artwork_id:Artwork,
                  hypothesis_id:Hypothesis,
                  artgraph_fact_ids:FactIDs
              }
            ),
            Raw),
    sort(Raw, Evidence).

write_preference_state_json(Visitor) :-
    preference_state_mode(Visitor, Mode),
    preference_explanations(Visitor, Mode, Explanations),
    ranked_actions(Visitor, Mode, Actions),
    observation_evidence(Visitor, Evidence),
    Result = _{
        status:ok,
        visitor:Visitor,
        mode:Mode,
        preference_explanations:Explanations,
        ranked_actions:Actions,
        observation_evidence:Evidence
    },
    json_write_dict(current_output, Result, [width(0)]),
    nl.
