% Phase 1 logic-guided active preference clarification.
% ArtGraph facts, hypothesis vocabulary, and visitor state are loaded by the
% caller. Python validates/serializes state but does not derive questions.

:- use_module(library(http/json)).
:- use_module(library(lists)).
:- use_module(library(pairs)).

:- discontiguous artwork_attribute/4.

% Layer A: factual typed attributes with exact ArtGraph provenance.
artwork_attribute(Artwork, artist, Artist, [Fact]) :-
    created_by(Artwork, Artist, Fact).
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
artwork_attribute(Artwork, movement, Value, [CreatedFact, MovementFact]) :-
    created_by(Artwork, Artist, CreatedFact),
    belongs_to_movement(Artist, Value, MovementFact).

% Layer B: provisional hypothesis evidence. The assumption is always named.
hypothesis_evidence(Visitor, Hypothesis, Observation, explicit,
                    none, [], r_explicit_interest_hypothesis) :-
    visitor_observation(Observation, Visitor, explicit_interest, Hypothesis),
    hypothesis_definition(Hypothesis, _, _, _).
hypothesis_evidence(Visitor, Hypothesis, Observation, strong,
                    Artwork, Facts, r_like_suggests_attribute_hypothesis) :-
    visitor_observation(Observation, Visitor, likes, Artwork),
    hypothesis_definition(Hypothesis, Type, Value, _),
    artwork_attribute(Artwork, Type, Value, Facts).
hypothesis_evidence(Visitor, Hypothesis, Observation, weak,
                    Artwork, Facts, r_familiarity_suggests_attribute_hypothesis) :-
    visitor_observation(Observation, Visitor, knows, Artwork),
    hypothesis_definition(Hypothesis, Type, Value, _),
    artwork_attribute(Artwork, Type, Value, Facts).

suggested_hypothesis(Visitor, Hypothesis) :-
    hypothesis_evidence(Visitor, Hypothesis, _, _, _, _, _).

% A response contradicts a hypothesis only when that hypothesis made the
% opposite recorded-support prediction. Neither/unsure eliminate nothing.
contradicted_hypothesis(Visitor, Hypothesis, Observation,
                       r_response_contradicts_prediction) :-
    question_response(Observation, Visitor, Question, prefer_a),
    asked_question(Question, Visitor, ArtworkA, ArtworkB),
    hypothesis_prediction(Hypothesis, ArtworkA, ArtworkB, prefer_b, _).
contradicted_hypothesis(Visitor, Hypothesis, Observation,
                       r_response_contradicts_prediction) :-
    question_response(Observation, Visitor, Question, prefer_b),
    asked_question(Question, Visitor, ArtworkA, ArtworkB),
    hypothesis_prediction(Hypothesis, ArtworkA, ArtworkB, prefer_a, _).

active_hypothesis(Visitor, Hypothesis) :-
    suggested_hypothesis(Visitor, Hypothesis),
    \+ hypothesis_status(Visitor, Hypothesis, rejected),
    \+ contradicted_hypothesis(Visitor, Hypothesis, _, _).

active_hypothesis_ids(Visitor, Hypotheses) :-
    findall(Hypothesis, active_hypothesis(Visitor, Hypothesis), Raw),
    sort(Raw, Hypotheses).

% Layer C: the response model compares positive recorded support. A zero count
% means no support was found in this bounded snapshot, not that the attribute
% is proven absent from the depicted or physical artwork.
hypothesis_support(Hypothesis, Artwork, Facts) :-
    hypothesis_definition(Hypothesis, Type, Value, _),
    artwork_attribute(Artwork, Type, Value, Facts).

hypothesis_support_summary(Hypothesis, Artwork, Count, FactIDs) :-
    findall(Fact,
            ( hypothesis_support(Hypothesis, Artwork, Facts),
              member(Fact, Facts)
            ),
            RawFacts),
    sort(RawFacts, FactIDs),
    ( FactIDs = [] -> Count = 0 ; Count = 1 ).

hypothesis_prediction(Hypothesis, ArtworkA, ArtworkB, prefer_a, Record) :-
    hypothesis_support_summary(Hypothesis, ArtworkA, CountA, FactsA),
    hypothesis_support_summary(Hypothesis, ArtworkB, CountB, FactsB),
    CountA > CountB,
    Record = prediction{
        hypothesis_id:Hypothesis,
        predicted_response:prefer_a,
        support_a:CountA,
        support_b:CountB,
        option_a_fact_ids:FactsA,
        option_b_fact_ids:FactsB,
        rule_id:r_greater_recorded_support_predicts_preference,
        assumption_id:a_recorded_positive_support_comparison
    }.
hypothesis_prediction(Hypothesis, ArtworkA, ArtworkB, prefer_b, Record) :-
    hypothesis_support_summary(Hypothesis, ArtworkA, CountA, FactsA),
    hypothesis_support_summary(Hypothesis, ArtworkB, CountB, FactsB),
    CountB > CountA,
    Record = prediction{
        hypothesis_id:Hypothesis,
        predicted_response:prefer_b,
        support_a:CountA,
        support_b:CountB,
        option_a_fact_ids:FactsA,
        option_b_fact_ids:FactsB,
        rule_id:r_greater_recorded_support_predicts_preference,
        assumption_id:a_recorded_positive_support_comparison
    }.

