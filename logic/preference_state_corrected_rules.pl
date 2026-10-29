% Corrected Phase 1.2 policy v2. The included v1 predicates are historical;
% this entry point uses only c_* inference, with masked evidence and corrections.
:- ensure_loaded('preference_state_rules.pl').
:- dynamic observation_order/2, observation_components/2, superseded_observation/1.
:- dynamic hidden_fact/1, incomplete_evidence/0.

c_observation(O, V, K, A) :-
    preference_observation(O, V, K, A), \+ superseded_observation(O).

c_support(H, A, Fs) :-
    preference_artwork_support(H, A, Fs),
    \+ (member(F, Fs), hidden_fact(F)).

c_cooccurrence(V, H, K, A, O, Fs) :-
    c_observation(O, V, K, A), memberchk(K, [likes, dislikes]), c_support(H, A, Fs).

c_explicit_raw(V, atomic, [H], S, O) :-
    c_observation(O, V, K, H),
    (K = explicit_interest -> S = explicitly_confirmed ; memberchk(K,[explicit_rejection,reject_atomic_explanation]), S = explicitly_rejected).
c_explicit_raw(V, all_of, Cs, S, O) :-
    c_observation(O, V, K, preference_pair), observation_components(O, Cs),
    (K = explicit_conjunction -> S = explicitly_confirmed ; memberchk(K,[reject_conjunction,reject_pair_explanation]), S = explicitly_rejected).
c_explicit(V, K, Cs, S, O) :-
    c_explicit_raw(V, K, Cs, S, O), observation_order(O, N),
    \+ (c_explicit_raw(V, K, Cs, _, Later), observation_order(Later, M), M > N).

c_counts(V, H, P, N) :-
    findall(A, c_cooccurrence(V, H, likes, A, _, _), Ps), sort(Ps, PU), length(PU, P),
    findall(A, c_cooccurrence(V, H, dislikes, A, _, _), Ns), sort(Ns, NU), length(NU, N).

c_atomic_status(V, H, S) :- c_explicit(V, atomic, [H], S, _), !.
c_atomic_status(V, H, mixed) :- c_counts(V, H, P, N), P > 0, N > 0, !.
c_atomic_status(V, H, reinforced) :- c_counts(V, H, P, 0), P >= 2, !.
c_atomic_status(V, H, candidate) :- c_counts(V, H, P, 0), P > 0.

c_atomic_proof(V, H, Proof) :-
    findall(O, (c_cooccurrence(V,H,_,_,O,_);c_explicit_raw(V,atomic,[H],_,O)), Os), sort(Os, Obs),
    findall(F, (c_cooccurrence(V,H,_,_,_,Fs),member(F,Fs)), Raw), sort(Raw, Facts),
    c_counts(V,H,P,N),
    Proof = _{rule_id:r_explicit_authority_then_cooccurrence,
        assumption_ids:[a_observation_is_not_universal_attribute_judgment],
        observation_ids:Obs,artgraph_fact_ids:Facts,positive_artwork_count:P,negative_artwork_count:N}.

c_blocked_pair(V, Cs) :- member(H,Cs), c_explicit(V,atomic,[H],explicitly_rejected,O),
    c_observation(O,V,explicit_rejection,H).
c_blocked_pair(V, Cs) :- c_explicit(V,all_of,Cs,explicitly_rejected,_).
% Confirmed independent components do not justify inventing a conjunction.
c_independent_pair(V,[A,B]) :-
    c_explicit(V,atomic,[A],explicitly_confirmed,_),
    c_explicit(V,atomic,[B],explicitly_confirmed,_).

c_interaction(V, Cs, Proof) :-
    \+ incomplete_evidence,
    allowed_interaction(A,B), sort([A,B],Cs),
    \+ c_blocked_pair(V,Cs), \+ c_independent_pair(V,Cs),
    c_observation(OL,V,likes,L), c_support(A,L,FA), c_support(B,L,FB),
    c_observation(OA,V,dislikes,DA), c_support(A,DA,FDA), \+ c_support(B,DA,_),
    c_observation(OB,V,dislikes,DB), DA \= DB, c_support(B,DB,FDB), \+ c_support(A,DB,_),
    append([FA,FB,FDA,FDB],Fs), sort(Fs,Facts), sort([OL,OA,OB],Obs),
    Proof = _{rule_id:r_component_rejection_suggests_interaction,
        assumption_ids:[a_bounded_recorded_support_contrast,a_component_rejection_can_suggest_interaction],
        observation_ids:Obs, artgraph_fact_ids:Facts,
        not_recorded_components:[_{artwork_id:DA,hypothesis_id:B},_{artwork_id:DB,hypothesis_id:A}],
        limitation:observations_also_admit_incidental_or_independent_preferences}.

c_record(V, atomic, [H], S, Proof) :-
    hypothesis_definition(H,_,_,_), c_atomic_status(V,H,S), c_atomic_proof(V,H,Proof).
c_record(V, all_of, Cs, S, Proof) :-
    c_explicit(V,all_of,Cs,S,O),
    Proof=_{rule_id:r_latest_explicit_statement,assumption_ids:[],observation_ids:[O],artgraph_fact_ids:[]}.
c_record(V, all_of, Cs, interaction_candidate, Proof) :-
    c_interaction(V,Cs,Proof), \+ c_explicit(V,all_of,Cs,_,_).

c_status_priority(explicitly_confirmed,0).
c_status_priority(reinforced,1).
c_status_priority(interaction_candidate,2).
c_status_priority(candidate,3).
c_status_priority(mixed,4).
c_status_priority(explicitly_rejected,5).

