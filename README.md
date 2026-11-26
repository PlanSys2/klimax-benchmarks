# Klimax benchmarks

Hierarchical planning problems in HDDL 2.1 with what the benchmarks of the HTN tracks of the IPC
do not have: time. Generators with a seed and a size, the problems they give, a harness that
runs any planner of [Unified Planning](https://github.com/aiplan4eu/unified-planning) on them
with the same limits, and the results.

They are made to measure [Klimax](https://github.com/PlanSys2/klimax) against other planners,
and are not written for it: every problem is built with Unified Planning, so that every engine
that takes temporal hierarchical problems gets the same one, and is also given as HDDL files.

> **Status**: a first set, with time. The other levels (numbers, constraints on the states of
> the plan) and more families are to come.

## Families

Forty problems: four families of ten, of growing size (`p01` to `p10`; the seed is the size).
Each has durative actions and an initial task network that does not order its tasks, so that
a plan may run actions at once.

| Family | What it is | What it has |
|---|---|---|
| `transport` | Trucks deliver packages over roads of some length | durations from a function; a recursive task (`get-to`) |
| `satellite` | A satellite takes images of sites that are visible only for a while | timed initial literals; conditions over all |
| `workshop` | Pieces go through two machines in order; a machine does one piece at a time | a shared resource; actions of different tasks at once |
| `cellar` | Fuses are mended by the light of matches that burn for a while | actions that must overlap: no plan with one action after another |

[FEATURES.md](FEATURES.md) says which features of HDDL 2.1 each family uses.

## Layout

- `generators/temporal.py`: the generators. `transport(size, seed)` and the others return a
  `HierarchicalProblem` of Unified Planning; run as a script it writes every problem as HDDL.
- `temporal/<family>/domain-pNN.hddl` and `pNN.hddl`: the problems, as Unified Planning writes
  them in HDDL (a domain file per problem: only its name changes within a family).
- `tools/run.py` and `tools/one.py`: the harness.
- `results/`: what was measured, as CSV.

## Running it

With Unified Planning, [up-klimax](https://github.com/PlanSys2/up-klimax) (its validator
checks the plans of every planner) and the engines to measure installed:

```
python generators/temporal.py temporal                 # write the problems again
python tools/run.py --engines klimax,aries --timeout 30 --jobs 10 --cpus 6-15 --out out.csv
```

Each run is one process on one core, with 8 GB of address space and the time limit for the
whole process: it is stopped then, whatever the planner does. A plan counts if it is out in
time and the validator accepts it. The CSV has the status (`solved`, `invalid`, `timeout`,
`failed:...`), the seconds, the actions of the plan and when it ends (the makespan).

On the HDDL files, Klimax runs without Unified Planning:

```
klimax temporal/cellar/domain-p03.hddl temporal/cellar/p03.hddl --timeline
```

## Results

At 30 s per problem, one core and 8 GB (`results/2026-11-26-temporal.csv`; Klimax at
[`b93e6de`](https://github.com/PlanSys2/klimax/commit/b93e6de), Aries as `up-aries` 0.5.0):

| Family | Klimax | Aries |
|---|---|---|
| `transport` | 10 | 0 |
| `satellite` | 10 | 10 |
| `workshop` | 10 | 10 |
| `cellar` | 10 | 10 |
| **Total** | **40 of 40** | **30 of 40** |

- In `transport` Aries runs out of time in five problems and gives a plan in the five
  smallest, which the validator rejects: each `drive` lasts 0.1 more than the problem says
  (the length of its road). They are counted as not solved.
- In the thirty that both solve, the plans of Klimax end at 3218 in all and those of Aries at
  3314.
- No verifier of temporal hierarchical plans existed: the plans of every planner are checked
  by Klimax's, which follows the plan with the evaluator of
  [Kairos](https://github.com/PlanSys2/kairos)' validator and shares no code with Klimax's
  searches. A second, independent one is welcome.

## License

Apache-2.0.