hypothesis_prediction_record(Hypothesis, ArtworkA, ArtworkB, Record) :-
    hypothesis_prediction(Hypothesis, ArtworkA, ArtworkB, _, Record), !.
hypothesis_prediction_record(Hypothesis, ArtworkA, ArtworkB, Record) :-
    hypothesis_support_summary(Hypothesis, ArtworkA, CountA, FactsA),
    hypothesis_support_summary(Hypothesis, ArtworkB, CountB, FactsB),
    Record = prediction{
        hypothesis_id:Hypothesis,
        predicted_response:unknown,
        support_a:CountA,
        support_b:CountB,
        option_a_fact_ids:FactsA,
        option_b_fact_ids:FactsB,
        rule_id:r_equal_recorded_support_is_undecidable,
        assumption_id:a_recorded_positive_support_comparison
    }.

distinguishes_hypotheses(ArtworkA, ArtworkB, HypothesisA, HypothesisB,
                         PredictionA, PredictionB) :-
    HypothesisA @< HypothesisB,
    hypothesis_prediction(HypothesisA, ArtworkA, ArtworkB, ChoiceA, PredictionA),
    hypothesis_prediction(HypothesisB, ArtworkA, ArtworkB, ChoiceB, PredictionB),
    dif(ChoiceA, ChoiceB).

% Layer D: state filters are grounded in the finite caller-provided universe.
unavailable_artwork(Visitor, Artwork) :-
    visitor_observation(_, Visitor, Kind, Artwork),
    memberchk(Kind, [knows, likes, dislikes, viewed, rejected]).
unavailable_artwork(Visitor, Artwork) :-
    asked_question(_, Visitor, Artwork, _).
unavailable_artwork(Visitor, Artwork) :-
    asked_question(_, Visitor, _, Artwork).

eligible_option(Visitor, Artwork) :-
    allowed_artwork(Artwork),
    \+ unavailable_artwork(Visitor, Artwork).

question_statistics(Visitor, ArtworkA, ArtworkB, DistinctionCount,
                    PreferACount, PreferBCount, UnknownCount,
                    Distinctions, Predictions) :-
    selection_hypotheses(Visitor, Hypotheses),
    findall(Prediction,
            ( member(Hypothesis, Hypotheses),
              hypothesis_prediction_record(
                  Hypothesis, ArtworkA, ArtworkB, Prediction)
            ),
            Predictions),
    findall(Distinction,
            ( select(HypothesisA, Hypotheses, Tail),
              member(HypothesisB, Tail),
              distinguishes_hypotheses(
                  ArtworkA, ArtworkB, HypothesisA, HypothesisB,
                  PredictionA, PredictionB),
              Distinction = distinction{
                  hypothesis_a:HypothesisA,
                  hypothesis_b:HypothesisB,
                  rule_id:r_opposing_predictions_discriminate,
                  children:[PredictionA, PredictionB]
              }
            ),
            RawDistinctions),
    sort(RawDistinctions, Distinctions),
    length(Distinctions, DistinctionCount),
    include(prediction_is(prefer_a), Predictions, PreferA),
    include(prediction_is(prefer_b), Predictions, PreferB),
    include(prediction_is(unknown), Predictions, Unknown),
    length(PreferA, PreferACount),
    length(PreferB, PreferBCount),
    length(Unknown, UnknownCount).

selection_hypotheses(Visitor, Hypotheses) :-
    clarification_mode(Visitor, single_rule),
    active_hypothesis_ids(Visitor, [First, Second|_]),
    Hypotheses = [First, Second],
    !.
selection_hypotheses(Visitor, Hypotheses) :-
    active_hypothesis_ids(Visitor, Hypotheses).

prediction_is(Choice, Prediction) :-
    get_dict(predicted_response, Prediction, Choice).

eligible_question(Visitor, ArtworkA, ArtworkB, Score, Statistics) :-
    eligible_option(Visitor, ArtworkA),
    eligible_option(Visitor, ArtworkB),
    ArtworkA @< ArtworkB,
    question_statistics(
        Visitor, ArtworkA, ArtworkB, DistinctionCount,
        PreferACount, PreferBCount, UnknownCount,
        Distinctions, Predictions),
    DistinctionCount > 0,
    Imbalance is abs(PreferACount - PreferBCount),
    Score is DistinctionCount * 1000 - Imbalance * 10 - UnknownCount,
    Statistics = statistics{
        distinguished_hypothesis_pair_count:DistinctionCount,
        predicted_prefer_a_count:PreferACount,
        predicted_prefer_b_count:PreferBCount,
        unknown_prediction_count:UnknownCount,
        balance_penalty:Imbalance,
        distinctions:Distinctions,
        predictions:Predictions
    }.

