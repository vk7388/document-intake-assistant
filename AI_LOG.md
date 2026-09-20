# AI Development Log

This project was built with heavy AI assistance (Claude). This log
records the key prompts used, what was accepted as-is, what was changed,
and why — as requested by the assignment brief.

## 1. Overall architecture prompt
**Prompt:** Asked for a step-by-step plan to build a document-intake
chatbot covering backend, simple UI, multi-turn conversation, structured
state, corrections, validation, previews, tests, and setup instructions,
for a placement technical test.

**Accepted:** The overall phased plan (project setup → schema → state →
API → LLM → validation → corrections → document → UI → connect → tests →
docs → GitHub) and the core pipeline:
`user message → LLM extraction → JSON → Pydantic validation → state update`.
This separation (LLM never writes state directly) was kept exactly as
suggested because it directly satisfies the assignment's validation
requirement.

**Changed:** Given a hard one-hour deadline, collapsed the AI's suggested
21-step incremental build (build one file, run it, test it, then move on)
into a single pass producing the full, working codebase at once, then
verified the extraction logic separately by running it in isolation
(without needing the full dependency stack installed) rather than
following each step interactively.

## 2. LLM extraction design
**Prompt:** Asked how the LLM should be used to avoid it directly
mutating application state, and how to keep the app testable without
depending on a live API key.

**Accepted:** The suggested contract — LLM (or a substitute) returns
structured JSON only, validated by Pydantic before being merged into
state.

**Changed / added by me:** The original plan only sketched the OpenAI
call. I added a deterministic rule-based fallback extractor
(`extract_information_fallback`) that is used automatically whenever no
API key is configured or the API call fails, so the whole app (including
automated tests) runs fully offline. I corrected a bug I found while
testing it myself: the first version of the "I'm <name>" regex greedily
matched the rest of the sentence (e.g. "I'm Rahul and my children are
Amit and Riya" produced `full_name = "Rahul and my children are Amit and
Riya"`). I fixed this by bounding the name pattern to stop at
`" and"`, `" who"`, a comma, or a period, and re-verified against a set
of manual test cases before trusting it.

## 3. Corrections handling
**Prompt:** Asked how to make "Actually, my full name is X" correctly
overwrite a previously captured name rather than appending or confusing
the two.

**Accepted:** The approach of always overwriting non-null extracted
fields onto state (latest value wins), with no separate "correction mode"
needed — the same update path handles first-time answers and corrections.

**Changed:** For list fields (children, specific_gifts) I made corrections
*replace* the whole list rather than append, so restating "my children
are Amit, Riya and Kabir" doesn't duplicate earlier entries.

## 4. Error handling
**Prompt:** Asked what failure modes the assignment expects to be
handled (LLM unavailable, malformed JSON, missing key).

**Accepted:** The three cases named in the brief's request. Implemented
each as: fallback extractor on any API failure; Pydantic validation
rejection (state left untouched, safe "please rephrase" reply) on
malformed output; and the missing-key case being a non-issue by design
since the fallback path handles it.

## 5. What I verified myself (not just accepted from the AI)
Since I could not run a live OpenAI call or a full `npm install` in the
time available, I independently unit-tested the fallback extractor's
regex logic against the assignment's own example sentences (name,
multi-field, correction, "I don't know", yes/no, executor phrasing)
before finalizing the code, and fixed the bug described in section 2.
