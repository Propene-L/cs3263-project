% Phase 0 pilot clauses. These are factual context deductions, not prerequisites.

artwork_context(Artwork, Artist, artist_context, r_context_artist,
                [CreatedByFact]) :-
    created_by(Artwork, Artist, CreatedByFact).

artwork_context(Artwork, Style, style_context, r_context_style,
                [StyleFact]) :-
    has_style(Artwork, Style, StyleFact).

artwork_context(Artwork, Genre, genre_context, r_context_genre,
                [GenreFact]) :-
    has_genre(Artwork, Genre, GenreFact).

artwork_context(Artwork, Medium, medium_context, r_context_medium,
                [MediumFact]) :-
    made_of(Artwork, Medium, MediumFact).

% A two-join pilot rule; applicable only when an imported artist-movement fact exists.
artwork_context(Artwork, Movement, movement_via_artist,
                r_context_movement_via_artist,
                [CreatedByFact, MovementFact]) :-
    created_by(Artwork, Artist, CreatedByFact),
    belongs_to_movement(Artist, Movement, MovementFact).

