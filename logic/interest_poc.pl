% Phase 0.75 visitor-interest proof of concept.
% Imported ArtGraph facts are loaded separately from interest assumptions.
% Candidate eligibility is derived here in SWI-Prolog, never in Python.

:- use_module(library(lists)).
:- use_module(library(pairs)).
:- use_module(library(http/json)).

:- discontiguous candidate_support/5.

% Factual Layer A: typed artwork attributes with imported fact provenance.
artwork_attribute(Artwork, tag, Value, [Fact]) :-
    about(Artwork, Value, Fact).
artwork_attribute(Artwork, style, Value, [Fact]) :-
    has_style(Artwork, Value, Fact).
artwork_attribute(Artwork, genre, Value, [Fact]) :-
    has_genre(Artwork, Value, Fact).
artwork_attribute(Artwork, medium, Value, [Fact]) :-
    made_of(Artwork, Value, Fact).
artwork_attribute(Artwork, series, Value, [Fact]) :-
    part_of_series(Artwork, Value, Fact).
artwork_attribute(Artwork, period, Value, [Fact]) :-
    has_period(Artwork, Value, Fact).
artwork_attribute(Artwork, movement, Value, [CreatedByFact, MovementFact]) :-
    created_by(Artwork, Artist, CreatedByFact),
    belongs_to_movement(Artist, Value, MovementFact).

allowed_artwork(Artwork) :-
    topic(Artwork, artwork, _, _).

% Assumption Layer B: explicit liking is strong evidence. Familiarity is only
% weak evidence under the named r_weak_interest_from_familiarity assumption.
positive_observation(Visitor, Observation, Artwork, strong,
                     r_interest_from_like) :-
    visitor_observation(Observation, Visitor, likes, Artwork).
positive_observation(Visitor, Observation, Artwork, weak,
                     r_weak_interest_from_familiarity) :-
    visitor_observation(Observation, Visitor, knows, Artwork).

interest_signal(Visitor, Type, Value, Strength,
                signal(Observation, Artwork, SourceFacts, Rule), Rule) :-
    positive_observation(Visitor, Observation, Artwork, Strength, Rule),
    artwork_attribute(Artwork, Type, Value, SourceFacts).

negative_interest_signal(Visitor, Type, Value,
                         signal(Observation, Artwork, SourceFacts,
                                r_negative_interest_from_dislike)) :-
    visitor_observation(Observation, Visitor, dislikes, Artwork),
    artwork_attribute(Artwork, Type, Value, SourceFacts).

matched_signal(Visitor, Candidate, Type, Value, Strength,
               Observation, SourceArtwork, InterestRule,
               SourceFacts, CandidateFacts) :-
    interest_signal(Visitor, Type, Value, Strength,
                    signal(Observation, SourceArtwork, SourceFacts,
                           InterestRule), InterestRule),
    artwork_attribute(Candidate, Type, Value, CandidateFacts).

negative_match(Visitor, Candidate, Type, Value, Observation,
               SourceArtwork, SourceFacts, CandidateFacts) :-
    negative_interest_signal(
        Visitor, Type, Value,
        signal(Observation, SourceArtwork, SourceFacts,
               r_negative_interest_from_dislike)),
    artwork_attribute(Candidate, Type, Value, CandidateFacts).

attribute_key(Type, Value, Type-Value).

% A single direct tag match is deliberately insufficient. This rule requires
% two distinct typed attribute/value matches.
candidate_support(
    Visitor, Candidate, r_two_distinct_attribute_match,
    [Observation1, Observation2], FactIDs) :-
    matched_signal(Visitor, Candidate, Type1, Value1, _, Observation1, _, _,
                   SourceFacts1, CandidateFacts1),
    matched_signal(Visitor, Candidate, Type2, Value2, _, Observation2, _, _,
                   SourceFacts2, CandidateFacts2),
    attribute_key(Type1, Value1, Key1),
    attribute_key(Type2, Value2, Key2),
    Key1 @< Key2,
    append([SourceFacts1, CandidateFacts1, SourceFacts2, CandidateFacts2], RawFacts),
    sort(RawFacts, FactIDs).

