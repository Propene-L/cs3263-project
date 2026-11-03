"""Create a reproducible method-blind, unscored, text-only v2 review sheet."""
from __future__ import annotations
import csv
import hashlib
import json
import random
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SEED=32631203


def support_labels(artwork_id,evidence):
    defs={(h["attribute_type"],h["value_id"]):h for h in evidence["hypotheses"]}
    rows=[]
    for a in evidence["artworks"][artwork_id]["attributes"]:
        h=defs.get((a["type"],a["value_id"]))
        if h: rows.append(f"{h['label']} [{', '.join(a['fact_ids'])}]")
    return "; ".join(rows) or "no reviewed hypothesis support recorded"


def action_text(method_row,evidence,hypotheses):
    d=method_row["result"]["decision"]
    if d["action_type"]=="recommend":
        a=d["artwork_id"]
        return f"Recommend {evidence['artworks'][a]['label']} ({a}). Recorded attributes: {support_labels(a,evidence)}"
    if d["action_type"]=="clarify":
        e=d["question"]["explanation"]
        labels=[hypotheses[h] for h in e["components"]]
        phrase="specifically together" if e["kind"]=="all_of" else "as an independent interest"
        return f"Ask whether the visitor is interested in {' + '.join(labels)} {phrase} (yes / no / unsure)."
    return "Report insufficient evidence and request more visitor information before selecting an artwork."


def main():
    result_path=ROOT/"evaluation/preference_state_corrected_results.json"
    results=json.loads(result_path.read_text(encoding="utf-8"))
    evidence=json.loads((ROOT/"data/curated/clarification_evidence.json").read_text(encoding="utf-8"))
    hypotheses={h["id"]:h["label"] for h in evidence["hypotheses"]}
    scenarios={s["scenario_id"]:s for name in ["preference_state_corrected_scenarios.jsonl","preference_state_robustness_scenarios.jsonl"]
        for s in (json.loads(line) for line in (ROOT/"evaluation"/name).read_text(encoding="utf-8").splitlines())}
    candidates=[]
    for row in results["scenarios"]:
        p=row["methods"]["compositional_prolog"];b=row["methods"]["signed_additive_atomic"]
        pa=action_text(p,evidence,hypotheses);ba=action_text(b,evidence,hypotheses)
        if pa==ba: continue
        both_may_be_wrong=(p["metrics"]["top1_relevance"]<1 and b["metrics"]["top1_relevance"]<1)
        candidates.append((not both_may_be_wrong,row["scenario_id"],pa,ba,both_may_be_wrong))
    candidates.sort(key=lambda x:(x[0],hashlib.sha256(x[1].encode()).hexdigest()))
    selected=candidates[:16]
    fields=["review_item_id","scenario_id","visitor_history","recorded_observation_evidence",
        "presentation_seed","action_a","action_b","more_relevant_a_b_equal_neither",
        "overinterpretation_a_b_both_neither","clarification_more_appropriate_yes_no_unsure",
        "useful_next_step_a_b_equal_neither","reviewer_notes"]
    output=ROOT/"evaluation/preference_state_corrected_human_review.csv"
    with output.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for i,(_,sid,pa,ba,_) in enumerate(selected,1):
            s=scenarios[sid];seed=int.from_bytes(hashlib.sha256(f"{SEED}:{sid}".encode()).digest()[:8],"big")
            order=[pa,ba];random.Random(seed).shuffle(order)
            evidence_text=" | ".join(f"{o['id']} {o['kind']} {o['object_id']}: {support_labels(o['object_id'],evidence)}"
                for o in s["observations"] if o["kind"] in {"likes","dislikes"})
            w.writerow({"review_item_id":f"corrected_review_{i:02d}","scenario_id":sid,
                "visitor_history":s["natural_language_history"],"recorded_observation_evidence":evidence_text,
                "presentation_seed":seed,"action_a":order[0],"action_b":order[1],
                "more_relevant_a_b_equal_neither":"","overinterpretation_a_b_both_neither":"",
                "clarification_more_appropriate_yes_no_unsure":"","useful_next_step_a_b_equal_neither":"","reviewer_notes":""})
    manifest={"version":"corrected_v2","seed":SEED,"source_results_sha256":hashlib.sha256(result_path.read_bytes()).hexdigest(),
        "item_count":len(selected),"contains_method_disagreements":True,"contains_both_may_be_wrong_cases":any(x[4] for x in selected),
        "both_may_be_wrong_definition":"Both methods' raw top-ranked artworks are irrelevant in at least one controlled world; human action judgments remain unscored.",
        "review_mode":"text-only ArtGraph attributes and labels; no artwork images; unscored until human responses",
        "ordering":"A/B position deterministically randomized; presentation_seed recorded per item"}
    (ROOT/"docs/preference_state_human_review_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps(manifest,indent=2))

if __name__=="__main__":main()
