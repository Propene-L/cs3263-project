:- dynamic visitor_observation/4.
:- dynamic allowed_artwork/1.
:- dynamic asked_question/4.
:- dynamic question_response/4.
:- dynamic hypothesis_status/3.
:- dynamic clarification_mode/2.
:- discontiguous visitor_observation/4.
:- discontiguous asked_question/4.
:- discontiguous question_response/4.
:- discontiguous clarification_mode/2.

allowed_artwork(Artwork) :- topic(Artwork, artwork, _, _).

clarification_mode(v_pair, compositional).
visitor_observation(obs_pair_music, v_pair, explicit_interest, h_musical_subject).
visitor_observation(obs_pair_expression, v_pair, explicit_interest, h_expressionist_style).

clarification_mode(v_response, compositional).
visitor_observation(obs_response_music, v_response, explicit_interest, h_musical_subject).
visitor_observation(obs_response_expression, v_response, explicit_interest, h_expressionist_style).
asked_question(q_response, v_response, ag_8966, ag_8388).
question_response(obs_response_choice, v_response, q_response, prefer_a).

clarification_mode(v_unsure, compositional).
visitor_observation(obs_unsure_music, v_unsure, explicit_interest, h_musical_subject).
visitor_observation(obs_unsure_expression, v_unsure, explicit_interest, h_expressionist_style).
asked_question(q_unsure, v_unsure, ag_8966, ag_8388).
question_response(obs_unsure_choice, v_unsure, q_unsure, unsure).

clarification_mode(v_single, compositional).
visitor_observation(obs_single_music, v_single, explicit_interest, h_musical_subject).

clarification_mode(v_like, compositional).
visitor_observation(obs_like_cello, v_like, likes, ag_10472).
