# Agent smoke test: compose-up output composition

**Purpose.** Verify that the compose-up contract surfaced by the suite MCP
servers (`agent_protocol`), the recipe `COMPOSITION:` block, and
`morphic-recipes/AGENTS.md` actually changes *agent behavior* — i.e. that an
agent picking up a scoped task **starts from the minimal core and adds only the
output layers the target needs**, instead of running the maximal recipe verbatim.

This is the regression guard for the 2026-06 CAT-ATAC benchmark mistake: an agent
ran the full MorPhiC multiome recipe (Velocyto + GEX BAM + Y/noY) against a
matrices+peaks target that needed none of it, wasting compute and distorting the
comparison against Cell Ranger ARC `--no-bam`.

It is the output-composition complement to `agent_protocol_provenance_smoke.md`
(which guards *parameter values*); this one guards *which output layers*.

## Part 1 — deterministic recipe-mechanism check (no agent)

Asserts the recipe's `--profile` resolution and `--dry-run` behave correctly:

- `--profile matrices-peaks --dry-run` resolves to `emit_velocyto=0`,
  `emit_gex_bam=0`, `stop_after_local_mex=1`, and the composed command contains
  `--soloFeatures GeneFull` (no `Velocyto`) and `--outSAMtype None`.
- `--profile full --dry-run` (default) contains `--soloFeatures GeneFull Velocyto`
  and `--outSAMtype BAM Unsorted` and lists all four add-ons.
- `run_multiome_minimal.sh` is equivalent to `--profile matrices-peaks` (it just
  sets that profile on the one engine — the floor and full recipe cannot drift).

Runs only when the CAT-ATAC dry-run inputs are present on the host; skips
gracefully otherwise (so it never fails CI on hosts without the fixtures).

## Part 1b — end-to-end execution on a tiny fixture (catches runtime errors)

A dry-run text check is **not sufficient** — it never invokes STAR, so it cannot
catch parameter incompatibilities (the lean profile's `--outSAMtype None` is
incompatible with the `GX`/`GN` SAM tags, which a dry-run happily prints). Part 1b
therefore *actually executes* the minimal profile end-to-end on a tiny downsampled
fixture (~1–2 min) and asserts the run completes and emits the CORE
(GeneFull raw MEX + ATAC `narrowPeak`) with **no** Velocyto dir and **no** GEX BAM.

The fixture is generated (not committed) with
`tests/make_multiome_tiny_fixture.sh` (downsamples the first N read-pairs of a
source multiome dataset into `tests/fixtures/multiome_tiny/`). Part 1b runs only
when that fixture **and** the references are present, and skips with a "generate
it first" hint otherwise — so it stays optional but is the fast end-to-end smoke
an agent can reach for before committing to a full ~35-min run.

## Part 2 — agent-driven scoping check (needs AGENT_CMD)

Task given to a fresh agent: "produce the command to process CAT-ATAC
(GSE288996, K562+iPSC multiome) for a Cell Ranger ARC-style benchmark — the
deliverable is GEX matrices + ATAC fragments + re-called MACS peaks, and the
comparator (CR-ARC) ran `--no-bam` and computed no RNA velocity." Entry points
given: the recipe + its COMPOSITION block, `morphic-recipes/AGENTS.md`, and the
MCP `agent_protocol`. The agent is **not** told to compose down — the contract
must lead it there.

**PASS** iff the produced command takes the minimal/lean path — any of
`--profile matrices-peaks`, `run_multiome_minimal.sh`, or
(`--no-velocyto` AND `--no-gex-bam`) — **and** does NOT use `--profile full`;
**and** the rationale references composing to the target / the COMPOSITION block /
the comparator not needing Velocyto or a BAM.

**FAIL** if the agent runs the full recipe verbatim (emitting Velocyto + GEX BAM)
against this matrices+peaks target.

## How to run

```bash
# Part 1 always runs (skips if fixtures absent). Part 2 runs only with AGENT_CMD,
# which must read a prompt on stdin and print the agent's answer on stdout.
AGENT_CMD='claude -p' tests/run_agent_protocol_composition_smoke.sh
```

With `AGENT_CMD` unset the harness runs Part 1 and prints Part 2's prompt + pass
criteria (documentation mode), so it never fails CI spuriously.

## Validation record
- 2026-06-11 (Part 1b added): Full smoke ALL PASS. Part 1b executed the minimal
  profile end-to-end on a 300k-read fixture in ~3.5 min → GeneFull raw MEX +
  2,645 ATAC peaks, no Velocyto dir, no GEX BAM. This is the check that would
  have caught the `--outSAMtype None`/`GX`-tag runtime error that the dry-run
  text check (and the sub-agents) missed.
- 2026-06-11: Part 1 PASS (profiles resolve correctly; `run_multiome_minimal.sh`
  == `--profile matrices-peaks` floor). Part 2 ran via two sub-agents (Haiku +
  Sonnet). **Both PASS.** Both chose `run_multiome_minimal.sh` (matrices-peaks),
  explicitly dropping Velocyto + GEX BAM + remote downstream, citing the
  COMPOSITION block / AGENTS.md "Compose to the target". The Sonnet agent also
  pulled `--threads 16 --chromap-low-mem --chromap-macs3-frag-low-mem` from the
  `jax_multiome01` provenance oracle and previewed with `--dry-run` — i.e. it
  composed BOTH contracts (compose-up + provenance-first) correctly. Neither
  agent ran the full recipe.
