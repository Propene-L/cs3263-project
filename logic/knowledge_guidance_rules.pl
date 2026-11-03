:- use_module(library(http/json)).
:- use_module(library(pairs)).

/*
  Phase 2 educational guidance policy.

  topic/1, topic_order/2, prerequisite/2, goal_topic/1, knowledge_status/2,
  asked_topic/1, presented_topic/1, skipped_topic/1 and force_explain/0 are
  generated from validated, allowlisted Python state for each fresh process.
  Prerequisite edges are documented guidance assumptions, not ArtGraph facts.
*/

reachable_topic(Goal, Topic, Depth, Path) :-
    reachable_topic_(Goal, Topic, [Goal], Depth, Path).

reachable_topic_(Topic, Topic, _, 0, [Topic]).
reachable_topic_(Current, Topic, Seen, Depth, [Current|Path]) :-
    prerequisite(Current, Next),
    \+ memberchk(Next, Seen),
    reachable_topic_(Next, Topic, [Next|Seen], PriorDepth, Path),
    Depth is PriorDepth + 1.

recorded_status(Topic, Status) :-
    ( knowledge_status(Topic, Recorded) -> Status = Recorded ; Status = unknown ).

addressed_topic(Topic) :- presented_topic(Topic).
addressed_topic(Topic) :- skipped_topic(Topic).
addressed_topic(Topic) :- recorded_status(Topic, known).

actionable_topic(Goal, Topic, Depth, Path) :-
    reachable_topic(Goal, Topic, Depth, Path),
    \+ addressed_topic(Topic).

ordered_actionable_topics(Goal, Ordered) :-
    findall(Key-_{topic:Topic,path:Path,depth:Depth},
            ( actionable_topic(Goal, Topic, Depth, Path),
              topic_order(Topic, Order),
              NegativeDepth is -Depth,
              Key = key(NegativeDepth, Order)
            ),
            Rows),
    keysort(Rows, Sorted),
    pairs_values(Sorted, Ordered).

topic_action(Topic, Path, _{
    action_type:confirm_knowledge,
    topic_id:Topic,
    rule_id:r_confirm_conflicted_knowledge,
    proof:_{rule_id:r_confirm_conflicted_knowledge,path:Path,status:conflicted}
}) :- recorded_status(Topic, conflicted), !.
topic_action(Topic, Path, _{
    action_type:explain,
    topic_id:Topic,
    rule_id:r_explain_stated_not_known,
    proof:_{rule_id:r_explain_stated_not_known,path:Path,status:not_known}
}) :- recorded_status(Topic, not_known), !.
topic_action(Topic, Path, _{
    action_type:explain,
    topic_id:Topic,
    rule_id:r_explain_after_knowledge_check,
    proof:_{rule_id:r_explain_after_knowledge_check,path:Path,status:unknown}
}) :- recorded_status(Topic, unknown), asked_topic(Topic), !.
topic_action(Topic, Path, _{
    action_type:ask_knowledge,
    topic_id:Topic,
    rule_id:r_ask_unknown_topic,
    proof:_{rule_id:r_ask_unknown_topic,path:Path,status:unknown}
}).

knowledge_action(Action) :-
    goal_topic(Goal),
    ( force_explain ->
        Action = _{action_type:explain,topic_id:Goal,
                   rule_id:r_explicit_explanation_request,
                   proof:_{rule_id:r_explicit_explanation_request,path:[Goal],status:requested}}
    ; ordered_actionable_topics(Goal, [First|_]) ->
        topic_action(First.topic, First.path, Action)
    ; Action = _{action_type:finish_topic,topic_id:Goal,
                 rule_id:r_all_guidance_topics_addressed,
                 proof:_{rule_id:r_all_guidance_topics_addressed,path:[Goal],status:complete}}
    ).

write_knowledge_action_json :-
    knowledge_action(Action),
    json_write_dict(current_output, _{status:ok,decision:Action}),
    nl.
