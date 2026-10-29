"""Corrected direct-LLM interface. Inputs are constructed by allowlist only."""
from __future__ import annotations
from copy import deepcopy
from typing import Any

from .preference_state import PreferenceState, validate_state
from .preference_state_baselines import DirectPreferenceStateLLM, PreferenceEvidenceIndex
from .preference_state_comparator import visible_evidence, common_ranking

EXPLANATION_SCHEMA = {
    "type":"object", "properties":{
        "kind":{"type":"string","enum":["atomic","all_of"]},
        "components":{"type":"array","items":{"type":"string"}},
    }, "required":["kind","components"], "additionalProperties":False,
}
PREFERENCE_SCHEMA=deepcopy(EXPLANATION_SCHEMA)
PREFERENCE_SCHEMA["properties"]["status"]={"type":"string","enum":[
    "explicitly_confirmed","explicitly_rejected","candidate","reinforced","mixed","interaction_candidate"]}
PREFERENCE_SCHEMA["required"].append("status")


class CorrectedDirectPreferenceStateLLM(DirectPreferenceStateLLM):
    OUTPUT_SCHEMA={
        "type":"object","properties":{
            "inferred_preferences":{"type":"array","items":PREFERENCE_SCHEMA},
            "primary_explanation":{"anyOf":[EXPLANATION_SCHEMA,{"type":"null"}]},
            "next_action_type":{"type":"string","enum":["recommend","clarify","insufficient_evidence"]},
            "artwork_id":{"type":["string","null"]},
            "question_explanation":{"anyOf":[EXPLANATION_SCHEMA,{"type":"null"}]},
            "rationale":{"type":"string"},
        },
        "required":["inferred_preferences","primary_explanation","next_action_type","artwork_id","question_explanation","rationale"],
        "additionalProperties":False,
    }

    def build_payload(self,state:PreferenceState,natural_language_history:str)->dict:
        validate_state(state,self.index.evidence)
        view=visible_evidence(self.index.evidence,state)
        observed=sorted({o.object_id for o in state.observations if o.kind in {"likes","dislikes"}})
        # Candidate presentation preserves the recorded permutation, including its facts.
        return {
            "task":(
                "Infer provisional visitor interests from this history. Atomic and conjunction interests may coexist. "
                "Preserve explicit statements and corrections. A disliked artwork does not universally reject its attributes. "
                "Do not select a dominant explanation if the evidence is ambiguous. Recommend an eligible artwork when justified; "
                "otherwise ask a yes/no/unsure confirmation about one atomic or conjunction interest, or report insufficient evidence. "
                "A confirmation of all_of asks whether the visitor prefers these features specifically together. "
                "Recommendations must respect explicit rejections and must not repeat observed artworks."
            ),
            "output_instruction":(
                "Return exactly one JSON object matching required_output_schema. "
                "Use the property names verbatim and do not add properties."
            ),
            "required_output_schema":deepcopy(self.OUTPUT_SCHEMA),
            "visitor_history":natural_language_history,
            "hypothesis_vocabulary":view["hypotheses"],
            "observed_artworks":[{"artwork_id":a,**view["artworks"][a]} for a in observed],
            "candidate_artworks":[{"artwork_id":a,**view["artworks"][a]} for a in state.allowed_action_artwork_ids],
            "evidence_incomplete":state.evidence_incomplete or bool(state.hidden_fact_ids),
            "missing_support_policy":"not_recorded means unknown; the view may omit actual attributes",
        }

    def _explanation(self,value:Any)->dict:
        if not isinstance(value,dict) or set(value)!={"kind","components"}:
            raise ValueError("Invalid explanation fields")
        kind=value["kind"];components=value["components"]
        if kind not in {"atomic","all_of"} or not isinstance(components,list):
            raise ValueError("Invalid explanation type")
        if len(components)!=(1 if kind=="atomic" else 2) or any(not isinstance(h,str) for h in components):
            raise ValueError("Invalid component count or type")
        if len(set(components))!=len(components) or not set(components)<=set(self.index.hypothesis_rows):
            raise ValueError("Invalid component ID or duplicate")
        return {"kind":kind,"components":sorted(components)}

    def _normalize_components(self,result:dict)->tuple[dict,list[dict]]:
        """Map exact vocabulary labels to IDs without fuzzy interpretation."""
        normalized=deepcopy(result)
        aliases:dict[str,str]={}
        ambiguous:set[str]=set()
        for hypothesis_id,row in self.index.hypothesis_rows.items():
            label=row.get("label")
            if not isinstance(label,str):
                continue
            key=label.strip().casefold()
            previous=aliases.get(key)
            if previous is not None and previous!=hypothesis_id:
                ambiguous.add(key)
            else:
                aliases[key]=hypothesis_id
        for key in ambiguous:
            aliases.pop(key,None)
        known=set(self.index.hypothesis_rows)
        changes:list[dict]=[]

        def explanation(value:Any,path:str)->None:
            if not isinstance(value,dict) or not isinstance(value.get("components"),list):
                return
            for index,component in enumerate(value["components"]):
                if not isinstance(component,str):
                    continue
                stripped=component.strip()
                mapped=stripped if stripped in known else aliases.get(stripped.casefold())
                if mapped is not None and mapped!=component:
                    value["components"][index]=mapped
                    changes.append({"path":f"{path}.components[{index}]","input":component,
                        "output":mapped,"rule":"exact_official_label_or_id"})

        preferences=normalized.get("inferred_preferences")
        if isinstance(preferences,list):
            for index,value in enumerate(preferences):
                explanation(value,f"inferred_preferences[{index}]")
        explanation(normalized.get("primary_explanation"),"primary_explanation")
        explanation(normalized.get("question_explanation"),"question_explanation")
        return normalized,changes

    def infer(self,state:PreferenceState,*,natural_language_history:str)->dict:
        payload=self.build_payload(state,natural_language_history)
        self.last_record={"request":payload,"status":"attempting"}
        try:
            result=self.transport.complete_json(payload)
            self.last_record.update(raw_response=result.get("_raw_response",result),transport_metadata=result.get("_transport_metadata",{}))
            result,normalizations=self._normalize_components(result)
            self.last_record["normalizations"]=normalizations
            self.last_record["normalization_policy"]="stable IDs or exact unique official labels, trimmed and case-insensitive; no fuzzy matching"
            allowed=set(self.OUTPUT_SCHEMA["required"])|{"_raw_response","_transport_metadata"}
            if set(result)-allowed or not set(self.OUTPUT_SCHEMA["required"])<=set(result):
                raise ValueError("Invalid output fields")
            preferences=result["inferred_preferences"]
            if not isinstance(preferences,list): raise ValueError("Preferences must be a list")
            validated=[];seen=set()
            for e in preferences:
                if not isinstance(e,dict) or set(e)!={"kind","components","status"}: raise ValueError("Invalid preference fields")
                clean=self._explanation({k:e[k] for k in ("kind","components")})
                if e["status"] not in PREFERENCE_SCHEMA["properties"]["status"]["enum"]: raise ValueError("Invalid preference status")
                key=(clean["kind"],tuple(clean["components"]))
                if key in seen: raise ValueError("Duplicate explanation")
                seen.add(key);clean["status"]=e["status"];validated.append(clean)
            primary=self._explanation(result["primary_explanation"]) if result["primary_explanation"] is not None else None
            if primary and not any(e["kind"]==primary["kind"] and e["components"]==primary["components"] and e["status"] not in {"mixed","explicitly_rejected"} for e in validated):
                raise ValueError("Primary explanation must be an active returned preference")
            action=result["next_action_type"];artwork=result["artwork_id"];q=result["question_explanation"]
            if action not in {"recommend","clarify","insufficient_evidence"}: raise ValueError("Invalid action type")
            if action=="recommend":
                if not isinstance(artwork,str) or artwork not in state.allowed_action_artwork_ids or q is not None: raise ValueError("Invalid recommendation")
            elif action=="clarify":
                if artwork is not None: raise ValueError("A topic confirmation does not select an artwork")
                q=self._explanation(q)
            elif artwork is not None or q is not None:
                raise ValueError("Abstention must not contain an action")
            if not isinstance(result["rationale"],str): raise ValueError("Rationale must be text")
            index=PreferenceEvidenceIndex(visible_evidence(self.index.evidence,state))
            output={"status":"ok","preference_explanations":validated,"primary_explanation":primary,
                "ranked_actions":common_ranking(state,validated,index),
                "decision":{"action_type":action,"artwork_id":artwork,"question":({"kind":"confirm_explanation","explanation":q,"responses":["yes","no","unsure"]} if q else None),"reason":result["rationale"]},
                "unresolved_explanation_count":sum(e["status"] in {"candidate","reinforced","mixed","interaction_candidate"} for e in validated)}
            self.last_record.update(status="validated",validated_result=output)
            output["llm_record"]=deepcopy(self.last_record)
            return output
        except Exception as exc:
            self.last_record.update(status="error",error=f"{type(exc).__name__}: {exc}")
            exchange=getattr(self.transport,"last_exchange",None)
            if exchange: self.last_record["transport_exchange"]=deepcopy(exchange)
            raise