c_explanations(V, compositional, Explanations) :-
    findall(Key-R,
        (c_record(V,K,Cs,S,P),c_status_priority(S,N),Key=N-K-Cs,
         R=_{kind:K,components:Cs,status:S,proof:P}),Raw),
    sort(Raw,Sorted), pairs_values(Sorted,All),
    c_unique_explanations(All,[],Explanations).
c_explanations(V, atomic, Explanations) :-
    findall(R,(hypothesis_definition(H,_,_,_),c_counts(V,H,P,_),P>0,
        c_atomic_proof(V,H,Proof),R=_{kind:atomic,components:[H],status:candidate,proof:Proof}),Raw),
    sort(Raw,Explanations).
c_unique_explanations([],_,[]).
c_unique_explanations([R|Rs],Seen,Out) :-
    Key=R.kind-R.components,
    (memberchk(Key,Seen) -> c_unique_explanations(Rs,Seen,Out)
    ; Out=[R|Tail],c_unique_explanations(Rs,[Key|Seen],Tail)).

c_positive(S) :- memberchk(S,[explicitly_confirmed,reinforced,candidate,interaction_candidate]).
c_unresolved(S) :- memberchk(S,[reinforced,candidate,interaction_candidate,mixed]).
c_matches(E,A,Fs) :-
    findall(H,c_support(H,A,_),Hs), subset(E.components,Hs),
    findall(F,(member(H,E.components),c_support(H,A,X),member(F,X)),Raw),sort(Raw,Fs).

% Common ordinal policy: explicit match > provisional matches; no probabilities.
% Explicit rejections are hard candidate constraints, even for inferred pairs.
c_eligible(V,A) :- allowed_action_artwork(A),
    \+ (c_observation(_,V,K,A),memberchk(K,[likes,dislikes])),
    \+ (c_explicit(V,K,Cs,explicitly_rejected,O),c_observation(O,V,RejectionKind,_),
        memberchk(RejectionKind,[explicit_rejection,reject_conjunction]),
        E=_{kind:K,components:Cs},c_matches(E,A,_)).
c_ranking(V,Es,Actions) :-
    findall(Key-Action,(c_eligible(V,A),
        findall(E,(member(E,Es),c_positive(E.status),c_matches(E,A,_)),Matches),
        include(c_confirmed,Matches,Confirmed),length(Confirmed,C),length(Matches,T),
        findall(F,(member(E,Matches),c_matches(E,A,Fs),member(F,Fs)),Raw),sort(Raw,Facts),
        NC is -C, NT is -T, Key=NC-NT-A, topic(A,artwork,Label,_),
        Action=_{artwork_id:A,label:Label,ordinal_score:[C,T],supports:Matches,
            proof:_{rule_id:r_explicit_then_supported_explanations,artgraph_fact_ids:Facts}}),Rows),
    keysort(Rows,Sorted),pairs_values(Sorted,Actions).
c_confirmed(E) :- E.status == explicitly_confirmed.
c_reinforced(E) :- E.status == reinforced.
c_pending(E) :- c_unresolved(E.status).

c_primary(Es,Primary) :- include(c_confirmed,Es,[Primary|_]),!.
c_primary(_,null) :- incomplete_evidence,!.
c_primary(Es,Primary) :- include(c_reinforced,Es,[Primary]),
    \+ (member(E,Es),memberchk(E.status,[mixed,interaction_candidate])),!.
c_primary(_,null).

c_question(Es,Question) :-
    findall(Key-E,(member(E,Es),c_pending(E),
        (E.kind==all_of -> P=0 ; P=1),Key=P-E.kind-E.components),Rows),
    keysort(Rows,[_-E|_]),
    Question=_{kind:confirm_explanation,explanation:_{kind:E.kind,components:E.components},
        responses:[yes,no,unsure],
        semantics:yes_confirms_this_interest_no_rejects_only_this_explanation}.

c_decision(Es,Actions,Primary,Decision) :-
    c_primary(Es,Primary),
    (Primary \== null, Actions=[A|_], c_matches(Primary,A.artwork_id,_) ->
        Decision=_{action_type:recommend,artwork_id:A.artwork_id,question:null,reason:authoritative_or_unique_reinforced_interest}
    ; incomplete_evidence ->
        Decision=_{action_type:insufficient_evidence,artwork_id:null,question:null,reason:declared_incomplete_evidence}
    ; c_question(Es,Q) ->
        Decision=_{action_type:clarify,artwork_id:null,question:Q,reason:unresolved_explanations}
    ; Decision=_{action_type:insufficient_evidence,artwork_id:null,question:null,reason:no_supported_eligible_action}).

write_corrected_preference_state_json(V) :-
    preference_state_mode(V,Mode),c_explanations(V,Mode,Es),c_ranking(V,Es,Actions),
    c_decision(Es,Actions,Primary,Decision),include(c_pending,Es,Pending),length(Pending,N),
    findall(O,c_observation(O,V,_,_),Active),findall(O,superseded_observation(O),Superseded),
    findall(_{observation_id:O,kind:K,artwork_id:A,hypothesis_id:H,artgraph_fact_ids:Fs},
        c_cooccurrence(V,H,K,A,O,Fs),Evidence),
    Result=_{status:ok,policy_version:corrected_v2,visitor:V,mode:Mode,
        preference_explanations:Es,primary_explanation:Primary,ranked_actions:Actions,
        decision:Decision,unresolved_explanation_count:N,
        active_observation_ids:Active,superseded_observation_ids:Superseded,
        observation_evidence:Evidence},
    json_write_dict(current_output,Result,[width(0)]),nl.
