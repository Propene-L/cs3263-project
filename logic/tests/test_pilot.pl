:- begin_tests(phase0_pilot).

:- ensure_loaded('../generated_facts.pl').
:- ensure_loaded('../pilot_rules.pl').

test(real_artist_context_with_provenance, [nondet]) :-
    artwork_context(ag_8142, ag_850, artist_context,
                    r_context_artist, [Fact]),
    source_fact(Fact, created_by, ag_8142, ag_850,
                'https://www.gennarovessio.com/artgraph-schema#createdBy'),
    fact_snapshot(Fact, artgraph_v1_seed_8142).

test(real_style_context_with_unification, [nondet]) :-
    artwork_context(ag_8142, Topic, style_context,
                    r_context_style, [Fact]),
    assertion(Topic == ag_46),
    source_fact(Fact, has_style, ag_8142, Topic,
                'https://www.gennarovessio.com/artgraph-schema#hasStyle').

test(real_context_solution_count) :-
    findall(Topic-Kind,
            artwork_context(ag_8142, Topic, Kind, _Rule, _Facts),
            Rows),
    assertion(Rows == [ag_850-artist_context,
                       ag_46-style_context,
                       ag_12-genre_context,
                       ag_2551-medium_context,
                       ag_2552-medium_context]).

:- end_tests(phase0_pilot).

