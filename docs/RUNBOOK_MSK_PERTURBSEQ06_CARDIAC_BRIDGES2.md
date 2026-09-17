# MSK Perturb-seq 06 Cardiac on Bridges-2

Date: 2026-09-17
Status: two-node pilot and Pikachu control passed; full production not submitted

## Scope

Process the completed MSK Perturb-seq 06 Cardiac delivery on Bridges-2 with
STAR Suite v1.9.4. The workflow follows the MSK 30polyKO CR-compatible surface
while adapting to this delivery's eight cardiac-progenitor captures and its
GEX plus PolyIII guide design.

This runbook deliberately does not use any `zshard-*` code, reference, input,
scratch, or output path. It also does not transcode FASTQ files. Ordinary gzip
inputs are copied byte-for-byte to node-local storage and read through STAR
Suite's native gzip path.

## Pinned Inputs

| Item | Path | Contract |
| --- | --- | --- |
| Cardiac FASTQs | `/ocean/projects/bio230034p/lhung2/incoming/MSK_Perturbseq_20260910/MSK_Perturbseq06_Cardiac_20260910` | 1,020 FASTQs; provider MD5 file `cp.checksums.md5` |
| Corrected manifests | provenance run `msk_perturbseq06_cardiac/20260917T115903Z_bridges2_v194_pilot/inputs` | Corrected library identity and TRU/NXT routing |
| STAR Suite | v1.9.4, commit `1c9ddb9a5a2a3e62748e8e4ef28e553582affeed` | v1.9.5 is not approved for this run |
| GEX reference | `/ocean/projects/bio230034p/shared/processing/references/GRCh38-2024-A-star-msk30` | Exact MSK-30 GRCh38 2024-A / GENCODE v44 index |
| Run root | `/ocean/projects/bio230034p/lhung2/msk-perturbseq06-cardiac-20260917` | Pilot, production, logs, and staged provenance |

## Reference Audit

The pre-existing Ocean index at
`/ocean/projects/bio230034p/shared/processing/genome` is a coherent older
2020-A-style reference, not a damaged index. It has the same 194 chromosome
names, lengths, and coordinate starts as the MSK-30 index, but a different
annotation universe:

| Index | Genes | Transcripts | Use |
| --- | ---: | ---: | --- |
| Existing Ocean `/shared/processing/genome` | 36,601 | 199,138 | 2020-A-era workflows; reject for this run |
| MSK-30 `/storage/autoindex_110_44/bulk_index` | 38,606 | 226,005 | 2024-A / GENCODE v44; required here |

The older reference was used intentionally in CAT-ATAC work that matched a
Cell Ranger ARC 2020-A comparator. It was not used for MSK-30 or the current
PPARG controls; their rendered commands use the 2024-A index. The difference
therefore has a benign provenance explanation, but the indexes are not
interchangeable for Cardiac production.

The Cardiac preflight checks the 2024-A gene/transcript counts, core file sizes,
and pinned metadata checksums before STAR starts.

Bridges-2 builds v1.9.4 with `WITH_CHROMAP=0`. Ocean has no non-zshard
Chromap development installation, and a Pikachu-linked binary is not ABI
portable to Bridges-2. This is an explicit scRNA-only portable build: neither
the pilot nor Cardiac production invokes Chromap. The Pikachu host control uses
the normal `WITH_CHROMAP=1` build, and the comparison records that compile-mode
difference while keeping all GEX/Solo/feature inputs and arguments matched.
The v1.9.4 source archive required a portable-build workaround for bundled
HTSlib headers and duplicate integrated BGZF reader objects. The durable build
fix is STAR Suite commit `99a6536`; the accepted pilot itself remains pinned to
v1.9.4 commit `1c9ddb9` plus the recorded build-only workaround.

## Captures

All captures are H1 inducible dCas9-KRAB cardiac progenitors at day 5.5. No
expected subtype proportions are supplied in the provider workbook.

