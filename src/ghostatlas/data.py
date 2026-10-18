"""Data assembly over GhostSlice results.

One run produces one ``AtlasData``: every surface (map, reading
order, brief, HTML) renders from this single object, stamped once,
so numbers can never disagree between the HTML and ATLAS.md.
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from . import engine
from .config import is_hidden, load_atlas_config

READ_MIN_PER_1K_TOKENS = 0.5  # documented reading estimate used everywhere

_MANIFEST_NAMES = ("package.json", "pyproject.toml", "Cargo.toml",
                   "go.mod", "requirements.txt", "setup.py", "Gemfile")
_CONFIG_EXTS = {".json", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".xml", ".env"}
_LICENSE_NAMES = {"license", "license.md", "license.txt", "licence",
                  "licence.md", "copying", "copying.md", "notice"}


def _read(path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def docstring_first_line(text: str, language: str) -> str:
    """Extractive only: the module docstring's first non-empty line
    (Python), a leading block comment's first line (JS/TS family), or
    a Markdown file's first heading. '' when there is none - callers
    must say so rather than invent a description."""
    if not text:
        return ""
    if language == "python":
        try:
            tree = ast.parse(text)
            doc = ast.get_docstring(tree) or ""
        except Exception:
            doc = ""
        for ln in doc.splitlines():
            if ln.strip():
                return ln.strip()
        return ""
    if language == "markdown":
        for ln in text.splitlines():
            if ln.startswith("#"):
                return ln.lstrip("#").strip()
        return ""
    if language in ("typescript", "javascript", "go", "rust", "java", "csharp", "c", "cpp"):
        stripped = text.lstrip()
        if stripped.startswith("/*"):
            body = stripped[2:].split("*/", 1)[0]
            for ln in body.splitlines():
                ln = ln.strip().lstrip("*").strip()
                if ln:
                    return ln
        elif stripped.startswith("//"):
            return stripped.splitlines()[0].lstrip("/").strip()
    return ""


def top_symbols(text: str, language: str, limit: int = 8) -> list:
    """Top-level symbol names, extracted. Python via ast, other code
    via a conservative definition-line regex. Names only, no prose."""
    out = []
    if language == "python":
        try:
            tree = ast.parse(text)
        except Exception:
            return out
        for node in getattr(tree, "body", []):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                out.append(node.name)
            if len(out) >= limit:
                break
        return out
    pat = re.compile(
        r"^(?:export\s+)?(?:default\s+)?(function|class|interface|const|def|func|fn)\s+"
        r"([A-Za-z_$][\w$]*)", re.M)
    for m in pat.finditer(text or ""):
        out.append(m.group(2))
        if len(out) >= limit:
            break
    return out


def _git(args, root: Path):
    try:
        r = subprocess.run(["git", "-C", str(root)] + args,
                           capture_output=True, text=True, timeout=30)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def git_activity(root: Path, window_commits: int = 200) -> dict:
    """Change activity from the local git log. Window is labelled:
    the most recent ``window_commits`` commits (or all, if fewer)."""
    out = {"available": False, "window": f"last {window_commits} commits",
           "commits_considered": 0, "per_file": {}, "first_date": None,
           "last_date": None, "total_commits": 0}
    if not (root / ".git").exists():
        return out
    log = _git(["log", "--name-only", "--pretty=format:%H",
                f"-n{window_commits}"], root)
    if log is None:
        return out
    counts = Counter()
    commits = 0
    for ln in log.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if re.fullmatch(r"[0-9a-f]{7,40}", ln):
            commits += 1
        else:
            counts[ln] += 1
    dates = _git(["log", "--pretty=format:%ad", "--date=short"], root)
    if dates:
        ds = [d for d in dates.splitlines() if d.strip()]
        if ds:
            out["total_commits"] = len(ds)
            out["last_date"] = ds[0]
            out["first_date"] = ds[-1]
    out.update({"available": True, "commits_considered": commits,
                "per_file": dict(counts)})
    return out


def dependency_surface(root: Path, files) -> list:
    """Dependency names declared in manifests. Names only - manifest
    dependency lists are the manifest's public interface."""
    deps = set()
    by_path = {f.path: f for f in files}
    pkg = by_path.get("package.json")
    if pkg:
        try:
            data = json.loads(_read(pkg.abspath))
            for key in ("dependencies", "devDependencies", "peerDependencies"):
                deps.update((data.get(key) or {}).keys())
        except ValueError:
            pass
    req = by_path.get("requirements.txt")
    if req:
        for ln in _read(req.abspath).splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                name = re.split(r"[<>=!~\[; ]", ln, 1)[0].strip()
                if name:
                    deps.add(name)
    pyproj = by_path.get("pyproject.toml")
    if pyproj:
        text = _read(pyproj.abspath)
        m = re.search(r"dependencies\s*=\s*\[(.*?)\]", text, re.S)
        if m:
            for item in re.findall(r'"([^"]+)"|\'([^\']+)\'', m.group(1)):
                name = re.split(r"[<>=!~\[; ]", (item[0] or item[1]), 1)[0].strip()
                if name:
                    deps.add(name)
    cargo = by_path.get("Cargo.toml")
    if cargo:
        in_deps = False
        for ln in _read(cargo.abspath).splitlines():
            s = ln.strip()
            if s.startswith("["):
                in_deps = s in ("[dependencies]", "[dev-dependencies]")
                continue
            if in_deps and "=" in s:
                deps.add(s.split("=", 1)[0].strip().strip('"'))
    gomod = by_path.get("go.mod")
    if gomod:
        for ln in _read(gomod.abspath).splitlines():
            s = ln.strip()
            if s.startswith("require "):
                rest = s[len("require "):].strip("() ")
                if rest:
                    deps.add(rest.split()[0])
    return sorted(deps)


