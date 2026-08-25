"""Goal 4 -- real-world research distillation (BM25 + citation ranking + structure).

The original spec asked for a FIVE-STAGE DETERMINISTIC pipeline (no model in
the loop; CPU-only, stdlib-only) that turns raw material -- web/source/docs --
with a query into a citations-ranked, structurally-extracted digest:

  Stage 1  Term relevance      -- BM25 (Robertson/Sparck-Jones) scoring of each
                                  doc against the query. Same family as the
                                  TF-IDF term-relevance step in the spec.
  Stage 2  Proximity filtering -- LexisNexus-style: a doc only counts if the
                                  query's discriminative terms co-occur within
                                  a bounded window (relevance without proximity
                                  is weak evidence).
  Stage 3  Citation ranking     -- PageRank-style power iteration over the
                                  docs' citation graph (a doc is authoritative
                                  if authoritative docs cite it).
  Stage 4  Relevance feedback   -- WAIS/Rocchio-style: expand the query with the
                                  most discriminative terms of the top-ranked
                                  docs and re-score (feedback loop).
  Stage 5  Structural extraction-- Edmundson-style cue-phrase extraction: pull
           the sentences whose cue words ("we found", "the results show",
           "in conclusion") mark them as topical/key, with bonus for doc titles
           and penalty for boilerplate ("Introduction", "click here").

All scoring is deterministic and unit-testable with a tiny corpus. This module
is deliberately decoupled from the scheduler/task store: it is a pure function
on a document set, so research tasks can use it directly through the same
dispatch path.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------
_WORD_RE = re.compile(r"[A-Za-z0-9]+")


def tokenize(text: str) -> List[str]:
    return _WORD_RE.findall((text or "").lower())


# Terms that add no relevance signal (left OUT of the BM25 term set; positional
# windows keep working with them present because windows are positional).
_STOP = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with",
    "is", "are", "was", "were", "be", "been", "at", "by", "as", "it", "this",
    "that", "from", "but", "not", "we", "our", "you", "your", "they", "their",
    "have", "has", "had", "do", "does", "did", "will", "would", "can", "could",
}


def content_tokens(text: str) -> List[str]:
    return [t for t in tokenize(text) if t not in _STOP]


@dataclass
class Doc:
    id: str
    text: str
    title: str = ""
    citations: List[str] = field(default_factory=list)   # ids this doc cites
    year: Optional[int] = None

    def full_text(self) -> str:
        return f"{self.title}\n{self.text}"


# ---------------------------------------------------------------------------
# Stage 1 -- BM25 term relevance
# ---------------------------------------------------------------------------
class BM25:
    def __init__(self, docs: Sequence[Doc], k1: float = 1.5, b: float = 0.75) -> None:
        self.docs = list(docs)
        self.N = len(self.docs)
        self.k1 = k1
        self.b = b
        self.docs_len = [len(tokenize(d.full_text())) for d in self.docs]
        self.avgdl = sum(self.docs_len) / self.N if self.N else 0.0
        self.df: Dict[str, int] = {}
        for d in self.docs:
            for term in set(content_tokens(d.full_text())):
                self.df[term] = self.df.get(term, 0) + 1
        self.idf: Dict[str, float] = {}
        for term in self.df:
            n = self.df[term]
            self.idf[term] = math.log1p((self.N - n + 0.5) / max(n + 0.5, 1e-9))

    def score(self, query_terms: Sequence[str], doc_idx: int) -> float:
        if self.N == 0 or self.avgdl <= 0:
            return 0.0
        qset = set(query_terms)
        freq: Dict[str, int] = {}
        for t in tokenize(self.docs[doc_idx].full_text()):
            if t in qset:
                freq[t] = freq.get(t, 0) + 1
        dl = self.docs_len[doc_idx]
        score = 0.0
        for t in qset:
            f = freq.get(t, 0)
            if f == 0:
                continue
            idf = self.idf.get(t, 0.0)
            score += idf * (f * (self.k1 + 1)) / (
                f + self.k1 * (1 - self.b + self.b * float(dl) / max(self.avgdl, 1e-9)))
        return score

    def scores(self, query_terms: Sequence[str]) -> List[float]:
        return [self.score(query_terms, i) for i in range(self.N)]


# ---------------------------------------------------------------------------
# Stage 2: LexisNexus-style proximity filtering
# ---------------------------------------------------------------------------
def proximity_ok(doc: Doc, query_terms: Sequence[str], window: int = 40) -> bool:
    """True if ALL query terms co-occur within one sliding window of tokens."""
    toks = tokenize(doc.full_text())
    if not query_terms:
        return True
    if not toks:
        return False
    needed = set(query_terms)
    counts: Dict[str, int] = {}
    start = 0
    for end, tok in enumerate(toks):
        if tok in needed:
            counts[tok] = counts.get(tok, 0) + 1
        while end - start + 1 > window:
            t0 = toks[start]
            if t0 in needed:
                counts[t0] = max(counts.get(t0, 0) - 1, 0)
                if counts[t0] == 0:
                    del counts[t0]
            start += 1
        if all(counts.get(t, 0) > 0 for t in needed):
            return True
    return False


# ---------------------------------------------------------------------------
# Stage 3: PageRank-style citation ranking
# ---------------------------------------------------------------------------
def citation_rank(docs: Sequence[Doc],
                  damping: float = 0.85,
                  tol: float = 1e-9,
                  max_iter: int = 60) -> List[float]:
    """Iterative PageRank over the citation graph (edge from citing -> cited)."""
    n = len(docs)
    if n == 0:
        return []
    idx = {d.id: i for i, d in enumerate(docs)}
    out: List[List[int]] = [[] for _ in range(n)]
    for u, d in enumerate(docs):
        for cit in d.citations:
            v = idx.get(cit)
            if v is not None and v != u:
                out[u].append(v)
    in_links: List[List[int]] = [[] for _ in range(n)]
    for u, edges in enumerate(out):
        for v in edges:
            in_links[v].append(u)
    dangling = [u for u in range(n) if not out[u]]
    rank = [1.0 / n for _ in range(n)]
    base = (1.0 - damping) / n
    for _ in range(max_iter):
        new = [base for _ in range(n)]
        for v in range(n):
            acc = 0.0
            deg = [max(len(out[u]), 1) for u in in_links[v]]
            for u, deg_ in zip(in_links[v], deg):
                acc += rank[u] / deg_
            new[v] += damping * acc
        if dangling:
            spread = damping * sum(rank[u] for u in dangling) / n
            for v in range(n):
                new[v] += spread
        if all(abs(new[i] - rank[i]) < tol for i in range(n)):
            rank = new
            break
        rank = new
    return rank


# ---------------------------------------------------------------------------
# Stage 4: WAIS-style relevance feedback (Rocchi-style query expansion)
# ---------------------------------------------------------------------------
def rocchio_query(query_terms: Sequence[str],
                  top_docs: Sequence[Doc],
                  n_terms: int = 3) -> List[str]:
    """Expand the query with the most discriminative NEW terms of the top docs.

    Term score contribution = (its local term freq / doc length) *
    log1p(1 / doc-freq-across-feedback-set) * rank-weight (top doc counts more).
    """
    from collections import Counter
    docs = list(top_docs)
    if not docs:
        return list(query_terms)
    df = Counter()
    for d in docs:
        df.update(set(content_tokens(d.full_text())))
    merged = Counter()
    qset = set(query_terms)
    for rank_pos, d in enumerate(docs):
        w = 1.0 / (rank_pos + 1.0)
        n_doc = float(len(content_tokens(d.full_text())) or 1.0)
        local = Counter(content_tokens(d.full_text()))
        for term, cnt in local.items():
            if term in qset or not term:
                continue
            score = (cnt / n_doc) * math.log1p(1.0 / max(df[term], 1)) * w
            merged[term] += score
    extra = [t for t, _ in merged.most_common(n_terms)]
    return list(query_terms) + extra


# ---------------------------------------------------------------------------
# Stage 5: Edmundson-style cue-phrase key-sentence extraction
# ---------------------------------------------------------------------------
_BONUS_CUES = [
    "we found", "we show", "our results", "the results show", "we conclude",
    "in conclusion", "reveals that", "demonstrate", "key finding", "summary",
    "this study shows", "the evidence suggests",
]
_PENALTY_CUES = [
    "introduction", "copyright", "all rights reserved", "abstract", "click",
    "subscribe", "log in", "cookie",
]


def extract_key_sentences(doc: Doc, max_sentences: int = 3) -> List[str]:
    """Cue-based extraction. Bonus for bonus cues + title-term echo; penalty for
    boilerplate. Returns top sentences in document order."""
    text = doc.full_text().replace("\n", " ")
    sentences = re.split(r"(?<=[.!?])\s+", text)
    title_toks = set(content_tokens(doc.title))
    scored: List[Tuple[float, str, int]] = []
    for order, sent in enumerate(sentences):
        s = sent.strip()
        if not s:
            continue
        low = s.lower()
        score = 0.0
        for cue in _BONUS_CUES:
            if cue in low:
                score += 1.5
        for cue in _PENALTY_CUES:
            if cue in low:
                score -= 1.0
        score += float(len(set(content_tokens(s)) & title_toks))
        scored.append((score, s, order))
    scored.sort(key=lambda x: (-x[0], x[2]))
    return [s for _, s, _ in scored[:max_sentences]]


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------
@dataclass
class ResearchReport:
    query: str
    ranked: List[Dict]                  # per-doc: id,title,score,top_sentences
    feedback_added: List[str]           # terms expanded by stage 4
    citation_weights: List[float]
    included_docs: int


def _to_docs(documents: Sequence[Dict]) -> List[Doc]:
    docs: List[Doc] = []
    for i, raw in enumerate(documents):
        did = str(raw.get("id", f"doc-{i}"))
        docs.append(Doc(
            id=did,
            text=str(raw.get("text", "")),
            title=str(raw.get("title", "")),
            citations=[str(c) for c in raw.get("citations", [])],
            year=raw.get("year"),
        ))
    return docs


def distill(query: str,
            documents: Sequence[Dict],
            window: int = 40,
            max_sentences: int = 3) -> ResearchReport:
    """Five-stage composition. Returns the full ResearchReport."""
    docs = _to_docs(documents)
    if not docs:
        return ResearchReport(query=query, ranked=[], feedback_added=[],
                              citation_weights=[], included_docs=0)

    query_terms = content_tokens(query)
    bm = BM25(docs)

    # Stage 3 (citation rank) -- computed over the whole set, independent of
    # query, so citation weight is a property of the corpus.
    citer_ranks = citation_rank(docs)

    # Stage 2 proximity filter: keep only docs where the query co-occurs within
    # a window. A doc that is highly cited but never talks about the query in
    # one passage is not a research return for THIS query.
    staged = [(i, d) for i, d in enumerate(docs)
              if proximity_ok(d, query_terms, window=window)]
    if not staged:
        return ResearchReport(query=query, ranked=[], feedback_added=[],
                              citation_weights=citer_ranks, included_docs=0)

    # Stage 1 initial BM25 ordering -> Stage 4 relevance feedback.
    s1: List[Tuple[int, float]] = []
    for i, d in staged:
        s1.append((i, bm.score(query_terms, i)))
    s1.sort(key=lambda x: -x[1])
    top_feedback = [docs[i] for i, _ in s1[:3] if _ > 0.0]
    expanded = rocchio_query(query_terms, top_feedback, n_terms=3)

    # Re-score with the expanded query (Stage 1+4) and combine with citation
    # weight (Stage 3) into a final ordering.
    ranked: List[Dict] = []
    for i, d in staged:
        refined = bm.score(expanded, i)
        fill = proximity_ok(d, query_terms, window=window)
        final = refined * (0.7 + 0.6 * citer_ranks[i])
        if not fill:
            final *= 0.5
        ranked.append({
            "id": d.id,
            "title": d.title,
            "score": round(final, 6),
            "top_sentences": extract_key_sentences(d, max_sentences=max_sentences),
            "citation_weight": round(citer_ranks[i], 6),
        })
    ranked.sort(key=lambda x: -x["score"])
    return ResearchReport(
        query=query,
        ranked=ranked,
        feedback_added=[t for t in expanded if t not in query_terms],
        citation_weights=[round(x, 6) for x in citer_ranks],
        included_docs=len(staged),
    )