| Capture | GEX library | Guide library | FASTQs |
| --- | --- | --- | ---: |
| `CP_A1` | `CP_A1_mRNA` | `CP_A1_gRNA` | 124 |
| `CP_A2` | `CP_A2_mRNA` | `CP_A2_gRNA` | 124 |
| `CP_A3` | `CP_A3_mRNA` | `CP_A3_gRNA` | 124 |
| `CP_B1` | `CP_B1_mRNA` | `CP_B1_gRNA` | 124 |
| `CP_B2` | `CP_B2_mRNA` | `CP_B2_gRNA` | 124 |
| `CP_B3` | `CP_B3_mRNA` | `CP_B3_gRNA` | 124 |
| `CP_R1` | `CP_R1_mRNA` | `CP_R1_gRNA` | 152 |
| `CP_R2` | `CP_R2_mRNA` | `CP_R2_gRNA` | 124 |

Only R1/R2 files enter STAR. I1/I2 files remain inventoried but are not staged
to node-local storage.

The CP_R1 guide pair has provider basenames beginning `CP_gRNA_` rather than
`CP_R1_gRNA_`. The corrected file manifest maps that pair to `CP_R1_gRNA` and
is the authoritative source for its logical capture identity.

CP_R2 guide basenames begin `CP_R2_`, so they contain a non-terminal `_R2_`
token in addition to the true terminal `_R1_`/`_R2_` read role. Node-local
staging rewrites only that prefix to `CPR2_` and records the reversible mapping
in `STAGING_MAP.tsv`. Provider files are never renamed or modified.

## Chemistry And Feature Layout

- Read layout: I1 10 bp, I2 10 bp, R1 29 bp, R2 89 bp.
- GEX: February-2018 3M TRU input and TRU output.
- PolyIII guide capture: February-2018 3M NXT input, normalized to canonical
  TRU at the integrated MEX boundary by STAR Suite. The assignment-layer
  `cr_assign/.../PolyIII` MEX remains NXT by design; the release-facing
  `outs/*feature_bc_matrix` surfaces are TRU.
- Guide design: 15,656 unique 20 bp guides targeting 2,324 genes.
- Feature pattern: `AAGCAGTGGTATCAACGCAGAGTACATGGG(BC)` in guide R2.
- No LARRY library is present in this delivery.

The September 4 audit already established the whitelist families from real
Cardiac reads: GEX had a 0.949140 exact TRU hit rate and guides had a 0.833595
exact NXT hit rate. Do not repeat that audit as the pilot. The remaining pilot
question is the Cardiac guide-R2 feature layout plus the integrated GEX/guide
join and TRU-normalized output namespace.

## Phase 1: Inventory

Run the provenance manifest builder on Bridges-2. It requires all 1,020
expected basenames, validates sizes where the earlier manifest recorded them,
joins the provider MD5 file, verifies R1/R2 pairing, and emits an execution
manifest for all eight captures.

```bash
bash provenance/commands/prepare_inputs.sh
```

Acceptance gates:

- Exactly 1,020 expected and observed FASTQs, with no extras or missing files.
- Exactly eight logical captures, each with one mRNA and one gRNA library.
- Equal R1/R2 counts within every library.
- GEX routes TRU to TRU; guides route NXT to TRU.
- Provider checksum coverage is complete.

## Phase 2: Two-Capture, Two-Node Pilot

Submit the build and the dependent pilot through the rendered submitter:

```bash
bash provenance/commands/submit_pilot.sh
```

The pilot uses two one-element submissions of the same Slurm array script,
covering `CP_R1` and `CP_R2`. The submitter selects two distinct idle
`RM-shared` nodes and pins one task to each. Each capture uses one GEX pair and
one guide pair, capped at 250,000 read pairs. A dependent gather job requires
two distinct node names and validates both result trees together. Pilot tasks
emit GeneFull and CR-compatible guide outputs only; no BAM or Velocyto is
requested in this boundary test.

On `RM-shared`, each pilot task reserves 64 CPUs and 120 GB to satisfy the
2-GB-per-allocated-CPU limit; STAR uses 32 threads. The prepared production
tasks reserve 64 CPUs and 120 GB, STAR uses 64 threads, and `%1` array
concurrency prevents two full captures from sharing a node.

Each task's four gzip files are copied unchanged to `$LOCAL` by four concurrent
copy workers. Each local copy is checked against the provider MD5 and with `gzip -t`.
STAR receives no `--readFilesCommand`; `--readFilesBgzfMode auto` and
`--crAssignBgzfMode auto` select native gzip reading without format conversion.