% Repeated evidence requires the same attribute to be supported by two
% distinct positively observed artworks, plus a second distinct attribute.
repeated_interest_signal(
    Visitor, Type, Value, Observation1, Artwork1, Observation2, Artwork2) :-
    interest_signal(Visitor, Type, Value, _,
                    signal(Observation1, Artwork1, _, _), _),
    interest_signal(Visitor, Type, Value, _,
                    signal(Observation2, Artwork2, _, _), _),
    dif(Artwork1, Artwork2),
    Observation1 @< Observation2.

candidate_support(
    Visitor, Candidate, r_repeated_signal_plus_distinct_attribute,
    [Observation1, Observation2, Observation3], FactIDs) :-
    repeated_interest_signal(
        Visitor, Type1, Value1, Observation1, _, Observation2, _),
    artwork_attribute(Candidate, Type1, Value1, CandidateFacts1),
    matched_signal(Visitor, Candidate, Type2, Value2, _, Observation3, _, _,
                   SourceFacts2, CandidateFacts2),
    attribute_key(Type1, Value1, Key1),
    attribute_key(Type2, Value2, Key2),
    dif(Key1, Key2),
    matched_signal(Visitor, Candidate, Type1, Value1, _, Observation1, _, _,
                   SourceFacts1, _),
    append([SourceFacts1, CandidateFacts1, SourceFacts2, CandidateFacts2], RawFacts),
    sort(RawFacts, FactIDs).

% Negative preference is represented separately. The conservative pilot only
% declares a conflict after two distinct negative attribute matches.
strong_negative_conflict(Visitor, Candidate,
                         conflict(r_two_negative_attribute_matches,
                                  [Observation1, Observation2], FactIDs)) :-
    negative_match(Visitor, Candidate, Type1, Value1, Observation1, _,
                   SourceFacts1, CandidateFacts1),
    negative_match(Visitor, Candidate, Type2, Value2, Observation2, _,
                   SourceFacts2, CandidateFacts2),
    attribute_key(Type1, Value1, Key1),
    attribute_key(Type2, Value2, Key2),
    Key1 @< Key2,
    append([SourceFacts1, CandidateFacts1, SourceFacts2, CandidateFacts2], RawFacts),
    sort(RawFacts, FactIDs).

excluded_candidate(Visitor, Candidate, Observation, Kind) :-
    visitor_observation(Observation, Visitor, Kind, Candidate),
    memberchk(Kind, [knows, likes, dislikes, viewed, rejected]).

candidate_artwork(Visitor, Candidate) :-
    allowed_artwork(Candidate),
    candidate_support(Visitor, Candidate, _, _, _),
    \+ excluded_candidate(Visitor, Candidate, _, _),
    \+ strong_negative_conflict(Visitor, Candidate, _).

attribute_priority(style, 5).
attribute_priority(movement, 5).
attribute_priority(genre, 4).
attribute_priority(series, 4).
attribute_priority(period, 3).
attribute_priority(tag, 2).
attribute_priority(medium, 1).

signal_record(Visitor, Candidate, Record) :-
    matched_signal(Visitor, Candidate, Type, Value, Strength, Observation,
                   SourceArtwork, InterestRule, SourceFacts, CandidateFacts),
    Record = signal{
        type:Type,
        value:Value,
        strength:Strength,
        observation_id:Observation,
        source_artwork:SourceArtwork,
        interest_rule:InterestRule,
        source_fact_ids:SourceFacts,
        candidate_fact_ids:CandidateFacts
    }.

attribute_record(Type-Value, attribute{type:Type, value:Value}).

