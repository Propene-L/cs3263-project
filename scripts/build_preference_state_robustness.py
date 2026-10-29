"""Freeze 32 authored controls; labels are specified before running any method.

No symbolic engine or interaction detector is imported. This builder validates
real IDs, attaches existing provenance, and derives only controlled gold relevance.
"""
from __future__ import annotations
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = 32631202


def atom(h): return {"kind": "atomic", "components": ["h_" + h]}
def pair(a,b): return {"kind": "all_of", "components": sorted(["h_"+a,"h_"+b])}
def obs(kind, value, *, supersedes=None):
    row = {"kind":kind,"object_id":value}
    if supersedes: row["supersedes"] = supersedes
    return row
def like(a): return obs("likes", "ag_"+str(a))
def dislike(a): return obs("dislikes", "ag_"+str(a))
def confirm(h): return obs("explicit_interest", "h_"+h)
def reject(h): return obs("explicit_rejection", "h_"+h)
def confirm_pair(a,b):
    return {"kind":"explicit_conjunction","object_id":"preference_pair","components":sorted(["h_"+a,"h_"+b])}


def authored_cases():
    """Fixed case cards. Paired ambiguous worlds share one statistical unit."""
    cases=[]
    def add(name, category, group, observations, profiles, expected, note, mask=None):
        cases.append(dict(scenario_id=name,category=category,group_id=group,observations=observations,
            latent_profiles=profiles,expected_action_type=expected,author_note=note,mask=mask or []))
    for slug,group,hs,likes,d in [
        ("music","music_dev","musical_subject",[14531,16386,12372],13231),
        ("feline","feline_test","feline_subject",[12564,17716,11706],13231),
        ("nature","nature_dev","nature_subject",[15247,16916,11912],8296),
        ("water","water_test","water_subject",[14588,33200,17083],8296),
    ]:
        add("atomic_"+slug,"true_atomic",group,[*(like(a) for a in likes),dislike(d)],[[atom(hs)]],"recommend",
            "Three preferred examples include incidental oil; one unrelated negative. One atomic interest is specified independently.")
    add("independent_music_portrait","multiple_independent","music_dev",
        [like(10472),confirm("musical_subject"),confirm("portrait_genre")],
        [[atom("musical_subject"),atom("portrait_genre")]],"recommend","Two separately confirmed interests; no conjunction is implied.")
    add("independent_feline_impressionist","multiple_independent","feline_test",
        [like(12564),like(10632)],[[atom("feline_subject"),atom("impressionist_style")]],"clarify",
        "Two likes with distinct features do not identify a unique explanation; ask before asserting the hidden independent interests.")
    add("independent_nature_water","multiple_independent","nature_dev",
        [confirm("nature_subject"),confirm("water_subject"),dislike(12343)],
        [[atom("nature_subject"),atom("water_subject")]],"recommend","Independent subject interests survive one disliked water artwork.")
    add("independent_style_portrait","multiple_independent","expression_dev",
        [like(8416),dislike(13231),dislike(8296),confirm("expressionist_style"),confirm("portrait_genre")],
        [[atom("expressionist_style"),atom("portrait_genre")]],"recommend","Explicit independent interests contradict an automatic conjunction interpretation.")
    for name,group,a,b in [
        ("style_portrait","expression_dev","expressionist_style","portrait_genre"),
        ("music_impressionist","impression_test","musical_subject","impressionist_style"),
        ("feline_style","feline_test","feline_subject","expressionist_style"),
        ("cubist_portrait","cubist_dev","cubist_style","portrait_genre"),
    ]:
        add("conjunction_"+name,"true_conjunction",group,[confirm_pair(a,b)],[[pair(a,b)]],"recommend",
            "The visitor explicitly states a conditional interest; no component-rejection trigger is used.")
    for slug,group,h,ls,d in [
        ("music","music_dev","musical_subject",[14531,16386,12372],13351),
        ("feline","feline_test","feline_subject",[12564,17716,11706],21076),
        ("nature","nature_dev","nature_subject",[15247,16916,11912],20164),
        ("water","water_test","water_subject",[14588,33200,17083],34659),
    ]:
        add("noisy_"+slug,"noisy",group,[*(like(a) for a in ls),dislike(d)],[[atom(h)]],"clarify",
            "One deliberately flipped preference response; mixed evidence should be retained and clarified.")
    for slug,group,h,d in [
        ("music","music_dev","musical_subject",10472),
        ("feline","feline_test","feline_subject",11706),
        ("nature","nature_dev","nature_subject",11014),
        ("water","water_test","water_subject",12343),
    ]:
        add("contradictory_"+slug,"contradictory",group,[confirm(h),dislike(d)],[[atom(h)]],"recommend",
            "An explicit interest is authoritative; disliking one example is not a universal attribute rejection.")
    for name,group,observations,profile,mask in [
        ("portrait_hidden","expression_dev",[like(8416),dislike(42361),dislike(8296)],pair("expressionist_style","portrait_genre"),[(42361,"portrait_genre")]),
        ("music_hidden","music_dev",[like(10472),dislike(10766)],atom("musical_subject"),[(10766,"musical_subject")]),
        ("feline_hidden","feline_test",[like(30919),dislike(23692)],atom("feline_subject"),[(23692,"feline_subject")]),
        ("water_hidden","water_test",[like(12343),dislike(25837)],atom("water_subject"),[(25837,"water_subject")]),
    ]:
        add("missing_"+name,"missing_evidence",group,observations,[[profile]],"insufficient_evidence",
            "Test-only deletion of a real supporting attribute makes contrast unreliable. Full snapshot supplies evaluator-only relevance.",mask)
    add("ambiguous_albert","ambiguous","expression_dev",[like(8416),dislike(13231),dislike(8296)],
        [[pair("expressionist_style","portrait_genre")],[atom("oil_medium")]],"clarify",
        "Identical observations fit either the conjunction or oil interest on recorded support. Evaluate both worlds equally.")
    add("ambiguous_cellist","ambiguous","music_dev",[like(10472)],
        [[atom("musical_subject")],[atom("portrait_genre")]],"clarify","One co-occurrence cannot identify its cause; two indistinguishable worlds.")
    add("ambiguous_sleeping_cat","ambiguous","feline_test",[like(30919)],
        [[atom("feline_subject")],[atom("impressionist_style")]],"clarify","Same history fits either subject or style; no label is passed to inference.")
    add("ambiguous_water","ambiguous","water_test",[like(24720)],
        [[atom("water_subject")],[atom("impressionist_style")]],"clarify","Same history fits either subject or style; one scenario with two worlds.")
    correction = reject("portrait_genre"); correction["supersedes"]="o1"
    add("correction_music","explicit_correction","music_dev",[confirm("portrait_genre"),correction,confirm("musical_subject")],
        [[atom("musical_subject")]],"recommend","Visitor retracts portrait statement and names musical subjects instead.")
    correction = confirm("feline_subject"); correction["supersedes"]="o1"
    add("correction_feline","explicit_correction","feline_test",[reject("feline_subject"),correction],
        [[atom("feline_subject")]],"recommend","Explicit correction replaces the earlier rejection without deleting it.")
    correction = dislike(11014); correction["supersedes"]="o1"
    add("correction_nature","explicit_correction","nature_dev",[like(11014),correction,confirm("nature_subject")],
        [[atom("nature_subject")]],"recommend","Correct an artwork response while keeping the separately confirmed subject interest.")
    correction = reject("expressionist_style"); correction["supersedes"]="o4"
    add("correction_interaction_block","explicit_correction","expression_dev",
        [like(8416),dislike(13231),dislike(8296),confirm("expressionist_style"),correction,confirm("oil_medium")],
        [[atom("oil_medium")]],"recommend","Rejecting a component blocks the inferred conjunction; an independent oil interest remains.")
    return cases