Run the same two captures sequentially on Pikachu as a host control:

```bash
bash provenance/commands/run_pikachu_control.sh
```

The Pikachu control uses the same eight FASTQs, read cap, v1.9.4 source commit,
2024-A index, and STAR parameters. It does not use the active STAR Suite
checkout. It performs a clean build from the pinned v1.9.4 source archive.
The comparison records the intentional Chromap compile-mode difference.

Pilot acceptance requires:

- STAR exits successfully and writes `Log.final.out`.
- GeneFull raw and filtered MEX outputs are readable.
- CRISPR output contains all 15,656 reference features.
- At least one guide read is assigned.
- Exported cell barcodes are valid February-2018 TRU barcodes.
- Both validation scripts write `PILOT_VALIDATION.json` with `status=PASS`.
- The Bridges gather report records two distinct compute nodes.
- Pikachu and Bridges agree on matrix dimensions and UMI totals for both captures.
- Assignment-layer guide MEX files agree after canonicalizing barcode column
  order; integrated raw and filtered MEX files are byte-identical.

### Accepted Pilot

The accepted Bridges jobs were build `46246773`, CP_R1 `46246783` on `r039`,
CP_R2 `46246784` on `r067`, and gather `46246785` on `r055`. Both per-capture
validators, the two-node gather, and the Pikachu-versus-Bridges comparison
report `PASS`.

| Capture | Raw GeneFull UMIs | Filtered GeneFull UMIs | Guide UMIs | Combined raw UMIs | Combined filtered UMIs |
| --- | ---: | ---: | ---: | ---: | ---: |
| `CP_R1` | 150,628 | 127,431 | 108,271 | 233,824 | 203,346 |
| `CP_R2` | 141,421 | 120,022 | 134,618 | 220,950 | 187,641 |

These values and all matrix dimensions are identical on Pikachu and Bridges-2.
Raw guide MEX byte hashes differ because parallel assignment emitted barcode
columns in a different order; sorted barcode sets and barcode-keyed count
digests are identical. Production remains unsubmitted pending explicit review.

## Phase 3: Production Array

Do not submit production until the pilot passes and its report is reviewed.
The prepared command is:

```bash
sbatch provenance/commands/run_cardiac_production_array.sbatch
```

The array covers eight captures with `%1` concurrency. Each task uses 64 cores
on `RM-shared`, copies only its R1/R2 files to `$LOCAL` with eight concurrent
workers, verifies provider MD5 values and gzip integrity, and runs one integrated
STAR invocation. Output is copied to Ocean only after successful completion.

Production adds the layers required by the MSK handoff:

- `GeneFull` and `Velocyto`.
- CR-compatible guide matrices and calls.
- Unsorted BAM with CB/UB tags.
- No Y-chromosome removal.
- No FASTQ transcoding and no derived FASTQ output.

Core assignment settings follow MSK-30: `EmptyDrops_CR`, `crMinUmi=2`, Hamming
distance 1, NXT guide input, and TRU canonical output. The patterned 20 bp guide
reference uses automatic pattern-derived feature offset detection rather than
the old MSK-30 short-barcode offset 0.

## Phase 4: Downstream

After all eight upstream tasks pass:

1. Run the standard GeneFull/Velocyto H5AD assembly.
2. Run CellBender only on a CUDA GPU host; verify both `--cellbender-gpu` and
   CellBender `--cuda`, then confirm GPU use with `nvidia-smi`.
3. Apply adaptive MADS mitochondrial filtering.
4. Add STAR Suite guide assignments and Scimilarity labels/sublabels.
5. Do not add provider `.rds` labels and do not invent LARRY fields.
6. Validate final H5AD layers, observations, QC plots, and barcode namespace
   before release packaging.

## Provenance

Rendered scripts, pinned manifests, reference audit, submission records, and
pilot results belong under:

```text
morphic-provenance/runs/msk_perturbseq06_cardiac/
  20260917T115903Z_bridges2_v194_pilot/
```

The recipe documents the reusable method. The provenance run is authoritative
for the exact paths, checksums, Slurm resources, and commands used here.
