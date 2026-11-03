"""Independent Python representation-equivalence comparator, authorized for v2.

This module is never called by the symbolic engine. It also supplies the shared
downstream scoring contract for non-symbolic baselines and evaluation oracles.
"""
from __future__ import annotations

from copy import deepcopy
from itertools import combinations
from typing import Any

from .preference_state import PreferenceState, validate_state
from .preference_state_baselines import PreferenceEvidenceIndex

POSITIVE = {"explicitly_confirmed", "reinforced", "candidate", "interaction_candidate", "model_inferred"}
PENDING = {"reinforced", "candidate", "interaction_candidate", "mixed"}
PRIORITY = {s: i for i, s in enumerate([
    "explicitly_confirmed", "reinforced", "interaction_candidate", "candidate", "mixed", "explicitly_rejected"
])}


def explanation_key(e: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    return e["kind"], tuple(sorted(e["components"]))


def visible_evidence(evidence: dict, state: PreferenceState) -> dict:
    result = deepcopy(evidence)
    hidden = set(state.hidden_fact_ids)
    for artwork in result["artworks"].values():
        artwork["attributes"] = [a for a in artwork["attributes"] if not hidden.intersection(a["fact_ids"])]
    return result


def active_observations(state: PreferenceState) -> list:
    superseded = {o.supersedes for o in state.observations if o.supersedes}
    return [o for o in state.observations if o.id not in superseded]


def explicit_records(state: PreferenceState) -> dict:
    records = {}
    for o in active_observations(state):
        if o.kind in {"explicit_interest", "explicit_rejection", "explicit_conjunction", "reject_conjunction", "reject_atomic_explanation", "reject_pair_explanation"}:
            kind = "all_of" if o.components else "atomic"
            cs = tuple(sorted(o.components)) if o.components else (o.object_id,)
            status = "explicitly_rejected" if o.kind in {"explicit_rejection", "reject_conjunction", "reject_atomic_explanation", "reject_pair_explanation"} else "explicitly_confirmed"
            records[(kind, cs)] = (status, o.id)
    return records


def common_ranking(state: PreferenceState, explanations: list[dict], index: PreferenceEvidenceIndex) -> list[dict]:
    observed = {o.object_id for o in active_observations(state) if o.kind in {"likes", "dislikes"}}
    kinds = {o.id:o.kind for o in active_observations(state)}
    rejected = [set(cs) for (_, cs), (status, oid) in explicit_records(state).items()
                if status == "explicitly_rejected" and kinds[oid] in {"explicit_rejection","reject_conjunction"}]
    actions = []
    for a in sorted(set(state.allowed_action_artwork_ids) - observed):
        supported = index.supports[a]
        if any(cs <= supported for cs in rejected):
            continue
        matches = [e for e in explanations if e["status"] in POSITIVE and set(e["components"]) <= supported]
        confirmed = sum(e["status"] == "explicitly_confirmed" for e in matches)
        facts = sorted({f for e in matches for h in e["components"] for f in index.fact_ids.get((a, h), [])})
        actions.append({"artwork_id": a, "label": index.evidence["artworks"][a]["label"],
                        "ordinal_score": [confirmed, len(matches)], "supports": matches,
                        "proof": {"rule_id": "python_explicit_then_supported_explanations", "artgraph_fact_ids": facts}})
    return sorted(actions, key=lambda a: (-a["ordinal_score"][0], -a["ordinal_score"][1], a["artwork_id"]))


def common_decision(state: PreferenceState, explanations: list[dict], actions: list[dict], index: PreferenceEvidenceIndex) -> tuple:
    confirmed = [e for e in explanations if e["status"] == "explicitly_confirmed"]
    reinforced = [e for e in explanations if e["status"] == "reinforced"]
    primary = confirmed[0] if confirmed else None
    if primary is None and not (state.evidence_incomplete or state.hidden_fact_ids) and len(reinforced) == 1 and not any(e["status"] in {"mixed", "interaction_candidate"} for e in explanations):
        primary = reinforced[0]
    if primary and actions and set(primary["components"]) <= index.supports[actions[0]["artwork_id"]]:
        decision = {"action_type": "recommend", "artwork_id": actions[0]["artwork_id"], "question": None,
                    "reason": "authoritative_or_unique_reinforced_interest"}
    elif state.evidence_incomplete or state.hidden_fact_ids:
        decision = {"action_type": "insufficient_evidence", "artwork_id": None, "question": None, "reason": "declared_incomplete_evidence"}
    else:
        pending = sorted([e for e in explanations if e["status"] in PENDING],
                         key=lambda e: (0 if e["kind"] == "all_of" else 1, *explanation_key(e)))
        if pending:
            e = pending[0]
            decision = {"action_type": "clarify", "artwork_id": None, "reason": "unresolved_explanations",
                        "question": {"kind": "confirm_explanation", "explanation": {"kind": e["kind"], "components": e["components"]},
                                     "responses": ["yes", "no", "unsure"],
                                     "semantics": "yes_confirms_this_interest_no_rejects_only_this_explanation"}}
        else:
            decision = {"action_type": "insufficient_evidence", "artwork_id": None, "question": None, "reason": "no_supported_eligible_action"}
    return primary, decision


def finish_result(state: PreferenceState, explanations: list[dict], index: PreferenceEvidenceIndex) -> dict:
    actions = common_ranking(state, explanations, index)
    primary, decision = common_decision(state, explanations, actions, index)
    return {"status": "ok", "preference_explanations": explanations, "primary_explanation": primary,
            "ranked_actions": actions, "decision": decision,
            "unresolved_explanation_count": sum(e["status"] in PENDING for e in explanations),
            "active_observation_ids": [o.id for o in active_observations(state)],
            "superseded_observation_ids": [o.supersedes for o in state.observations if o.supersedes]}


class InteractionPythonBaseline:
    """Direct Python implementation of the documented corrected formal policy."""
    def __init__(self, evidence: dict) -> None:
        self.evidence = evidence

    def infer(self, state: PreferenceState) -> dict:
        validate_state(state, self.evidence)
        index = PreferenceEvidenceIndex(visible_evidence(self.evidence, state))
        active = active_observations(state)
        explicit = explicit_records(state)
        explanations: dict[tuple, dict] = {}
        for h in sorted(index.hypothesis_rows):
            pos = [o for o in active if o.kind == "likes" and h in index.supports[o.object_id]]
            neg = [o for o in active if o.kind == "dislikes" and h in index.supports[o.object_id]]
            p, n = len({o.object_id for o in pos}), len({o.object_id for o in neg})
            key = ("atomic", (h,))
            if key in explicit:
                status = explicit[key][0]
            elif p and n:
                status = "mixed"
            elif p >= 2:
                status = "reinforced"
            elif p:
                status = "candidate"
            else:
                continue
            obs = sorted({o.id for o in pos + neg} | {o.id for o in active if o.object_id == h})
            facts = sorted({f for o in pos + neg for f in index.fact_ids[(o.object_id, h)]})
            explanations[key] = {"kind": "atomic", "components": [h], "status": status,
                "proof": {"rule_id": "python_explicit_authority_then_cooccurrence", "observation_ids": obs,
                          "artgraph_fact_ids": facts, "positive_artwork_count": p, "negative_artwork_count": n,
                          "assumption_ids": ["a_observation_is_not_universal_attribute_judgment"]}}
        if not state.evidence_incomplete and not state.hidden_fact_ids:
            for a, b in combinations(sorted(index.hypothesis_rows), 2):
                types = {index.hypothesis_rows[h]["attribute_type"] for h in (a, b)}
                if types not in ({"tag", "style"}, {"tag", "genre"}, {"style", "genre"}):
                    continue
                cs = (a, b)
                hard_rejections={o.id for o in active if o.kind=="explicit_rejection"}
                if any(explicit.get(("atomic", (h,)), (None,None))[1] in hard_rejections for h in cs):
                    continue
                if all(explicit.get(("atomic", (h,)), (None,))[0] == "explicitly_confirmed" for h in cs):
                    continue
                if ("all_of", cs) in explicit:
                    continue
                liked = [o for o in active if o.kind == "likes" and set(cs) <= index.supports[o.object_id]]
                da = [o for o in active if o.kind == "dislikes" and a in index.supports[o.object_id] and b not in index.supports[o.object_id]]
                db = [o for o in active if o.kind == "dislikes" and b in index.supports[o.object_id] and a not in index.supports[o.object_id]]
                if not liked or not da or not db:
                    continue
                l, x, y = liked[0], da[0], db[0]
                facts = sorted({f for o,h in [(l,a),(l,b),(x,a),(y,b)] for f in index.fact_ids[(o.object_id,h)]})
                explanations[("all_of", cs)] = {"kind": "all_of", "components": list(cs), "status": "interaction_candidate",
                    "proof": {"rule_id": "python_component_rejection_suggests_interaction",
                              "observation_ids": sorted([l.id,x.id,y.id]),"artgraph_fact_ids": facts,
                              "assumption_ids": ["a_bounded_recorded_support_contrast","a_component_rejection_can_suggest_interaction"],
                              "not_recorded_components": [{"artwork_id":x.object_id,"hypothesis_id":b},{"artwork_id":y.object_id,"hypothesis_id":a}]}}
        for (kind, cs), (status, obs) in explicit.items():
            if kind == "all_of":
                explanations[(kind,cs)] = {"kind":kind,"components":list(cs),"status":status,
                    "proof":{"rule_id":"python_latest_explicit_statement","observation_ids":[obs],"artgraph_fact_ids":[],"assumption_ids":[]}}
        ordered = sorted(explanations.values(), key=lambda e: (PRIORITY[e["status"]], *explanation_key(e)))
        return finish_result(state, ordered, index)