def support_index(evidence):
    defs={(h["attribute_type"],h["value_id"]):h["id"] for h in evidence["hypotheses"]}
    return {a:{defs[(x["type"],x["value_id"])] for x in row["attributes"] if (x["type"],x["value_id"]) in defs}
            for a,row in evidence["artworks"].items()}


def order_candidates(ids, scenario_id, permutation=0):
    seed = int.from_bytes(hashlib.sha256(f"{SEED}:{scenario_id}:{permutation}".encode()).digest()[:8],"big")
    ids=sorted(set(ids)); random.Random(seed).shuffle(ids)
    return ids, seed


def render_history(observations,evidence):
    labels={h["id"]:h["label"] for h in evidence["hypotheses"]}
    lines=[]
    for o in observations:
        k=o["kind"]
        if k in {"likes","dislikes"}:
            t=f"I {'liked' if k=='likes' else 'disliked'} {evidence['artworks'][o['object_id']]['label']} ({o['object_id']})."
        elif k=="reject_atomic_explanation":
            t=f"I do not identify {labels[o['object_id']]} as an independent interest; this does not ban artworks containing it."
        elif k=="reject_pair_explanation":
            t="I do not identify the conjunction of "+" and ".join(labels[h] for h in o["components"])+" as an interest; this does not reject either independent interest."
        elif o.get("components"):
            t="I " + ("prefer" if k=="explicit_conjunction" else "reject") + " the combination of " + " and ".join(labels[h] for h in o["components"]) + " specifically together."
        else:
            t=f"I {'am interested in' if k=='explicit_interest' else 'do not want'} {labels[o['object_id']]} as an independent interest."
        if o.get("supersedes"): t=f"Correction replacing statement {o['supersedes']}: "+t
        lines.append(f"{o['id']}: {t}")
    return "\n".join(lines)