candidate_proof(Visitor, Candidate, Proof, MatchedCount, EvidenceCount,
                StrongCount, RuleCount, Specificity) :-
    findall(Type-Value,
            matched_signal(Visitor, Candidate, Type, Value, _, _, _, _, _, _),
            RawAttributes),
    sort(RawAttributes, Attributes),
    maplist(attribute_record, Attributes, AttributeRecords),
    length(Attributes, MatchedCount),
    findall(SourceArtwork,
            matched_signal(Visitor, Candidate, _, _, _, _, SourceArtwork, _, _, _),
            RawSources),
    sort(RawSources, Sources),
    length(Sources, EvidenceCount),
    findall(Observation,
            matched_signal(Visitor, Candidate, _, _, strong, Observation, _, _, _, _),
            RawStrong),
    sort(RawStrong, StrongObservations),
    length(StrongObservations, StrongCount),
    findall(Rule,
            candidate_support(Visitor, Candidate, Rule, _, _),
            RawRules),
    sort(RawRules, Rules),
    length(Rules, RuleCount),
    findall(Priority,
            (member(Type-_, Attributes), attribute_priority(Type, Priority)),
            Priorities),
    sum_list(Priorities, Specificity),
    findall(Record, signal_record(Visitor, Candidate, Record), RawSignals),
    sort(RawSignals, Signals),
    findall(Observation,
            ( member(Signal, Signals),
              get_dict(observation_id, Signal, Observation)
            ),
            RawObservationIDs),
    sort(RawObservationIDs, ObservationIDs),
    findall(Fact,
            ( member(Signal, Signals),
              ( member(Fact, Signal.source_fact_ids)
              ; member(Fact, Signal.candidate_fact_ids)
              )
            ),
            RawFacts),
    sort(RawFacts, FactIDs),
    Proof = proof{
        rule_ids:Rules,
        visitor_observation_ids:ObservationIDs,
        matched_attributes:AttributeRecords,
        signals:Signals,
        artgraph_fact_ids:FactIDs
    }.

% This is a transparent deterministic score, not a probability. Eligibility
% is established before ranking and remains entirely in Prolog.
candidate_recommendation(Visitor, Candidate, Score, Proof) :-
    eligible_candidates(Visitor, Candidates),
    member(Candidate, Candidates),
    candidate_proof(Visitor, Candidate, Proof, MatchedCount, EvidenceCount,
                    StrongCount, RuleCount, Specificity),
    Score is StrongCount * 10000 + EvidenceCount * 1000
             + MatchedCount * 100 + RuleCount * 10 + Specificity.

% candidate_artwork/2 can have several proofs for the same artwork. Ranking
% operates on the set of eligible artwork IDs, never on proof multiplicity.
eligible_candidates(Visitor, Candidates) :-
    setof(Candidate, candidate_artwork(Visitor, Candidate), Candidates),
    !.
eligible_candidates(_, []).

ranked_recommendations(Visitor, Ranked) :-
    findall(Key-Row,
            ( candidate_recommendation(Visitor, Candidate, Score, Proof),
              NegativeScore is -Score,
              Key = NegativeScore-Candidate,
              Row = recommendation{artwork_id:Candidate,
                                   deterministic_score:Score,
                                   proof:Proof}
            ),
            Rows),
    keysort(Rows, Sorted),
    pairs_values(Sorted, Ranked).

write_recommendations_json(Visitor) :-
    ranked_recommendations(Visitor, Ranked),
    json_write_dict(current_output,
                    _{visitor:Visitor, recommendations:Ranked},
                    [width(0)]),
    nl.

write_top_recommendations_json(Visitor, Limit) :-
    ranked_recommendations(Visitor, Ranked),
    prefix_length_at_most(Ranked, Limit, Top),
    json_write_dict(current_output,
                    _{visitor:Visitor, recommendations:Top},
                    [width(0)]),
    nl.

prefix_length_at_most(_, Limit, []) :-
    Limit =< 0,
    !.
prefix_length_at_most([], _, []) :- !.
prefix_length_at_most([Head|Tail], Limit, [Head|TopTail]) :-
    NextLimit is Limit - 1,
    prefix_length_at_most(Tail, NextLimit, TopTail).

