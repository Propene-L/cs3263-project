from pathlib import Path
from evaluation.evaluate_integrated_guide import evaluate, load_jsonl
from museum_guide.dialogue import MuseumDialogue
from museum_guide.knowledge_layer import Topic, TopicLibrary
from test_phase2_dialogue import EVIDENCE, TOPICS, FakeProlog


def test_acceptance_runner_does_not_claim_human_ground_truth():
    guide=MuseumDialogue(EVIDENCE,TOPICS,preference_engine=FakeProlog(),candidate_artworks=("ag_1","ag_2"))
    cases=[{'id':'knowledge', 'turns':[{'visitor':'topic c_portrait','expected_action':'ask_knowledge'},
                                       {'visitor':'no','expected_action':'explain'}]}]
    report=evaluate(guide,cases,mode='manual')
    assert report['summary']['error_count']==0
    assert report['summary']['authored_action_match']==1.0
    assert report['summary']['source_coverage_of_explain_or_recommend']==1.0
    assert len(report['turns'])==2


def test_error_does_not_advance_the_evaluation_state():
    guide=MuseumDialogue(EVIDENCE,TOPICS,preference_engine=FakeProlog(),candidate_artworks=("ag_1","ag_2"))
    cases=[{'id':'wrong', 'turns':[{'visitor':'yes','expected_action':'clarify_interest'},
                                  {'visitor':'like ag_1'}]}]
    report=evaluate(guide,cases,mode='manual')
    assert report['summary']['error_count']==1
    assert report['summary']['complete_scenarios']==0
    assert report['turns'][0]['status']=='error'
