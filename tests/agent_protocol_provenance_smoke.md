# Agent smoke test: provenance-first protocol

**Purpose.** Verify that the `agent_protocol` surfaced by the suite MCP servers
(and the recipe/AGENTS guidance) actually changes *agent behavior* — i.e. that an
agent picking up a multiome run **consults `morphic-provenance` for known-good
parameters instead of inventing them**. This is the regression guard for the
2026-06 multiome OOM (an agent ran `--threads 32 --chromap-threads 32` with no
low-mem flags, vs the verified `16+16 + --chromap-low-mem --chromap-macs3-frag-low-mem`).

This is an **agent-driven** test: it spawns a fresh LLM sub-agent (e.g. Sonnet or
Haiku), gives it a realistic task and the MCP/recipe/provenance entry points, and
checks the command it produces. It does **not** tell the agent to consult
provenance — the protocol must lead it there on its own.

## Fixtures (entry points given to the agent)
- MCP discovery guidance: the `agent_protocol` field in
  `STAR-suite/mcp_server/config.yaml` (returned by `list_workflows` /
  `describe_workflow`).
- Recipe: `morphic-recipes/scripts/run_star_multiome_lane_smoke.sh`.
- Repos: `/mnt/pikachu/{STAR-suite,morphic-recipes,morphic-provenance}`.

## Trial A — existing provenance (must reproduce the known-good config)
Task: "produce the command to reproduce the MorPhiC production multiome run for
project `jax_multiome01`."
**PASS** iff the produced command contains all of:
`--threads 16`, `--chromap-threads 16`, `--chromap-low-mem`,
`--chromap-macs3-frag-low-mem`; **and** does NOT contain `--threads 32`; **and**
the rationale names `morphic-provenance/runs/jax_multiome01` as the source.

## Trial B — no provenance for this dataset (must use the closest run, not invent)
Task: "produce the command to process a NEW dataset (e.g. CAT-ATAC, GSE288996,
K562+iPSC) for the first time; machine has 32 cores / 125 GB." There is no
provenance run for this dataset.
**PASS** iff the produced command contains `--threads 16` + `--chromap-low-mem`
(+`--chromap-macs3-frag-low-mem`); **and** does NOT contain `--threads 32`;
**and** the rationale states there is no prior run and the params come from the
**closest** known-good run (e.g. `jax_multiome01`).

## How to run
`run_agent_protocol_provenance_smoke.sh` drives both trials through an agent CLI:

```bash
# AGENT_CMD must read a prompt on stdin and print the agent's answer on stdout.
AGENT_CMD='claude -p' tests/run_agent_protocol_provenance_smoke.sh
```

If `AGENT_CMD` is unset the harness prints the prompts + pass criteria and exits 0
(documentation mode), so it never fails CI spuriously on hosts without an agent.

## Validation record
- 2026-06-10: ran via two Sonnet sub-agents. **Both PASS.** Trial A produced
  `16+16 + low-mem`, citing `runs/jax_multiome01/.../production_launch.argv.json`.
  Trial B (CAT-ATAC, no provenance) produced `16+16 + low-mem` from the closest
  run, explicitly noting no prior run existed. Neither invented `32+32`.
