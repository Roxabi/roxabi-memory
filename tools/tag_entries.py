#!/usr/bin/env python3
"""
Batch-tag all vault entries using metadata + keyword extraction (no API needed).

Strategy per type:
- All entries: category + type as base tags
- knowledge/twitter: URL domain, keywords from preview/title
- knowledge/github: owner, repo name, language if in metadata
- knowledge/article|tool|website: domain, keywords from title
- knowledge/youtube: keywords from title
- idea/*: keywords from title + content
- content/*: subtype tag

Usage:
    python tools/tag_entries.py [--dry-run] [--force]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent.parent))
from roxabi_vault.db import MemoryDB  # noqa: E402

DEFAULT_DB = Path.home() / ".roxabi-vault" / "vault.db"

# ── Stopwords (FR + EN) ──────────────────────────────────────────────────────
STOPWORDS = {
    # EN
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "this", "that", "these", "those", "it", "its",
    "i", "you", "we", "they", "he", "she", "my", "your", "our", "their",
    "what", "how", "why", "when", "where", "which", "who", "not", "no",
    "can", "now", "also", "just", "more", "new", "use", "used", "using",
    "https", "http", "com", "www", "get", "set", "run", "make", "like",
    "one", "two", "all", "any", "some", "there", "than", "then", "so",
    # FR
    "le", "la", "les", "un", "une", "des", "du", "de", "et", "ou", "en",
    "dans", "sur", "par", "pour", "avec", "sans", "est", "sont", "être",
    "avoir", "faire", "plus", "très", "bien", "aussi", "comme", "mais",
    "qui", "que", "quoi", "ce", "se", "sa", "son", "ses", "mon", "ma",
    "mes", "vous", "nous", "je", "il", "elle", "ils", "elles", "au", "aux",
}

# ── Tech keyword map (keyword → tag) ─────────────────────────────────────────
TECH_KEYWORDS: dict[str, str] = {
    # AI / LLM
    "llm": "llm", "gpt": "gpt", "claude": "claude", "gemini": "gemini",
    "mistral": "mistral", "qwen": "qwen", "ollama": "ollama",
    "rag": "rag", "embedding": "embeddings", "embeddings": "embeddings",
    "vector": "vector-search", "fine-tuning": "fine-tuning", "finetuning": "fine-tuning",
    "agent": "agents", "agents": "agents", "mcp": "mcp", "reasoning": "reasoning",
    "inference": "inference", "transformer": "transformer",
    "openai": "openai", "anthropic": "anthropic", "huggingface": "huggingface",
    "stable": "stable-diffusion", "diffusion": "diffusion", "midjourney": "midjourney",
    "tts": "tts", "stt": "stt", "whisper": "whisper", "voice": "voice",
    # Dev
    "python": "python", "typescript": "typescript", "javascript": "javascript",
    "rust": "rust", "go": "golang", "java": "java", "kotlin": "kotlin",
    "react": "react", "vue": "vue", "nextjs": "nextjs", "fastapi": "fastapi",
    "docker": "docker", "kubernetes": "kubernetes", "k8s": "kubernetes",
    "postgres": "postgres", "sqlite": "sqlite", "redis": "redis",
    "api": "api", "graphql": "graphql", "grpc": "grpc", "rest": "rest-api",
    "github": "github", "git": "git", "ci": "ci-cd", "cd": "ci-cd",
    "aws": "aws", "gcp": "gcp", "azure": "azure", "vercel": "vercel",
    "monorepo": "monorepo", "microservices": "microservices",
    # Business / Finance
    "startup": "startup", "saas": "saas", "b2b": "b2b", "b2c": "b2c",
    "fintech": "fintech", "crypto": "crypto", "bitcoin": "bitcoin",
    "trading": "trading", "finance": "finance", "invest": "investing",
    "revenue": "business", "business": "business", "marketing": "marketing",
    "growth": "growth", "product": "product", "design": "design",
    # Career
    "career": "career", "job": "job-search", "hiring": "hiring",
    "interview": "interview", "resume": "cv", "cv": "cv",
    "freelance": "freelance", "remote": "remote-work",
    # Personal
    "productivity": "productivity", "habit": "habits", "learning": "learning",
    "book": "books", "note": "notes",
}


def extract_domain_tag(url: str) -> str | None:
    """Extract meaningful tag from URL domain."""
    if not url:
        return None
    try:
        host = urlparse(url).netloc.lower().replace("www.", "")
        # Map known domains
        domain_map = {
            "x.com": "twitter", "twitter.com": "twitter",
            "github.com": "github", "huggingface.co": "huggingface",
            "arxiv.org": "arxiv", "youtube.com": "youtube", "youtu.be": "youtube",
            "reddit.com": "reddit", "linkedin.com": "linkedin",
            "medium.com": "medium", "substack.com": "substack",
            "news.ycombinator.com": "hackernews",
        }
        if host in domain_map:
            return domain_map[host]
        # Generic: first part of domain
        parts = host.split(".")
        return parts[0] if parts and len(parts[0]) > 2 else None
    except Exception:
        return None


def extract_github_tags(url: str) -> list[str]:
    """Extract owner/repo from GitHub URL."""
    match = re.search(r"github\.com/([^/]+)/([^/?#]+)", url or "")
    if not match:
        return []
    repo = match.group(2)
    tags = []
    # Add repo name (clean up)
    repo_clean = re.sub(r"[-_.]", "-", repo.lower())
    if len(repo_clean) > 2:
        tags.append(repo_clean)
    return tags


def keywords_from_text(text: str, max_tags: int = 4) -> list[str]:
    """Extract meaningful keywords from free text."""
    if not text:
        return []
    text_lower = text.lower()
    found: list[str] = []
    # First: check known tech keywords (priority)
    for kw, tag in TECH_KEYWORDS.items():
        if re.search(r"\b" + re.escape(kw) + r"\b", text_lower) and tag not in found:
            found.append(tag)
    if len(found) >= max_tags:
        return found[:max_tags]
    # Then: extract frequent nouns (simple heuristic: capitalized words in original)
    words = re.findall(r"\b[A-Z][a-z]{3,}\b", text)
    for w in words:
        w_lower = w.lower()
        if w_lower not in STOPWORDS and w_lower not in found and len(w_lower) > 3:
            found.append(w_lower)
        if len(found) >= max_tags:
            break
    return found[:max_tags]


def tags_for_entry(entry) -> list[str]:
    """Compute tags for a single entry."""
    tags: list[str] = []
    meta: dict = {}
    try:
        meta = json.loads(entry.metadata or "{}")
    except (json.JSONDecodeError, TypeError):
        pass

    url: str = meta.get("url", "")
    preview: str = meta.get("preview", "")
    title: str = entry.title or ""
    category: str = entry.category
    etype: str = entry.type

    # 1. Base: category (if not 'knowledge'/'content'/'idea') + type
    if category not in ("knowledge", "content", "idea", "general"):
        tags.append(category)
    if etype not in ("note", "link") and etype not in tags:
        tags.append(etype)

    # 2. Domain / source tag
    domain_tag = extract_domain_tag(url)
    if domain_tag and domain_tag not in tags:
        tags.append(domain_tag)

    # 3. GitHub: extract repo name
    if etype == "github" or "github.com" in url:
        for t in extract_github_tags(url):
            if t not in tags:
                tags.append(t)

    # 4. Keywords from title + preview
    text = f"{title} {preview}"
    for kw_tag in keywords_from_text(text, max_tags=4):
        if kw_tag not in tags:
            tags.append(kw_tag)

    # 5. Category-level tag for content/idea
    if category in ("content", "idea"):
        cat_tag = f"{category}"
        if cat_tag not in tags:
            tags.append(cat_tag)

    # Normalize: lowercase, no spaces
    tags = [t.lower().strip().replace(" ", "-") for t in tags if t.strip()]
    # Deduplicate preserving order
    seen: set[str] = set()
    result: list[str] = []
    for t in tags:
        if t not in seen and len(t) > 1:
            seen.add(t)
            result.append(t)

    # Ensure minimum 2 tags
    if len(result) < 2:
        if category not in result:
            result.append(category)
        if etype not in result:
            result.append(etype)

    return result[:8]


def main() -> None:
    parser = argparse.ArgumentParser(description="Tag vault entries (no API needed)")
    parser.add_argument("--dry-run", action="store_true", help="Print tags, don't write")
    parser.add_argument("--force", action="store_true", help="Re-tag already-tagged entries")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    args = parser.parse_args()

    db_path = Path(args.db)
    with MemoryDB(db_path) as db:
        all_entries = db.list_entries(limit=None)
        already_tagged = db.tagged_entry_ids() if not args.force else set()

    to_process = [e for e in all_entries if e.id not in already_tagged]
    skipped = len(all_entries) - len(to_process)
    print(f"Entries: {len(all_entries)} total, {skipped} already tagged, {len(to_process)} to process")

    if not to_process:
        print("Nothing to do. Use --force to re-tag.")
        return

    tag_counts: dict[str, int] = {}
    with MemoryDB(db_path) as db:
        for entry in to_process:
            tags = tags_for_entry(entry)
            if args.dry_run:
                print(f"[{entry.id}] {entry.category}/{entry.type} {entry.title[:50]!r} → {tags}")
            else:
                db.set_tags(entry.id, tags)
            for t in tags:
                tag_counts[t] = tag_counts.get(t, 0) + 1

    action = "Would tag" if args.dry_run else "Tagged"
    print(f"\n{action} {len(to_process)} entries.")
    print("\nTop 20 tags:")
    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])[:20]:
        print(f"  {tag}: {count}")


if __name__ == "__main__":
    main()
