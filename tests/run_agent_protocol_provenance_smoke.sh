#!/usr/bin/env bash
# Agent smoke test for the provenance-first protocol.
# Spawns a fresh LLM agent per trial and checks the command it produces.
# See agent_protocol_provenance_smoke.md for the full spec.
#
# AGENT_CMD must read a prompt on stdin and print the agent's answer on stdout,
# e.g.  AGENT_CMD='claude -p'  tests/run_agent_protocol_provenance_smoke.sh
# With AGENT_CMD unset the harness runs in documentation mode (prints prompts +
# criteria, exits 0) so it never fails CI on hosts without an agent runner.
set -uo pipefail

ENTRY='Entry points (read whatever you need; do NOT run anything):
- MCP discovery guidance is the `agent_protocol` field in /mnt/pikachu/STAR-suite/mcp_server/config.yaml
- Recipe: /mnt/pikachu/morphic-recipes/scripts/run_star_multiome_lane_smoke.sh
- Repos: /mnt/pikachu/STAR-suite , /mnt/pikachu/morphic-recipes , /mnt/pikachu/morphic-provenance
Output (1) THE COMMAND with concrete --threads/--chromap-threads/low-mem flags and (2) one-line RATIONALE naming your source.'

PROMPT_A="You are an automation agent on host pikachu. Task: produce the exact command to reproduce the MorPhiC production 10x-multiome run for project jax_multiome01. ${ENTRY}"
PROMPT_B="You are an automation agent on host pikachu (32 cores, 125 GB RAM). Task: produce the command to process a NEW 10x-multiome dataset for the first time — CAT-ATAC, GSE288996 (K562+iPSC). There is no prior production run for this dataset. ${ENTRY}"

check() { # name, output, must-contain-regex..., must-NOT-contain "--threads 32"
  local name="$1" out="$2"; shift 2
  local ok=1
  for re in "$@"; do grep -qiE "$re" <<<"$out" || { echo "  FAIL[$name]: missing /$re/"; ok=0; }; done
  if grep -qE '\-\-threads[ =]*32' <<<"$out"; then echo "  FAIL[$name]: invented --threads 32"; ok=0; fi
  [[ $ok -eq 1 ]] && echo "  PASS[$name]"; return $((1-ok))
}

if [[ -z "${AGENT_CMD:-}" ]]; then
  echo "DOC MODE (AGENT_CMD unset). Trials:"; echo "--- A ---"; echo "$PROMPT_A"; echo "--- B ---"; echo "$PROMPT_B"
  echo "PASS-A: --threads 16 & --chromap-low-mem & --chromap-macs3-frag-low-mem & cites runs/jax_multiome01 & no --threads 32"
  echo "PASS-B: --threads 16 & --chromap-low-mem & (no prior / closest run) & no --threads 32"
  exit 0
fi

rc=0
echo "== Trial A: existing provenance =="
OUT_A="$(printf '%s' "$PROMPT_A" | ${AGENT_CMD} 2>/dev/null)"
check A "$OUT_A" '\-\-threads[ =]*16' 'chromap-low-mem' 'chromap-macs3-frag-low-mem' 'jax_multiome01' || rc=1
echo "== Trial B: no provenance for this dataset =="
OUT_B="$(printf '%s' "$PROMPT_B" | ${AGENT_CMD} 2>/dev/null)"
check B "$OUT_B" '\-\-threads[ =]*16' 'chromap-low-mem' 'closest|no prior|jax_multiome01' || rc=1

echo; [[ $rc -eq 0 ]] && echo "ALL PASS" || echo "FAILURES (see above)"
exit $rc
