# GhostAtlas examples

Two runnable demos, both against the fixture repos in `tests/`,
both fully local. They assume GhostAtlas is runnable as
`python3 -m ghostatlas` with `PYTHONPATH` pointing at this repo's
`src/`, as in the project README.

## 1. Fixture map (`demo.sh`)

```bash
./demo.sh
```

Builds an Atlas for the ground-truth fixture
(`tests/fixtures/ground_truth/project`) into a temp folder and
prints where `atlas.html` and `ATLAS.md` landed.

What to look for in the output:

- Reading order starts with `main.py` (the fixture's entry point,
  `__main__` guard).
- The map shows `main.py -> engine.py -> util.py`.
- `dead.py` appears under dead zones ("worth asking about"),
  nowhere else.
- Every token number in `ATLAS.md` matches a
  `ghostslice scan` of the same fixture.

## 2. Diligence brief (`diligence.sh`)

```bash
./diligence.sh
```

Same fixture, `--audience diligence`. The brief leads with size
and shape and includes the checked / not-checked box. It is an
orientation aid, not an audit opinion, and the brief says so.

## Not included yet

A demo on a real repo (GhostBus, and one parked project, per
`PLAN.md`) belongs with the parent verification step once the
core lands; the fixture demos above are what the test suite can
reproduce byte-for-byte in totals today.
