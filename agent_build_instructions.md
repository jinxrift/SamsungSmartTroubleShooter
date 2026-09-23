# Agent-Driven Build Instructions: Smart Guided Troubleshooting Engine

Execute these steps **in order**. Each step has a concrete deliverable and an explicit exit check. Do not proceed to the next step until the exit check passes. Treat `samples/`, `schema.py`, `deeplinks.json`, `queries.json`, and `siis_responses.json` as ground truth — never invent data outside them.

---

## Step 1 — Environment & Schema Bootstrap
1. Initialize repo structure: `/src`, `/tests`, `/data`, `/config`.
2. Copy `schema.py` into `/src/schema.py` verbatim — do not modify field names or types.
3. Write a script `validate_schema.py` that loads each `samples/*.json` file and validates it against `ContextDeeplinkResponse`.
4. Run it against all 5 sample pairs.

**Exit check:** All 5 samples parse without Pydantic errors. If any fail, stop and report which field/rule broke — do not proceed.

---

## Step 2 — Data Audit
1. Load `deeplinks.json`. Report: total count, entries missing `description`, duplicate `deeplink` values, any non-`bixby://masked/act/...` URIs.
2. Load `queries.json` and `siis_responses.json`. Report coverage by domain (Battery, Display, Camera, Performance) and flag any domain with near-zero reference data.
3. Confirm `bixby://dummy_positive` exists as a literal entry point (not matched via catalog search).

**Exit check:** Produce a short audit report (`data_audit.md`) with these counts. Human reviews before continuing.

---

## Step 3 — Structure Extraction (Stage 1)
1. Write the LLM prompt/parser (`extract.py`) that takes `{query, siis_response}` and returns a raw `Goal`-shaped object.
2. Enforce in the prompt (not just hope): exact `goal` syntax, title word count, description word count + "It will" prefix, category enum values.
3. Build `validators.py` with **programmatic** (non-LLM) checks for every rule in §4.1 of the spec: goal regex, title length, description length/prefix, category enum, one-action-one-screen.
4. Add a URL-scrubbing regex pass (`http`, `https`, `www.`, markdown link syntax) applied to every string field before it leaves this stage.

**Exit check:** Run extraction on all 5 `samples/` inputs. Diff structural shape (not exact wording) against expected outputs. All validators must pass on all 5. Any failure = fix the prompt/validator, re-run, do not skip.

---

## Step 4 — Deeplink Indexing & Matching
1. Build two indexes over `deeplinks.json`, both keyed on `description` + `message` + `qna_description` text (never the URI string):
   - BM25 keyword index
   - Dense embedding index
2. Write `match_deeplink.py`: given an extracted step group, retrieve top-K candidates from both indexes, merge/rerank, resolve parent-menu vs. exact-screen ambiguity in favor of the most specific screen.
3. Implement fallback: if no catalog match clears a confidence threshold, attach `bixby://dummy_positive` with a generated description/message instead of hallucinating a URI.
4. Write 10 adversarial test cases (by hand) covering: parent-menu confusion, multi-step-same-screen bundling, no-match scenarios.

**Exit check:** All 5 samples resolve to their documented deeplinks exactly (verbatim URI match). All 10 adversarial cases resolve as expected or correctly fall back to `dummy_positive`.

---

## Step 5 — Action Ordering
1. Write `order_actions.py`: within an extracted Goal, group steps so **one action = one physical screen** (merge same-screen steps, never split one screen across two actions).
2. Sequence actions: `auto` → `manual` → `critical` (least disruptive first, destructive/irreversible last).
3. Unit test against the doc's stated pitfall: creating a separate action per tap, and bundling unrelated screens into one action.

**Exit check:** Ordering on all 5 samples matches expected action sequence and grouping exactly.

---

## Step 6 — Query Enrichment & Semantic Cache
1. Write `enrich_query.py`: normalize colloquial input to a canonical technical query string; generate 8–10 paraphrase variations across formal/casual/keyword-only/typo-inclusive registers (this is also a required `query_variations` output field).
2. Build a semantic cache: key on embedding similarity clusters, not exact strings. Store fully validated `Goal` payloads on write.
3. Implement cache-hit path: embed incoming query, similarity search, return cached payload with `cache_hit: true` if above threshold.
4. Tune the similarity threshold against a labeled paraphrase test set until the same-intent hit rate is ≥80% with no false-positive collisions between distinct issues.

**Exit check:** On a held-out paraphrase set (generate ~50 variants across the 4 domains), cache hit rate ≥80%, and manually spot-check 10 hits for correctness (not just similarity).

---

## Step 7 — API Assembly
1. Implement `POST /v1/troubleshoot`:
   - Input: `{query, siis_response?}`
   - If `siis_response` omitted, do cache lookup only (no cold-path LLM call).
   - On cache miss, run Steps 3→5 pipeline, validate, write to cache, return.
2. Implement `GET /health`: return `{"status": "ok"}` only once model connections, cache, and vector indexes are fully warmed — not before.
3. Implement error boundaries: return `contexts: []` with `fallback: "no_match"` when no viable solution exists in source data. Never fabricate a plan.
4. Add a final output-layer sanitizer: strip markdown code fences / conversational preamble from any LLM-touched string before serialization — pure JSON only.

**Exit check:** Send all 5 sample queries through the live endpoint; response bodies match `results.jsonl` structure and pass schema validation. Cold-start sequence tested (health returns non-200 until warm, then 200).

---

## Step 8 — Latency & Cost Instrumentation
1. Add timing instrumentation around cache-hit and cold-path branches; log to `meta.latency_ms`.
2. Add token/cost tracking per request (`meta.cost_usd`), even if $0.00 on cache hits.
3. Run N≥30 requests per path (cache-hit-exact, cache-hit-paraphrase, cold-query) and record P50/P95.

**Exit check:** Cache-hit paths P95 ≤ 300ms. Cold path P95 ≤ 8000ms. If missed, profile and optimize before moving on — do not silently relax the target.

---

## Step 9 — Full Evaluation Pass
1. Fill in `metrics.md` (Appendix C template) with real measured values across all 5 sections: schema/rule compliance, accuracy benchmarks, latency, cost/cache efficacy, ablation analysis.
2. Run the architectural ablation: implement and benchmark (a) full-LLM baseline, (b) hybrid BM25+dense (your Step 4 build), (c) pure rules-based matching. Compare step accuracy, latency, cost.
3. Re-run all adversarial tests from Steps 3–4 as a regression suite.
4. Document known edge cases and gaps discovered (multi-intent complaints, domain gaps, hierarchy quirks) in the metrics template's §6.

**Exit check:** All automated gates green (0 URL leaks, ≥99% schema-valid lines, ≥95% rule compliance, ≥80% cache hit rate on unseen paraphrases). Ablation table has a clear winner with a one-paragraph rationale.

---

## Step 10 — Regression Lock-In
1. Freeze the 5 provided samples + your constructed held-out/adversarial sets into a permanent test suite that runs on every change.
2. Add a provenance check to CI: assert every deeplink in any output exists verbatim in `deeplinks.json` (or is the literal `dummy_positive` fallback) — fail the build otherwise.
3. Tag this as the release candidate build.

**Exit check:** CI green on a clean checkout; no manual steps required to reproduce Steps 1–9 results.

---

### Non-negotiables to enforce at every step (not just their own step)
- Never let an LLM call be the last line of defense for a schema rule — always follow with a programmatic validator.
- Never match deeplinks against the URI string itself.
- Never emit a plan not traceable to source text/catalog.
- Never return non-JSON (fences, preamble) from the API.