selected_question(Visitor, ArtworkA, ArtworkB, Score, Statistics) :-
    setof(Key-question(A, B, CandidateScore, CandidateStats),
          ( eligible_question(Visitor, A, B, CandidateScore, CandidateStats),
            NegativeScore is -CandidateScore,
            Key = NegativeScore-(A-B)
          ),
          [_-question(ArtworkA, ArtworkB, Score, Statistics)|_]).

question_observation_ids(Visitor, Hypotheses, ObservationIDs) :-
    findall(Observation,
            ( member(Hypothesis, Hypotheses),
              hypothesis_evidence(
                  Visitor, Hypothesis, Observation, _, _, _, _)
            ),
            Raw),
    sort(Raw, ObservationIDs).

prediction_fact_ids(Predictions, FactIDs) :-
    findall(Fact,
            ( member(Prediction, Predictions),
              ( member(Fact, Prediction.option_a_fact_ids)
              ; member(Fact, Prediction.option_b_fact_ids)
              )
            ),
            Raw),
    sort(Raw, FactIDs).

question_dict(Visitor, ArtworkA, ArtworkB, Score, Statistics, Question) :-
    topic(ArtworkA, artwork, LabelA, _),
    topic(ArtworkB, artwork, LabelB, _),
    selection_hypotheses(Visitor, Hypotheses),
    question_observation_ids(Visitor, Hypotheses, ObservationIDs),
    prediction_fact_ids(Statistics.predictions, FactIDs),
    atomic_list_concat([q, ArtworkA, ArtworkB], '_', QuestionID),
    selection_rule_id(Visitor, SelectionRule),
    Proof = proof{
        predicate:selected_clarification_question,
        rule_id:SelectionRule,
        observation_ids:ObservationIDs,
        hypothesis_ids:Hypotheses,
        artgraph_fact_ids:FactIDs,
        assumption_ids:[a_recorded_positive_support_comparison],
        children:[
            proof_node{
                predicate:eligible_question,
                rule_id:r_finite_state_filtered_pair,
                option_a:ArtworkA,
                option_b:ArtworkB
            },
            proof_node{
                predicate:hypothesis_discrimination,
                rule_id:r_opposing_predictions_discriminate,
                children:Statistics.distinctions
            }
        ]
    },
    Question = question{
        question_id:QuestionID,
        kind:pairwise_artwork_preference,
        option_a:_{artwork_id:ArtworkA, label:LabelA},
        option_b:_{artwork_id:ArtworkB, label:LabelB},
        prompt_template:'Which of these two artworks interests you more?',
        deterministic_score:Score,
        statistics:Statistics,
        proof:Proof
    }.

selection_rule_id(Visitor, r_single_opposing_prediction_pair) :-
    clarification_mode(Visitor, single_rule), !.
selection_rule_id(_, r_select_max_discrimination_then_balance).

final_recommendations(Visitor, Recommendations) :-
    active_hypothesis_ids(Visitor, Hypotheses),
    findall(Key-Recommendation,
            ( allowed_artwork(Artwork),
              \+ unavailable_artwork(Visitor, Artwork),
              findall(support{hypothesis_id:Hypothesis, fact_ids:Facts},
                      ( member(Hypothesis, Hypotheses),
                        hypothesis_support(Hypothesis, Artwork, Facts)
                      ),
                      RawSupports),
              sort(RawSupports, Supports),
              Supports \= [],
              length(Supports, SupportCount),
              NegativeScore is -SupportCount,
              Key = NegativeScore-Artwork,
              topic(Artwork, artwork, Label, _),
              Recommendation = recommendation{
                  artwork_id:Artwork,
                  label:Label,
                  supported_hypothesis_count:SupportCount,
                  supports:Supports,
                  rule_id:r_recommend_from_remaining_hypotheses
              }
            ),
            RawRows),
    keysort(RawRows, SortedRows),
    pairs_values(SortedRows, AllRecommendations),
    prefix_length_at_most(AllRecommendations, 5, Recommendations).

write_clarification_json(Visitor) :-
    active_hypothesis_ids(Visitor, Hypotheses),
    final_recommendations(Visitor, Recommendations),
    ( selected_question(Visitor, ArtworkA, ArtworkB, Score, Statistics)
    -> question_dict(Visitor, ArtworkA, ArtworkB, Score, Statistics, Question),
       Result = _{
           status:selected,
           visitor:Visitor,
           active_hypothesis_ids:Hypotheses,
           question:Question,
           final_recommendations:Recommendations
       }
    ;  Result = _{
           status:no_discriminative_question,
           visitor:Visitor,
           active_hypothesis_ids:Hypotheses,
           question:_{},
           final_recommendations:Recommendations
       }
    ),
    json_write_dict(current_output, Result, [width(0)]),
    nl.

prefix_length_at_most(_, Limit, []) :- Limit =< 0, !.
prefix_length_at_most([], _, []) :- !.
prefix_length_at_most([Head|Tail], Limit, [Head|Prefix]) :-
    Next is Limit - 1,
    prefix_length_at_most(Tail, Next, Prefix).
