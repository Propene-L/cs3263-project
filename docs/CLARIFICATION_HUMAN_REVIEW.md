# Clarification Human Review

## Status and limits

No human judgments have been collected. The prepared sheet at
`evaluation/clarification_human_review.csv` contains 12 held-out, method-blind
textual clarification items and deliberately blank rating cells. Do not treat
blank cells as zeros and do not invent aggregate scores.

No artwork images are bundled because the ArtGraph licensing status remains
unresolved. Review therefore measures textual question suitability and its
recorded factual basis, not genuine visual preference or the experience of
viewing the artwork.

## Reviewer task

For each anonymized pair, use a 1–5 scale:

1. Is the question understandable?
2. Are the artwork labels and stated typed attributes accurate against the
   supplied ArtGraph evidence?
3. Is the intended comparison meaningful?
4. Could this comparison plausibly clarify the stated visitor interests?
5. Are the supporting deductions represented correctly without treating
   missing RDF as a negative fact?

Add free-text notes for ambiguity, unfamiliar terminology, correlated
hypotheses, broad media, or reasons the pair would be hard to answer. A rating
of question usefulness must not be interpreted as a revealed artwork
preference.

## Procedure

1. Recruit at least two reviewers with no access to the selecting method.
2. Randomize row order per reviewer while retaining `review_item_id`.
3. Provide the same textual evidence and rubric to every reviewer.
4. Verify labels/fact IDs against `data/curated/clarification_evidence.json`.
5. Preserve individual ratings before computing summaries.
6. Report reviewer count, expertise, missing ratings, disagreements, and the
   aggregation rule. Do not tune ranking parameters on held-out ratings.
7. If images become legally available, run a separately labeled image-based
   study; do not merge it with this text-only sample.

The sheet can be regenerated after a genuine evaluation run with:

```powershell
.\.venv\Scripts\python.exe scripts\build_clarification_human_review.py
```

## Realism questions to discuss qualitatively

- Did a reviewer choose based on an unmodeled feature such as color or mood?
- Did multiple styles/subjects make the intended single-attribute contrast
  implausible?
- Did both, neither, or unfamiliarity feel more natural than a forced choice?
- Was a recorded medium visibly relevant?
- Did movement/style correlation make hypotheses redundant?
- Did text alone make the comparison impossible to judge?

These observations should be reported separately from formal resolution rates.