def build():
    evidence=json.loads((ROOT/"data/curated/clarification_evidence.json").read_text(encoding="utf-8"))
    supports=support_index(evidence)
    defs={h["id"]:(h["attribute_type"],h["value_id"]) for h in evidence["hypotheses"]}
    # A fixed balanced pool independent of each case's latent label. Observed works excluded.
    pool=[14531,16386,12372,17716,21076,30919,15247,16916,23352,14588,33200,25837,
          20804,8415,42361,13231,8296,10766,21066,19176,10632,13233,10025,8145]
    scenarios=authored_cases()
    for s in scenarios:
        for i,o in enumerate(s["observations"],1): o["id"]=f"o{i}"
        observed={o["object_id"] for o in s["observations"] if o["kind"] in {"likes","dislikes"}}
        candidates=["ag_"+str(a) for a in pool if "ag_"+str(a) not in observed]
        s["candidate_artwork_ids"],s["candidate_order_seed"]=order_candidates(candidates,s["scenario_id"])
        s["permutation_id"]=0
        s["subset"]="held_out" if s["group_id"].endswith("test") else "development"
        s["benchmark_kind"]="controlled_robustness"
        s["label_review_status"]="authored_by_implementation_agent_not_independently_human_reviewed"
        s["hidden_fact_ids"]=[]
        for a,h in s.pop("mask"):
            attributes=[x for x in evidence["artworks"]["ag_"+str(a)]["attributes"] if (x["type"],x["value_id"])==defs["h_"+h]]
            assert attributes, (a,h)
            s["hidden_fact_ids"].extend(f for x in attributes for f in x["fact_ids"])
        s["hidden_fact_ids"]=sorted(set(s["hidden_fact_ids"]))
        s["evidence_incomplete"]=bool(s["hidden_fact_ids"])
        s["natural_language_history"]=render_history(s["observations"],evidence)
        s["worlds"]=[{"profile":profile,"relevant_artwork_ids":sorted(a for a in candidates if any(set(e["components"])<=supports[a] for e in profile))} for profile in s.pop("latent_profiles")]
        assert all(w["relevant_artwork_ids"] for w in s["worlds"]),s["scenario_id"]
        s["provenance"]={a:sorted({f for x in evidence["artworks"][a]["attributes"] for f in x["fact_ids"]}) for a in sorted(observed|set(candidates))}
    original=[json.loads(line) for line in (ROOT/"evaluation/preference_state_scenarios.jsonl").read_text(encoding="utf-8").splitlines()]
    for s in original:
        s["benchmark_kind"]="pattern_matched_regression"
        s["candidate_artwork_ids"],s["candidate_order_seed"]=order_candidates(s["candidate_artwork_ids"],s["scenario_id"])
        s["permutation_id"]=0
        s["worlds"]=[{"profile":[s["latent_profile"]],"relevant_artwork_ids":s["relevant_artwork_ids"]}]
        s["expected_action_type"]="clarify"
        s["evidence_incomplete"]=False;s["hidden_fact_ids"]=[]
    return scenarios,original


