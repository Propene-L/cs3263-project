"""Corrected v2 evaluation: coverage, uncertainty, rankings, and actual updates.

Each scenario is a unit. Alternative worlds are averaged within that unit;
candidate permutations are a separate sensitivity audit, never extra samples.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import statistics
import time
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from museum_guide.preference_state import PreferenceObservation, PreferenceState, default_preference_state_engine, validate_state
from museum_guide.preference_state_baselines import PositiveAccumulationBaseline, SignedAdditiveAtomicBaseline, PreferenceEvidenceIndex
from museum_guide.preference_state_comparator import (
    InteractionPythonBaseline, active_observations, explicit_records, explanation_key,
    visible_evidence, finish_result, POSITIVE, PENDING,
)
from museum_guide.preference_state_llm import CorrectedDirectPreferenceStateLLM
from scripts.build_preference_state_robustness import order_candidates, SEED, render_history

ROOT=Path(__file__).resolve().parents[1]
METHODS=("positive_attribute_accumulation","signed_additive_atomic","existing_atomic_prolog","compositional_prolog","interaction_python")
LLM="direct_llm_state_reasoning"


def read_jsonl(path): return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def mean(values):
    xs=[x for x in values if x is not None]
    return round(statistics.fmean(xs),6) if xs else None


def make_state(s):
    return PreferenceState(s["scenario_id"],tuple(PreferenceObservation(**{**o,"components":tuple(o.get("components",()))}) for o in s["observations"]),
        tuple(s["candidate_artwork_ids"]),hidden_fact_ids=tuple(s.get("hidden_fact_ids",())),evidence_incomplete=s.get("evidence_incomplete",False))


class Runner:
    def __init__(self,evidence,run_llm=False):
        self.evidence=evidence
        self.engine=default_preference_state_engine(ROOT)
        self.python=InteractionPythonBaseline(evidence)
        self.llm=CorrectedDirectPreferenceStateLLM.from_environment(evidence) if run_llm else None
        self.llm_calls=[]

    def infer(self,method,state,history):
        start=time.perf_counter()
        validate_state(state,self.evidence)
        if method in {"compositional_prolog","existing_atomic_prolog"}:
            result=self.engine.infer(replace(state,mode="atomic" if method=="existing_atomic_prolog" else "compositional"))
        elif method=="interaction_python": result=self.python.infer(state)
        elif method==LLM:
            try:
                result=self.llm.infer(state,natural_language_history=history)
            finally:
                self.llm_calls.append({"scenario_id":state.session_id,"elapsed_ms":(time.perf_counter()-start)*1000,
                    "candidate_order":list(state.allowed_action_artwork_ids),"record":deepcopy(self.llm.last_record)})
        else:
            view=visible_evidence(self.evidence,state)
            baseline=(PositiveAccumulationBaseline if method==METHODS[0] else SignedAdditiveAtomicBaseline)(view)
            native=baseline.infer(replace(state,observations=tuple(active_observations(state))))
            result=finish_result(state,native.preference_explanations,PreferenceEvidenceIndex(view))
            result["native_ranked_actions"]=native.ranked_actions
        result["runtime_ms"]=(time.perf_counter()-start)*1000
        return result


def state_metrics(result, profile):
    gold={explanation_key(e) for e in profile}
    all_returned={explanation_key(e) for e in result["preference_explanations"]}
    asserted={explanation_key(e) for e in result["preference_explanations"] if e["status"] in POSITIVE}
    primary=result.get("primary_explanation")
    atoms={e for e in asserted if e[0]=="atomic"}
    interactions={e for e in asserted if e[0]=="all_of"}
    primary_key=explanation_key(primary) if primary else None
    return {
        "explanation_coverage":gold<=all_returned,
        "primary_explanation_accuracy":primary_key in gold,
        "explanation_precision":len(asserted&gold)/len(asserted) if asserted else 0.0,
        "explanation_recall":len(asserted&gold)/len(gold) if gold else float(not asserted),
        "false_interaction_rate":bool(interactions-gold),
        "false_interaction_prioritized":primary_key is not None and primary_key[0]=="all_of" and primary_key not in gold,
        "false_atomic_interest_rate":len(atoms-gold)/len(atoms) if atoms else 0.0,
        "asserted_explanation_count":len(asserted),
    }


def ranking_metrics(actions,relevant,k=3):
    ids=[a["artwork_id"] for a in actions]
    kk=min(k,len(ids)); hit=len(set(ids[:kk])&set(relevant))
    return {"top1_relevance":bool(ids and ids[0] in relevant),
        "recall_at_k":hit/len(relevant) if relevant else 0.0,
        "precision_at_k":hit/kk if kk else 0.0,
        "hit_at_k":hit>0,"irrelevant_action_rate":not bool(ids and ids[0] in relevant),"k":kk}


def decision_validity(result,state,index):
    d=result["decision"];action=d.get("action_type")
    if action=="insufficient_evidence": return d.get("artwork_id") is None and d.get("question") is None
    if action=="clarify":
        q=d.get("question")
        if not isinstance(q,dict) or q.get("kind")!="confirm_explanation": return False
        e=q.get("explanation",{});cs=e.get("components",[])
        return (e.get("kind") in {"atomic","all_of"} and len(cs)==(1 if e["kind"]=="atomic" else 2)
            and len(cs)==len(set(cs)) and set(cs)<=set(index.hypothesis_rows)
            and d.get("artwork_id") is None)
    if action!="recommend": return False
    a=d.get("artwork_id")
    if a not in state.allowed_action_artwork_ids: return False
    if a in {o.object_id for o in active_observations(state) if o.kind in {"likes","dislikes"}}: return False
    explicit=explicit_records(state);supported=index.supports[a]
    kinds={o.id:o.kind for o in active_observations(state)}
    if any(set(cs)<=supported for (_,cs),(s,oid) in explicit.items()
           if s=="explicitly_rejected" and kinds[oid] in {"explicit_rejection","reject_conjunction"}): return False
    confirmed=[set(cs) for (_,cs),(s,_) in explicit.items() if s=="explicitly_confirmed"]
    return not confirmed or any(cs<=supported for cs in confirmed)


def evaluate_result(result,s,state,evidence):
    worlds=s["worlds"]
    values=[{**state_metrics(result,w["profile"]),**ranking_metrics(result["ranked_actions"],w["relevant_artwork_ids"])} for w in worlds]
    metrics={k:mean(v[k] for v in values) for k in values[0]}
    d=result["decision"];expected=s["expected_action_type"]
    index=PreferenceEvidenceIndex(visible_evidence(evidence,state))
    should_abstain=expected in {"clarify","insufficient_evidence"}
    metrics.update({
        "action_type_accuracy":d["action_type"]==expected,
        "appropriate_abstention":(result.get("primary_explanation") is None and d["action_type"]!="recommend") if should_abstain else None,
        "decision_validity":decision_validity(result,state,index),
        "unnecessary_clarification":d["action_type"]=="clarify" if expected=="recommend" else None,
        "failure_to_clarify":d["action_type"]!="clarify" if expected=="clarify" else None,
        "selected_recommendation_relevance":mean(d["artwork_id"] in w["relevant_artwork_ids"] for w in worlds) if d["action_type"]=="recommend" else None,
        "clean_probe_at_1":bool(result["ranked_actions"] and result["ranked_actions"][0]["artwork_id"] in s.get("clarification_useful_ids",[])) if s.get("family")=="contrastive_atomic" else None,
        "unresolved_explanation_count":result.get("unresolved_explanation_count",0),
        "runtime_ms":result.get("runtime_ms"),
    })
    return metrics


def controlled_response(question,profile):
    """A transparent membership oracle, not an artwork-liking simulator or human."""
    if question is None: return "unsure"
    return "yes" if explanation_key(question["explanation"]) in {explanation_key(e) for e in profile} else "no"


def apply_response(state,question,response):
    """Append an explicit observation; preserve the complete original tuple."""
    if response=="unsure": return state
    if response not in {"yes","no"}: raise ValueError("Unknown controlled response")
    e=question["explanation"];cs=tuple(sorted(e["components"]))
    kind=("explicit_interest" if response=="yes" else "reject_atomic_explanation") if e["kind"]=="atomic" else ("explicit_conjunction" if response=="yes" else "reject_pair_explanation")
    next_id="answer_"+str(len(state.observations)+1)
    if next_id in {o.id for o in state.observations}: raise ValueError("Duplicate answer ID")
    observation=PreferenceObservation(next_id,kind,cs[0] if e["kind"]=="atomic" else "preference_pair",cs if e["kind"]=="all_of" else ())
    return replace(state,observations=(*state.observations,observation))


def clarification_loop(runner,method,state,s,before):
    decision=before["decision"]
    if decision["action_type"]!="clarify": return {"asked":False,"worlds":[]}
    question=decision["question"];world_rows=[]
    for wi,world in enumerate(s["worlds"]):
        response=controlled_response(question,world["profile"])
        updated=apply_response(state,question,response)
        history=s["natural_language_history"]+"\nClarification answer: "+render_history([asdict(updated.observations[-1])],runner.evidence)
        after=runner.infer(method,updated,history)
        bm=state_metrics(before,world["profile"]);am=state_metrics(after,world["profile"])
        br=ranking_metrics(before["ranked_actions"],world["relevant_artwork_ids"]);ar=ranking_metrics(after["ranked_actions"],world["relevant_artwork_ids"])
        survivors=sum(controlled_response(question,w["profile"])==response for w in s["worlds"])
        remaining=after["unresolved_explanation_count"]
        informative=(remaining<before["unresolved_explanation_count"] or survivors<len(s["worlds"]) or am["explanation_precision"]!=bm["explanation_precision"] or am["explanation_recall"]!=bm["explanation_recall"])
        world_rows.append({"world_index":wi,"response":response,"informative_response":informative,
            "remaining_plausible_explanations":remaining,"remaining_controlled_worlds":survivors,
            "primary_accuracy_delta":float(am["primary_explanation_accuracy"])-float(bm["primary_explanation_accuracy"]),
            "explanation_precision_delta":am["explanation_precision"]-bm["explanation_precision"],
            "explanation_recall_delta":am["explanation_recall"]-bm["explanation_recall"],
            "recommendation_top1_delta":float(ar["top1_relevance"])-float(br["top1_relevance"]),
            "recommendation_top1_after":ar["top1_relevance"],
            "selected_recommendation_relevance_after":after["decision"]["artwork_id"] in world["relevant_artwork_ids"] if after["decision"]["action_type"]=="recommend" else None,
            "updated_observations":[asdict(o) for o in updated.observations],"after":after})
    return {"asked":True,"question":question,"worlds":world_rows}


def summarize(rows,methods):
    summary={}
    for method in methods:
        items=[r["methods"][method] for r in rows]
        successful=[x for x in items if "metrics" in x]
        metrics={k:mean(x["metrics"][k] for x in successful) for k in successful[0]["metrics"]} if successful else {}
        loops=[x["clarification"] for x in successful if x.get("clarification",{}).get("asked")]
        loop_fields=["informative_response","remaining_plausible_explanations","remaining_controlled_worlds","primary_accuracy_delta","explanation_precision_delta","explanation_recall_delta","recommendation_top1_delta","recommendation_top1_after","selected_recommendation_relevance_after"]
        loop_metrics={k:mean(mean(w[k] for w in l["worlds"]) for l in loops) for k in loop_fields}
        summary[method]={"scenario_count":len(items),"successful_scenario_count":len(successful),"error_count":len(items)-len(successful),
            "valid_decisions_per_attempt":sum(bool(x["metrics"]["decision_validity"]) for x in successful)/len(items) if items else None,
            "metrics":metrics,"clarification":{"asked_count":len(loops),**loop_metrics}}
    return summary


def signature(result):
    return {"explanations":sorted((e["kind"],tuple(sorted(e["components"])),e["status"]) for e in result["preference_explanations"]),
        "primary":explanation_key(result["primary_explanation"]) if result.get("primary_explanation") else None,
        "ranking":[a["artwork_id"] for a in result["ranked_actions"]],
        "decision":{k:result["decision"].get(k) for k in ["action_type","artwork_id","question"]}}


def evaluate(scenarios,runner,methods,loop=True):
    rows=[]
    for i,s in enumerate(scenarios):
        state=make_state(s);mr={}
        for method in methods:
            try:
                result=runner.infer(method,state,s["natural_language_history"])
                mr[method]={"result":result,"metrics":evaluate_result(result,s,state,runner.evidence),
                    "clarification":clarification_loop(runner,method,state,s,result) if loop else {"asked":False,"worlds":[]}}
            except Exception as exc:
                if method!=LLM: raise
                mr[method]={"error":f"{type(exc).__name__}: {exc}"}
        rows.append({"scenario_id":s["scenario_id"],"benchmark_kind":s["benchmark_kind"],"category":s.get("category",s.get("family")),
            "subset":s["subset"],"candidate_order_seed":s["candidate_order_seed"],"candidate_order":s["candidate_artwork_ids"],"world_count":len(s["worlds"]),"methods":mr})
        if (i+1)%8==0: print(f"Evaluated {i+1}/{len(scenarios)} scenarios",flush=True)
    return rows


def permutation_audit(scenarios,rows,runner,methods):
    chosen=[s for i,s in enumerate(scenarios) if i%8==0 or s.get("category")=="ambiguous"]
    lookup={r["scenario_id"]:r for r in rows};records=[]
    for s in chosen:
        for p in [1,2]:
            ids,seed=order_candidates(s["candidate_artwork_ids"],s["scenario_id"],p)
            state=replace(make_state(s),allowed_action_artwork_ids=tuple(ids))
            for method in methods:
                try:
                    result=runner.infer(method,state,s["natural_language_history"])
                    base=lookup[s["scenario_id"]]["methods"][method]
                    unchanged=signature(result)==signature(base["result"]) if "result" in base else None
                    records.append({"scenario_id":s["scenario_id"],"permutation_id":p,"seed":seed,"candidate_order":ids,"method":method,"unchanged":unchanged,"signature":signature(result)})
                except Exception as exc:
                    if method!=LLM: raise
                    records.append({"scenario_id":s["scenario_id"],"permutation_id":p,"seed":seed,"candidate_order":ids,"method":method,"error":f"{type(exc).__name__}: {exc}"})
    return {"independent_sample_count":0,"base_scenario_count":len(chosen),"records":records,
        "changed_counts":{m:sum(x.get("unchanged") is False for x in records if x["method"]==m) for m in methods}}


def historical_comparison():
    r=json.loads((ROOT/"evaluation/preference_state_results.json").read_text(encoding="utf-8"))
    ss={s["scenario_id"]:s for s in read_jsonl(ROOT/"evaluation/preference_state_corrected_scenarios.jsonl")}
    rows=[]
    for row in r["scenarios"]:
        s=ss[row["scenario_id"]];methods={}
        for m,old in row["methods"].items():
            sm=state_metrics(old,s["worlds"][0]["profile"])
            sm.update(ranking_metrics(old["ranked_actions"],s["worlds"][0]["relevant_artwork_ids"]))
            methods[m]=sm
        rows.append({"scenario_id":row["scenario_id"],"methods":methods})
    return {"source_commit":"28e77c98614ca35a23bd40f0b1ce56e01cfb8cd2","note":"Re-scoring frozen outputs, not rerunning old methods. Old state accuracy was coverage.",
        "summary":{m:{k:mean(row["methods"][m][k] for row in rows) for k in rows[0]["methods"][m]} for m in rows[0]["methods"]},"scenarios":rows}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--subset",choices=["all","development","held_out"],default="all")
    parser.add_argument("--run-direct-llm",action="store_true")
    parser.add_argument("--smoke",action="store_true")
    parser.add_argument("--output-prefix",default="preference_state_corrected")
    parser.add_argument("--llm-output",default="preference_state_llm_results.json")
    args=parser.parse_args()
    if args.smoke and args.subset!="development": parser.error("Smoke runs must use --subset development")
    if args.subset!="all" and args.output_prefix=="preference_state_corrected": parser.error("Use a distinct --output-prefix for subset runs")
    evidence=json.loads((ROOT/"data/curated/clarification_evidence.json").read_text(encoding="utf-8"))
    paths=[ROOT/"evaluation/preference_state_corrected_scenarios.jsonl",ROOT/"evaluation/preference_state_robustness_scenarios.jsonl"]
    scenarios=[s for path in paths for s in read_jsonl(path)]
    if args.subset!="all": scenarios=[s for s in scenarios if s["subset"]==args.subset]
    if args.smoke: scenarios=[next(s for s in scenarios if s["benchmark_kind"]=="pattern_matched_regression"),next(s for s in scenarios if s.get("category")=="explicit_correction")]
    runner=Runner(evidence,args.run_direct_llm);methods=list(METHODS)
    if runner.llm: methods.append(LLM)
    rows=evaluate(scenarios,runner,methods)
    permutations=permutation_audit(scenarios,rows,runner,methods)
    groups={name:summarize([r for r in rows if r["benchmark_kind"]==name],methods) for name in sorted({r["benchmark_kind"] for r in rows})}
    output={"version":"corrected_v2","executed_at_utc":datetime.now(timezone.utc).isoformat(),"seed":SEED,
        "configuration":vars(args),"methods":methods,"scenario_count":len(rows),
        "source_sha256":{str(p.relative_to(ROOT)):sha(p) for p in paths},
        "evidence_sha256":sha(ROOT/"data/curated/clarification_evidence.json"),
        "code_sha256":{p:sha(ROOT/p) for p in ["logic/preference_state_corrected_rules.pl","museum_guide/preference_state.py","museum_guide/preference_state_comparator.py","museum_guide/preference_state_llm.py","evaluation/evaluate_preference_state_corrected.py"]},
        "response_model":"Exact explanation-membership yes/no oracle; unsure preserves state. No answer rejects only the queried explanation, not all artworks containing its components.",
        "downstream_policy":"Lexicographic explicit-support count, total positive-explanation support count, artwork ID; raw ranking metrics also include states whose selected action abstains.",
        "label_notice":"Controlled authored profiles; no human preference accuracy. Worlds/permutations are not independent cases.",
        "direct_llm_status":"executed" if runner.llm else "unexecuted_missing_configuration_or_flag",
        "group_summary":groups,
        "subset_summary":{sub:{name:summarize([r for r in rows if r['subset']==sub and r['benchmark_kind']==name],methods) for name in groups} for sub in sorted({r['subset'] for r in rows})},
        "category_summary":{cat:summarize([r for r in rows if r["category"]==cat],methods) for cat in sorted({r["category"] for r in rows})},
        "historical_rescored":historical_comparison(),"candidate_order_audit":permutations,"scenarios":rows}
    outdir=ROOT/"evaluation"
    (outdir/(args.output_prefix+"_results.json")).write_text(json.dumps(output,indent=2,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n")
    flat=[{"benchmark":group,"method":m,"scenario_count":v["scenario_count"],"errors":v["error_count"],**v["metrics"],**{"loop_"+k:x for k,x in v["clarification"].items()}} for group,ms in groups.items() for m,v in ms.items()]
    fields=sorted({k for row in flat for k in row})
    with (outdir/(args.output_prefix+"_summary.csv")).open("w",encoding="utf-8",newline="") as handle:
        w=csv.DictWriter(handle,fieldnames=fields);w.writeheader();w.writerows(flat)
    if runner.llm:
        token_usage={};requests=0
        for call in runner.llm_calls:
            record=call["record"]
            meta=record.get("transport_metadata") or record.get("transport_exchange",{})
            requests+=meta.get("request_count",0)
            for k,v in meta.get("usage",{}).items():
                if isinstance(v,int): token_usage[k]=token_usage.get(k,0)+v
        llm={"version":"corrected_v2","configuration":vars(args),"executed_at_utc":output["executed_at_utc"],
            "scenario_count":len(rows),"call_count":len(runner.llm_calls),"request_count_including_retries":requests,
            "token_usage":token_usage,"failure_count":sum(c["record"].get("status")=="error" for c in runner.llm_calls),
            "refusal_count":sum("refus" in c["record"].get("error","").lower() for c in runner.llm_calls),"calls":runner.llm_calls}
        (outdir/args.llm_output).write_text(json.dumps(llm,indent=2,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({"groups":groups,"order_changes":permutations["changed_counts"],"llm":output["direct_llm_status"]},indent=2))

if __name__=="__main__": main()
