"""Category C (Structured data, incl. P extension) — JSON-LD extraction + required-field map."""
from __future__ import annotations
import json
from ..http_utils import soup_of
from ...schemas import CheckResult, unavailable
from datetime import datetime, timezone
def now(): return datetime.now(timezone.utc).isoformat()
def _mk(key,label,status,sev,found,evidence,why,fix):
    return CheckResult(key=key,label=label,category="C-structured",status=status,severity=sev,found=found,
        source="page HTML (application/ld+json blocks)",evidence=evidence,why_matters=why,how_to_fix=fix,checked_at=now())

REQUIRED = {
    "Article": ["headline","author","datePublished"],
    "NewsArticle": ["headline","author","datePublished"],
    "BlogPosting": ["headline","author","datePublished"],
    "Product": ["name","image","offers"],
    "Organization": ["name","url"],
    "LocalBusiness": ["name","address"],
    "Review": ["itemReviewed","reviewRating","author"],
    "Recipe": ["name","image","recipeIngredient"],
    "Event": ["name","startDate","location"],
    "JobPosting": ["title","hiringOrganization","datePosted"],
    "VideoObject": ["name","thumbnailUrl","uploadDate"],
    "HowTo": ["name","step"],
    "FAQPage": ["mainEntity"],
    "BreadcrumbList": ["itemListElement"],
}

def structured_checks(html: str) -> list[CheckResult]:
    try:
        soup = soup_of(html)
    except Exception as e:
        return [unavailable("c-parse","Structured data parse","C-structured","page HTML",str(e)[:120])]
    tags = soup.find_all("script", attrs={"type": "application/ld+json"})
    if not tags:
        return [_mk("c-jsonld","JSON-LD presence","warning","warning","no application/ld+json found",None,
            "Eligible rich results require structured data.","Add Schema.org JSON-LD matching the page type.")]
    out: list[CheckResult] = []
    out.append(_mk("c-jsonld","JSON-LD presence","pass","ok",f"{len(tags)} JSON-LD block(s)",[{"len": len(t.string or '')} for t in tags],
        "Structured data present.",""))
    for i, tag in enumerate(tags):
        raw = (tag.string or "").strip()
        try:
            data = json.loads(raw)
        except Exception as e:
            out.append(_mk(f"c-block-{i}","JSON-LD block %d valid JSON" % i,"fail","critical",f"parse error: {str(e)[:120]}",raw[:400],
                "Invalid JSON means Google ignores the block.","Validate with a JSON parser; fix trailing commas."))
            continue
        nodes = data if isinstance(data, list) else [data]
        for j, node in enumerate(nodes):
            if not isinstance(node, dict):
                out.append(_mk(f"c-block-{i}-{j}","JSON-LD node shape","warning","warning","node is not an object",str(node)[:200],
                    "Schema nodes must be objects.","Emit @context/@type objects.")); continue
            t = node.get("@type", "Unknown")
            if isinstance(t, list): t = t[0] if t else "Unknown"
            missing_ctx = "@context" not in node
            req = REQUIRED.get(str(t), [])
            missing = [f for f in req if f not in node]
            if missing_ctx or missing:
                out.append(_mk(f"c-{t}-{i}-{j}","Schema %s required fields" % t,"warning","warning",
                    f"@type={t}; missing: {', '.join((['@context'] if missing_ctx else []) + missing) or 'none'}" ,
                    {k: (str(v)[:80]) for k,v in list(node.items())[:8]},
                    "Missing required fields disqualify rich results.","Add: " + ", ".join((['@context'] if missing_ctx else []) + missing)))
            else:
                out.append(_mk(f"c-{t}-{i}-{j}","Schema %s required fields" % t,"pass","ok",f"@type={t}; required fields present",
                    {"@type": t},"Type validates against required-field map.",""))
            same = node.get("sameAs", [])
            if str(t).endswith("Organization") or str(t).endswith("Person") or str(t).endswith("LocalBusiness"):
                if same:
                    out.append(_mk(f"c-sameas-{i}-{j}","sameAs social links (E-E-A-T)","pass","ok",f"{len(same) if isinstance(same,list) else 1} sameAs link(s)",same,
                        "sameAs corroborates entity identity.",""))
                else:
                    out.append(_mk(f"c-sameas-{i}-{j}","sameAs social links (E-E-A-T)","warning","warning","no sameAs on entity node",node.get("name",""),
                        "Missing sameAs weakens entity corroboration.","Add official social/profile URLs to sameAs."))
            if str(t) in ("Article","NewsArticle","BlogPosting") and "author" not in node:
                out.append(_mk(f"c-author-{i}-{j}","Author markup","warning","warning","no author on Article",None,
                    "Author markup supports E-E-A-T.","Add author { @type: Person, name, url }."))
    return out