def audit(scenarios, original):
    def obs_arts(ss): return {o["object_id"] for s in ss for o in s["observations"] if o["kind"] in {"likes","dislikes"}}
    def histories(ss): return {json.dumps([{k:v for k,v in o.items() if k!='id'} for o in s["observations"]],sort_keys=True) for s in ss}
    def profiles(ss): return {e["kind"]+":"+",".join(sorted(e["components"])) for s in ss for w in s["worlds"] for e in w["profile"]}
    evidence=json.loads((ROOT/"data/curated/clarification_evidence.json").read_text(encoding="utf-8"))
    types={h["id"]:h["attribute_type"] for h in evidence["hypotheses"]}
    def schemas(ss): return {"+".join(sorted(types[h] for h in e["components"])) for s in ss for w in s["worlds"] for e in w["profile"] if e["kind"]=="all_of"}
    dev=[s for s in scenarios if s["subset"]=="development"];held=[s for s in scenarios if s["subset"]=="held_out"]
    return {"version":"corrected_v2","seed":SEED,"scenario_count":len(scenarios),"categories":dict(Counter(s["category"] for s in scenarios)),
        "splits":dict(Counter(s["subset"] for s in scenarios)),"world_count":sum(len(s["worlds"]) for s in scenarios),
        "group_overlap":sorted({s["group_id"] for s in dev}&{s["group_id"] for s in held}),
        "identical_history_overlap":len(histories(dev)&histories(held)),
        "observation_artwork_overlap":sorted(obs_arts(dev)&obs_arts(held)),
        "candidate_artwork_overlap":sorted({a for s in dev for a in s["candidate_artwork_ids"]}&{a for s in held for a in s["candidate_artwork_ids"]}),
        "profile_structure_overlap":sorted(profiles(dev)&profiles(held)),
        "development_interaction_schemas":sorted(schemas(dev)),
        "held_out_interaction_schemas":sorted(schemas(held)),
        "interaction_schema_overlap":sorted(schemas(dev)&schemas(held)),
        "historical_regression_identical_history_overlap":len(histories([s for s in original if s['subset']=='development'])&histories([s for s in original if s['subset']=='held_out'])),
        "original_target_positions":dict(sorted(Counter(s["candidate_artwork_ids"].index(s["construction"]["target_artwork_id"])+1 for s in original).items())),
        "generalization":"in-pattern; same vocabulary, shared candidate pool and related cross-type schemas",
        "review_status":"Case cards authored before evaluation by the same implementation agent; independent human review pending.",
        "limitations":["32 cases are small, clustered and authored, not an independently collected visitor dataset.","Explicit conjunction cases cover conditional statements outside the original trigger but make state identification easier.","Full-world relevance labels use recorded support; masks change model-visible evidence only.","Known incompleteness is signaled; unannounced missingness remains untested.","Four ambiguous cases have two worlds each; worlds and permutations are not independent samples."]}


def main():
    scenarios,original=build()
    for name,rows in [("preference_state_robustness_scenarios.jsonl",scenarios),("preference_state_corrected_scenarios.jsonl",original)]:
        (ROOT/"evaluation"/name).write_text("".join(json.dumps(s,ensure_ascii=False,sort_keys=True)+"\n" for s in rows),encoding="utf-8",newline="\n")
    report=audit(scenarios,original)
    (ROOT/"docs/preference_state_robustness_audit.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps(report,indent=2))

if __name__=="__main__": main()
