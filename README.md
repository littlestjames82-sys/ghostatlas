# GhostAtlas

**See how a codebase fits together, and where to start reading it.**

GhostSlice answers an agent's question: what should I read for this
task. GhostAtlas answers a person's question: how does this project
fit together, what matters in it, and where do I start.

It is built entirely on GhostSlice data (scanner, import graph and
call graph, entry-point signals, token estimator). It adds no second
size metric, no runtime tracing, and no model-written prose: an
Atlas is a finished, shareable artifact a non-operator can read
without running anything.

By Ghost Developer Studio. MIT licensed (core). **Zero
dependencies** (Python standard library only), **local-first**: no
network calls, no telemetry, your code never leaves the machine.

Position in the Ghost stack: GhostSlice governs what an agent
*reads*, GhostAtlas orients the *human* joining, reviewing, or
evaluating the project. Agent Seatbelt governs what an agent *does*.

> Status: v0.1 in build (Oct 2026). This README describes the
> v0.1 contract in `PLAN.md`. The verification harness under
> `tests/` is in place; see `REPORT_B.md` in this repo for the
> honest state of the test run against the core as it lands.

## Install

No install needed to try it from a checkout (GhostSlice must be
importable; from a sibling checkout the tools find each other as
documented in the plan):

```bash
cd ghostatlas
PYTHONPATH=src python3 -m ghostatlas --help
```

Requires Python 3.10 or newer, and a GhostSlice checkout or
install (GhostAtlas reuses its scanner, graph, and estimator
rather than reimplementing them).

## Quickstart

From any project you want a map of:

```bash
ghostatlas build ~/my-project -o ~/my-project-atlas.html
```

That one run produces:

- `atlas.html`, a single self-contained file (static SVG/HTML map,
  heat toggles for estimated token cost and caller count, no
  external assets, opens offline), and
- `ATLAS.md`, the architecture brief from the same run: layout,
  entry points, a start-here reading order with a factual reason
  per pick, main flows from the call graph (capped, labelled as
  sampled from static analysis), data/config hotspots, test
  layout, dead zones framed as "worth asking about", and the
  known GhostSlice lint warnings with their explanations.

For a buyer, partner, or client hand-over, reorder the same
brief for diligence:

```bash
ghostatlas build ~/my-project -o ~/atlas.html --audience diligence
```

Diligence mode leads with size and shape, test presence, the
secrets guard result (counts and types only, never values),
the dependency surface from manifests, licence files found, and
history span from git, and it includes an explicit box stating
what was checked and what was not checked. It is an orientation
aid, not an audit opinion.

## Honest labels

- Token counts in an Atlas are GhostSlice **estimates**, printed
  with the same estimator version a `ghostslice scan` reports.
  A number in `ATLAS.md` must always equal the same-run scan
  number; the test suite checks exactly that.
- Graph edges for Python come from full analysis. Other languages
  are import-level (parser-lite) and the map labels them as such,
  on the map itself.
- Module descriptions are extractive only: names, paths, and
  first docstring lines. A module with no docstring is shown with
  no description rather than an invented one.
- Dead zones are observations for a human to judge ("worth
  asking about"), never delete directives.

## Configuration

Atlas reads the project's `.ghostslice.json` and adds an `atlas`
section (title, audience notes, hidden paths). Unknown keys in
the section fail loudly, the same discipline as GhostSlice
profiles, rather than being silently ignored.

## Tests

```bash
PYTHONPATH=src python3 -m pytest tests -q
```

The suite pins a ground-truth fixture (known entry point, known
graph edges, known dead file), checks the consistency bar
(ATLAS.md numbers vs a same-run GhostSlice scan), and checks the
offline bar (the generated HTML has no network-capable
constructs and never contains a planted secret-shaped canary
from the fixture).

## Layout (v0.1)

```
PLAN.md        the v0.1 plan this build follows
src/ghostatlas/ the core (Agent A)
tests/         fixture repos + verification-bar tests (Agent B)
examples/      runnable demos against the fixture repos
```

See `PLAN.md` for scope, out-of-scope items, build estimate,
and the pricing draft (MIT core free; a studio-delivered
diligence/onboarding service is a separate, undecided gate).
Nothing about pricing or publishing is decided by this README.
