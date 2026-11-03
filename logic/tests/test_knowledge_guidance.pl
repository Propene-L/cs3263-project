:- dynamic topic/1, topic_order/2, prerequisite/2, goal_topic/1.
:- dynamic knowledge_status/2, asked_topic/1, presented_topic/1, skipped_topic/1, force_explain/0.

:- consult('../knowledge_guidance_rules.pl').

topic(c_style).
topic(c_expressionism).
topic(c_expressionist_portrait).
topic_order(c_style, 0).
topic_order(c_expressionism, 1).
topic_order(c_expressionist_portrait, 2).
prerequisite(c_expressionism, c_style).
prerequisite(c_expressionist_portrait, c_expressionism).
goal_topic(c_expressionist_portrait).

:- begin_tests(knowledge_guidance).

test(recursive_prerequisite_proof) :-
    knowledge_action(Action),
    assertion(Action.action_type == ask_knowledge),
    assertion(Action.topic_id == c_style),
    assertion(Action.rule_id == r_ask_unknown_topic),
    assertion(Action.proof.path == [c_expressionist_portrait,c_expressionism,c_style]).

test(explicit_not_known_changes_action,
     [setup(assertz(user:knowledge_status(c_style, not_known))),
      cleanup(retractall(user:knowledge_status(c_style, _)))]) :-
    knowledge_action(Action),
    assertion(Action.action_type == explain),
    assertion(Action.topic_id == c_style),
    assertion(Action.rule_id == r_explain_stated_not_known).

test(known_prerequisite_advances,
     [setup(assertz(user:knowledge_status(c_style, known))),
      cleanup(retractall(user:knowledge_status(c_style, _)))]) :-
    knowledge_action(Action),
    assertion(Action.action_type == ask_knowledge),
    assertion(Action.topic_id == c_expressionism).

:- end_tests(knowledge_guidance).
