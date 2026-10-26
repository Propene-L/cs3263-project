% Phase 0.5 feasibility rules over the selected real ArtGraph subgraph.
% These are museum factual/context deductions, not production recommendations.

:- discontiguous contextual_peer/5.

artwork_artist(Artwork, Artist, [Fact]) :-
    created_by(Artwork, Artist, Fact).

artist_movement(Artist, Movement, [Fact]) :-
    belongs_to_movement(Artist, Movement, Fact).

artwork_movement(Artwork, Movement, r_artwork_movement,
                 [CreatedByFact, MovementFact]) :-
    artwork_artist(Artwork, Artist, [CreatedByFact]),
    artist_movement(Artist, Movement, [MovementFact]).

artwork_style(Artwork, Style, [Fact]) :-
    has_style(Artwork, Style, Fact).

shared_style_pair(Artwork1, Artwork2, Style, [Fact1, Fact2]) :-
    artwork_style(Artwork1, Style, [Fact1]),
    artwork_style(Artwork2, Style, [Fact2]),
    dif(Artwork1, Artwork2).

contextual_peer(Artwork1, Artwork2, style(Style), r_peer_via_style, Proof) :-
    shared_style_pair(Artwork1, Artwork2, Style, Proof).

artwork_series(Artwork, Series, [Fact]) :-
    part_of_series(Artwork, Series, Fact).

shared_series_pair(Artwork1, Artwork2, Series, [Fact1, Fact2]) :-
    artwork_series(Artwork1, Series, [Fact1]),
    artwork_series(Artwork2, Series, [Fact2]),
    dif(Artwork1, Artwork2).

contextual_peer(Artwork1, Artwork2, series(Series), r_peer_via_series, Proof) :-
    shared_series_pair(Artwork1, Artwork2, Series, Proof).

artist_school(Artist, School, [Fact]) :-
    related_to_school(Artist, School, Fact).

artwork_school(Artwork, School, [CreatedByFact, SchoolFact]) :-
    artwork_artist(Artwork, Artist, [CreatedByFact]),
    artist_school(Artist, School, [SchoolFact]).

factual_context_topic(Artwork, School, training,
                      r_context_school_via_artist, Proof) :-
    artwork_school(Artwork, School, Proof).

% Recursive contextual reachability is semantically graph reachability over
% imported museum associations. Tabling guarantees termination on this finite
% sample. It is not a learning-prerequisite or recommendation relation.
base_context_edge(Artwork, Artist) :- created_by(Artwork, Artist, _).
base_context_edge(Artist, Movement) :- belongs_to_movement(Artist, Movement, _).
base_context_edge(Artwork, Style) :- has_style(Artwork, Style, _).
base_context_edge(Artwork, Genre) :- has_genre(Artwork, Genre, _).
base_context_edge(Artwork, Medium) :- made_of(Artwork, Medium, _).
base_context_edge(Artwork, Period) :- has_period(Artwork, Period, _).
base_context_edge(Artwork, Series) :- part_of_series(Artwork, Series, _).
base_context_edge(Artist, Subject) :- has_subject(Artist, Subject, _).
base_context_edge(Artist, School) :- related_to_school(Artist, School, _).

context_edge(X, Y) :- base_context_edge(X, Y).
context_edge(X, Y) :- base_context_edge(Y, X).

:- table context_reachable/2.
context_reachable(X, Y) :-
    context_edge(X, Y).
context_reachable(X, Z) :-
    context_edge(X, Y),
    context_reachable(Y, Z),
    dif(X, Z).

