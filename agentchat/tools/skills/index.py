"""Skill index using LanceDB for hybrid search."""

import os
import re
import tempfile
from pathlib import Path
from typing import Any

# Suppress tokenizers parallelism warning (must be set before importing transformers)
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
# Suppress LanceDB "No existing dataset" warning (we always create fresh temp DB)
os.environ.setdefault("LANCEDB_LOG", "error")

import lancedb
import yaml
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector
from lancedb.rerankers import RRFReranker

# YAML frontmatter pattern: starts with ---, ends with ---
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)

# Default skills directory (relative to project root)
SKILLS_DIR = Path(__file__).parent.parent.parent.parent / "skills"


def parse_skill_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from skill content.

    Args:
        content: Full content of SKILL.md file.

    Returns:
        Tuple of (frontmatter dict, body content).
    """
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return {}, content

    yaml_str = match.group(1)
    body = content[match.end() :]

    try:
        frontmatter = yaml.safe_load(yaml_str) or {}
    except yaml.YAMLError:
        frontmatter = {}

    return frontmatter, body


# Singleton index instance
_skill_index: "SkillIndex | None" = None


class SkillIndex:
    """In-memory skill index using LanceDB for hybrid search."""

    def __init__(self, skills_dir: Path = SKILLS_DIR) -> None:
        self.skills_dir = skills_dir
        # Use a true temp directory to avoid polluting the workspace
        self._temp_dir = tempfile.mkdtemp(prefix="lancedb_skills_")
        self.db = lancedb.connect(self._temp_dir)
        self.table: Any = None
        self._skill_metadata: dict[str, dict[str, Any]] = {}

    def _scan_skills(self) -> list[dict[str, Any]]:
        """Scan skills directory and extract metadata from SKILL.md files."""
        skills: list[dict[str, Any]] = []

        if not self.skills_dir.exists():
            return skills

        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            content = skill_md.read_text(encoding="utf-8")
            frontmatter, body = parse_skill_frontmatter(content)

            # Use frontmatter name or fall back to directory name
            name = frontmatter.get("name", skill_dir.name)
            # Use frontmatter description or extract from body
            description = frontmatter.get("description", self._extract_description(body))

            # Find other files in the skill directory (relative to skill dir)
            other_files = [
                str(f.relative_to(skill_dir))
                for f in skill_dir.rglob("*")
                if f.is_file() and f.name != "SKILL.md"
            ]

            self._skill_metadata[name] = {
                "name": name,
                "dir_name": skill_dir.name,  # Actual directory name for path resolution
                "path": str(skill_md.relative_to(self.skills_dir)),
                "content": content,
                "body": body,
                "other_files": other_files,
                **frontmatter,  # Include all frontmatter fields
            }

            skills.append(
                {
                    "name": name,
                    "description": description,
                    "text": f"{name}\n{description}\n{body}",
                }
            )

        return skills

    def _extract_description(self, body: str) -> str:
        """Extract description from SKILL.md body (after frontmatter)."""
        lines = body.strip().split("\n")
        description_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            # Skip headers
            if stripped.startswith("#"):
                continue
            # Stop at empty line after getting some content
            if not stripped and description_lines:
                break
            if stripped:
                description_lines.append(stripped)
            # Limit to first few meaningful lines
            if len(description_lines) >= 3:
                break

        return " ".join(description_lines)[:200] if description_lines else ""

    def build_index(self) -> None:
        """Build the search index from skills directory."""
        skills = self._scan_skills()

        if not skills:
            return

        # Get embedding model (multilingual for better Japanese support)
        # NOTE: Downloads model on first run (~500MB) to ~/.cache/huggingface/
        # Subsequent runs use the cached model and work offline.
        embeddings = get_registry().get("sentence-transformers").create(
            name="paraphrase-multilingual-MiniLM-L12-v2"
        )

        # Define schema with embedding
        class SkillDocument(LanceModel):  # type: ignore[misc]
            name: str
            description: str
            text: str = embeddings.SourceField()
            vector: Vector(embeddings.ndims()) = embeddings.VectorField()  # type: ignore[valid-type]

        # Create table
        self.table = self.db.create_table("skills", schema=SkillDocument, mode="overwrite")
        self.table.add(data=skills)

        # Create FTS index for hybrid search
        self.table.create_fts_index("text")

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search skills using hybrid search (BM25 + vector).

        Args:
            query: Search query.
            top_k: Number of results to return.

        Returns:
            List of matching skills with scores.
        """
        if self.table is None:
            return []

        reranker = RRFReranker()

        results = self.table.search(query, query_type="hybrid").rerank(reranker=reranker).limit(top_k).to_list()

        return [
            {
                "name": r["name"],
                "description": r["description"],
                "score": r.get("_relevance_score", 0.0),
            }
            for r in results
        ]

    def get(self, name: str) -> dict[str, Any] | None:
        """Get skill by name.

        Args:
            name: Skill name.

        Returns:
            Skill metadata or None if not found.
        """
        return self._skill_metadata.get(name)


def get_skill_index() -> SkillIndex:
    """Get or create the global skill index."""
    global _skill_index
    if _skill_index is None:
        _skill_index = SkillIndex()
        _skill_index.build_index()
    return _skill_index
