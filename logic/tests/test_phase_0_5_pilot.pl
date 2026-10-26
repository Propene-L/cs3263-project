:- begin_tests(phase0_5_pilot).

:- ensure_loaded('../phase_0_5_generated_facts.pl').
:- ensure_loaded('../phase_0_5_pilot_rules.pl').

test(real_artwork_artist_movement_chain, [nondet]) :-
    artwork_movement(ag_72463, ag_124741, r_artwork_movement,
                     [CreatedByFact, MovementFact]),
    source_fact(CreatedByFact, created_by, ag_72463, ag_1210,
                'https://www.gennarovessio.com/artgraph-schema#createdBy'),
    source_fact(MovementFact, belongs_to_movement, ag_1210, ag_124741,
                'https://www.gennarovessio.com/artgraph-schema#belongsToMovement').

test(real_shared_style_composition, [nondet]) :-
    contextual_peer(ag_72463, ag_72464, style(ag_41),
                    r_peer_via_style, [Fact1, Fact2]),
    source_fact(Fact1, has_style, ag_72463, ag_41, _),
    source_fact(Fact2, has_style, ag_72464, ag_41, _).

test(real_shared_series_composition, [nondet]) :-
    contextual_peer(ag_72464, ag_72465, series(ag_132972),
                    r_peer_via_series, [Fact1, Fact2]),
    source_fact(Fact1, part_of_series, ag_72464, ag_132972, _),
    source_fact(Fact2, part_of_series, ag_72465, ag_132972, _).

test(real_artwork_artist_school_chain, [nondet]) :-
    factual_context_topic(ag_72463, ag_124822, training,
                          r_context_school_via_artist,
                          [CreatedByFact, SchoolFact]),
    source_fact(CreatedByFact, created_by, ag_72463, ag_1210, _),
    source_fact(SchoolFact, related_to_school, ag_1210, ag_124822, _).

test(tabled_recursive_context_reachability, [nondet]) :-
    context_reachable(ag_72463, ag_124741).

:- end_tests(phase0_5_pilot).