@dataclass
class AtlasData:
    root: str
    title: str
    run_stamp: str
    engine: str
    audience: str = "onboarding"
    generated_at: str = ""
    config: dict = field(default_factory=dict)
    files: list = field(default_factory=list)          # dicts, scan order
    packages: list = field(default_factory=list)       # {path, files, tokens, size}
    graph: dict = field(default_factory=dict)          # path -> {imports, external}
    importers: dict = field(default_factory=dict)      # path -> [importer paths]
    entries: list = field(default_factory=list)        # entry candidates w/ evidence
    call_chains: list = field(default_factory=list)    # sampled chains (python)
    call_counts: dict = field(default_factory=dict)
    duplicates: dict = field(default_factory=dict)     # {exact: [], near: []}
    dead_candidates: list = field(default_factory=list)
    git: dict = field(default_factory=dict)
    secrets_summary: dict = field(default_factory=dict)  # counts/types only
    lint_findings: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)
    licenses: list = field(default_factory=list)
    total_tokens: int = 0
    total_size: int = 0

    def by_path(self):
        return {f["path"]: f for f in self.files}

    def to_dict(self):
        return {
            "root": self.root, "title": self.title,
            "run_stamp": self.run_stamp, "engine": self.engine,
            "audience": self.audience, "generated_at": self.generated_at,
            "files": self.files, "packages": self.packages,
            "graph": self.graph, "entries": self.entries,
            "call_chains": self.call_chains,
            "duplicates": self.duplicates,
            "dead_candidates": self.dead_candidates, "git": self.git,
            "secrets_summary": self.secrets_summary,
            "lint_findings": self.lint_findings,
            "dependencies": self.dependencies, "licenses": self.licenses,
            "total_tokens": self.total_tokens, "total_size": self.total_size,
        }


def _sample_call_chains(gs, scan_obj, graph) -> tuple[list, dict]:
    """Top call chains from GhostSlice's Python call graph, capped.
    Returns ([{chain: 'a -> b -> c', sites}], counts). Sampled from
    static analysis - callers must label them as such."""
    chains, counts = [], {}
    if gs is None:
        return chains, counts
    try:
        from ghostslice.callgraph import build_call_graph
        payload = build_call_graph(scan_obj, graph=graph)
    except Exception:
        return chains, counts
    counts = payload.get("counts", {}) or {}
    adj: dict[str, list] = defaultdict(list)
    sites: dict[tuple, int] = {}
    for e in payload.get("edges", []):
        if e.get("kind") == "reference":
            continue
        adj[e["caller"]].append(e["callee"])
        sites[(e["caller"], e["callee"])] = e.get("sites", 1)
    starts = sorted(adj, key=lambda s: -sum(sites.get((s, t), 1) for t in adj[s]))
    seen = set()
    for start in starts[:40]:
        chain, cur, visited = [start], start, {start}
        while adj.get(cur) and len(chain) < 5:
            nxts = [t for t in adj[cur] if t not in visited]
            if not nxts:
                break
            cur = max(nxts, key=lambda t: sites.get((chain[-1], t), 1))
            chain.append(cur)
            visited.add(cur)
        if len(chain) >= 3:
            key = " -> ".join(chain)
            if key not in seen:
                seen.add(key)
                chains.append({"chain": key,
                               "length": len(chain),
                               "symbols": list(chain)})
        if len(chains) >= 10:
            break
    return chains, counts


def build_atlas_data(root: str | Path, audience: str = "onboarding") -> AtlasData:
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError(f"ghostatlas: not a directory: {root}")
    cfg = load_atlas_config(root)
    gs = engine.load_ghostslice()
    eng = "ghostslice" if gs is not None else "fallback"

    scan_obj = None
    files: list = []
    packages: list = []
    graph: dict = {}
    entries: list = []
    duplicates: dict = {"exact": [], "near": []}
    secrets_summary: dict = {"count": 0, "by_type": {}, "by_file": {}}
    lint_findings: list = []
    call_chains: list = []
    call_counts: dict = {}
    dead: list = []

    if gs is not None:
        from ghostslice.scanner import scan as gs_scan
        from ghostslice.graph import build_graph, importers_of, recommendations
        from ghostslice.entries import find_entry_candidates
        scan_obj = gs_scan(root)
        for f in scan_obj.files:
            d = f.to_dict() if hasattr(f, "to_dict") else dict(f.__dict__)
            d.pop("abspath", None)
            files.append(d)
        try:
            from ghostslice.workspaces import summarize_packages
            packages = summarize_packages(scan_obj)
        except Exception:
            packages = []
        graph = build_graph(scan_obj)
        entries = find_entry_candidates(scan_obj, graph)
        try:
            from ghostslice.duplicates import find_duplicates
            duplicates = find_duplicates(scan_obj)
        except Exception:
            pass
        try:
            from ghostslice.secrets_scan import scan_scan_result
            findings = scan_scan_result(scan_obj)
            by_type = Counter(x.get("type", "unknown") for x in findings)
            by_file = Counter(x.get("path", "") for x in findings)
            secrets_summary = {"count": len(findings),
                               "by_type": dict(sorted(by_type.items())),
                               "by_file": dict(sorted(by_file.items()))}
        except Exception:
            pass
        try:
            from ghostslice.lint import lint_project
            payload = lint_project(root, scan_result=scan_obj, graph=graph)
            lint_findings = payload.get("findings", []) or []
        except Exception:
            lint_findings = []
        try:
            recs = recommendations(scan_obj, graph)
            dead = [{"path": r.get("path"), "reason": r.get("reason", ""),
                     "tokens": r.get("tokens", 0)} for r in recs]
        except Exception:
            dead = []
        call_chains, call_counts = _sample_call_chains(gs, scan_obj, graph)
    else:
        scan_obj = engine.fallback_scan(root)
        files = [f.to_dict() for f in scan_obj.files]
        for f in files:
            f.pop("abspath", None)
        packages = scan_obj.packages
        graph = engine.fallback_graph(scan_obj)
        entries = engine.fallback_entries(scan_obj, graph)

    # hidden paths from the atlas config are removed from every surface
    if cfg["hidden_paths"]:
        keep = [f for f in files if not is_hidden(f["path"], cfg["hidden_paths"])]
        removed = {f["path"] for f in files} - {f["path"] for f in keep}
        files = keep
        graph = {k: {"imports": [i for i in v.get("imports", []) if i not in removed],
                     "external": v.get("external", [])}
                 for k, v in graph.items() if k not in removed}
        entries = [e for e in entries if e["path"] not in removed]
        dead = [d for d in dead if d.get("path") not in removed]

    # per-file enrichment: docstring first line, top symbols, importers
    importers: dict[str, list] = defaultdict(list)
    for src, data in graph.items():
        for dst in data.get("imports", []):
            importers[dst].append(src)
    root_by_rel = {}
    if gs is not None and scan_obj is not None:
        root_by_rel = {f.path: f.abspath for f in scan_obj.files}
    elif scan_obj is not None and hasattr(scan_obj, "files"):
        root_by_rel = {f.path: f.abspath for f in scan_obj.files}
    for f in files:
        ap = root_by_rel.get(f["path"], str(root / f["path"]))
        text = _read(ap)
        f["doc"] = docstring_first_line(text, f.get("language", ""))
        f["symbols"] = top_symbols(text, f.get("language", ""))
        f["importer_count"] = len(importers.get(f["path"], []))
        f["package"] = f.get("package") or (
            f["path"].rsplit("/", 1)[0] if "/" in f["path"] else "")

    if not packages:
        agg: dict[str, dict] = {}
        for f in files:
            p = agg.setdefault(f["package"], {"path": f["package"], "files": 0,
                                              "tokens": 0, "size": 0})
            p["files"] += 1
            p["tokens"] += f.get("tokens", 0)
            p["size"] += f.get("size", 0)
        packages = sorted(agg.values(), key=lambda p: (-p["tokens"], p["path"]))

    file_objs = [type("F", (), {"path": f["path"], "abspath": root_by_rel.get(f["path"], str(root / f["path"]))})() for f in files]
    licenses = sorted(
        f["path"] for f in files
        if PurePosixPath(f["path"]).name.lower() in _LICENSE_NAMES)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = AtlasData(
        root=str(root),
        title=cfg["title"] or root.name,
        run_stamp=stamp,
        generated_at=stamp,
        engine=eng,
        audience=audience,
        config=cfg,
        files=files,
        packages=packages,
        graph=graph,
        importers={k: sorted(v) for k, v in importers.items()},
        entries=entries,
        call_chains=call_chains,
        call_counts=call_counts,
        duplicates=duplicates,
        dead_candidates=dead,
        git=git_activity(root),
        secrets_summary=secrets_summary,
        lint_findings=lint_findings,
        dependencies=dependency_surface(root, file_objs),
        licenses=licenses,
        total_tokens=sum(f.get("tokens", 0) for f in files),
        total_size=sum(f.get("size", 0) for f in files),
    )
    return data
