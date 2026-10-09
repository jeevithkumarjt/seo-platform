"""Category A (On-Page) + R (International) + G (Content). All from live DOM. No guessing."""
from __future__ import annotations
from urllib.parse import urlparse
from ..http_utils import soup_of
from ...schemas import CheckResult, unavailable
from datetime import datetime, timezone

def now(): return datetime.now(timezone.utc).isoformat()

def _mk(key, label, cat, status, sev, found, source, evidence, why, fix, conf="measured"):
    return CheckResult(key=key, label=label, category=cat, status=status, severity=sev,
        found=found, source=source, evidence=evidence, why_matters=why, how_to_fix=fix,
        checked_at=now(), confidence=conf)

def onpage_checks(url: str, html: str, headers: dict) -> list[CheckResult]:
    out: list[CheckResult] = []
    src = "raw HTML (httpx GET)"
    try:
        soup = soup_of(html)
    except Exception as e:
        return [unavailable("a-parse", "On-page parse", "A-onpage", src, f"HTML parse failed: {e}")]
    # Title
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    if not title:
        out.append(_mk("a-title","Title tag","A-onpage","fail","critical","missing <title>",src,None,
            "Title is the primary on-page relevance/CTR signal.","Add a unique 50-60 char <title>."))
    elif len(title) < 30 or len(title) > 60:
        out.append(_mk("a-title","Title tag","A-onpage","warning","warning",f'"{title}" ({len(title)} chars)',src,title,
            "Over/under-length titles truncate or underperform.","Rewrite to 50-60 chars, target keyword near front."))
    else:
        out.append(_mk("a-title","Title tag","A-onpage","pass","ok",f'"{title}" ({len(title)} chars)',src,title,"Title length is within range.",""))
    # Meta description
    md = soup.find("meta", attrs={"name": "description"})
    mdv = (md.get("content","").strip() if md else "")
    if not mdv:
        out.append(_mk("a-metadesc","Meta description","A-onpage","warning","warning","missing",src,None,
            "Controls snippet CTR.","Add a unique 120-160 char meta description."))
    elif not (70 <= len(mdv) <= 160):
        out.append(_mk("a-metadesc","Meta description","A-onpage","warning","warning",f"{len(mdv)} chars: {mdv[:120]}",src,mdv,
            "Short/long descriptions truncate.","Rewrite to 120-160 chars."))
    else:
        out.append(_mk("a-metadesc","Meta description","A-onpage","pass","ok",f"{len(mdv)} chars",src,mdv,"Length OK.",""))
    # H1-H6
    h1s = soup.find_all("h1")
    counts = {f"h{i}": len(soup.find_all(f"h{i}")) for i in range(1,7)}
    if len(h1s) == 0:
        out.append(_mk("a-h1","H1 hierarchy","A-onpage","fail","critical","no H1 found",src,counts,"Page has no top-level heading.","Add exactly one descriptive H1."))
    elif len(h1s) > 1:
        out.append(_mk("a-h1","H1 hierarchy","A-onpage","warning","warning",f"{len(h1s)} H1s: {[h.get_text(strip=True)[:60] for h in h1s]}",src,counts,"Multiple H1s dilute topical focus.","Reduce to one H1; demote rest to H2."))
    else:
        out.append(_mk("a-h1","H1 hierarchy","A-onpage","pass","ok",h1s[0].get_text(strip=True)[:120],src,counts,"Single H1 present.",""))
    # Images alt + dimensions
    imgs = soup.find_all("img")
    missing_alt = [str(i)[:60] for i, im in enumerate(imgs) if not im.get("alt")]
    missing_dim = sum(1 for im in imgs if not (im.get("width") and im.get("height")))
    if imgs and missing_alt:
        out.append(_mk("a-imgalt",f"Image alt ({len(missing_alt)}/{len(imgs)} missing)","A-onpage","warning","warning",
            f"{len(missing_alt)} of {len(imgs)} <img> lack alt",src,missing_alt[:5],"Missing alt hurts accessibility/image relevance.",'Add descriptive alt to every <img>.'))
    else:
        out.append(_mk("a-imgalt","Image alt","A-onpage","pass","ok",f"{len(imgs)} images, all have alt" if imgs else "no images on page",src,{"total":len(imgs)},"Alt coverage OK.",""))
    out.append(_mk("a-imgdim","Image dimensions","A-onpage","warning" if missing_dim else "pass","warning" if missing_dim else "ok",
        f"{missing_dim} images lack width/height" if missing_dim else f"{len(imgs)} images sized or none present",src,{"missing":missing_dim},
        "Unsized images cause layout shift (CLS).","Add width+height or aspect-ratio CSS."))
    # Canonical / robots / OG / hreflang / URL
    can = soup.find("link", attrs={"rel": "canonical"})
    out.append(_mk("a-canonical","Canonical tag","A-onpage","pass" if can and can.get("href") else "warning","ok" if can else "warning",
        can.get("href") if can else "missing",src,can.get("href") if can else None,"Canonical consolidates duplicates.","Add self-referencing canonical." if not can else ""))
    mr = soup.find("meta", attrs={"name": "robots"})
    mrv = mr.get("content","") if mr else ""
    if "noindex" in mrv.lower():
        out.append(_mk("a-robots","Meta robots","A-onpage","fail","critical",mrv,src,mrv,"Page is set to noindex: it cannot rank.","Remove noindex unless intentional."))
    else:
        out.append(_mk("a-robots","Meta robots","A-onpage","pass","ok",mrv or "indexable (no noindex)",src,mrv,"Indexable.",""))
    for prop in ["og:title","og:description","og:image","twitter:card"]:
        t = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
        out.append(_mk(f"a-{prop}","Open Graph/Twitter: "+prop,"A-onpage","pass" if t else "warning","ok" if t else "warning",
            (t.get("content","")[:120] if t else "missing"),src,(t.get("content","") if t else None),"Social previews depend on these tags.",f"Add <meta property=\"{prop}\">." if not t else ""))
    hls = soup.find_all("link", attrs={"rel": "hreflang"}) + soup.find_all("link", attrs={"rel": "alternate"})
    hreflangs = [l.get("hreflang","?")+":"+l.get("href","")[:80] for l in hls if l.get("hreflang") or l.get("href")]
    has_xd = any((l.get("hreflang")=="x-default") for l in hls)
    out.append(_mk("a-hreflang","hreflang","A-onpage","pass" if hreflangs else "info","ok" if hreflangs else "info",
        f"{len(hreflangs)} hreflang links" if hreflangs else "none declared",src,hreflangs[:10],"Only relevant for multi-locale sites.","Add hreflang cluster if site targets multiple languages." if not hreflangs else ""))
    # R: html lang + x-default
    html_tag = soup.find("html")
    lang = html_tag.get("lang","") if html_tag else ""
    out.append(_mk("r-lang","html lang attribute","R-intl","pass" if lang else "warning","ok" if lang else "warning",
        lang or "missing",src,lang,"Screen readers/translation rely on lang.",'Add <html lang="en"> (or locale).' if not lang else ""))
    out.append(_mk("r-xdefault","x-default hreflang","R-intl","pass" if has_xd else ("info" if not hreflangs else "warning"),
        "ok" if has_xd else "info", "present" if has_xd else ("n/a (no hreflang cluster)" if not hreflangs else "missing x-default"),
        src,hreflangs[:10],"x-default guides unmatched locales.","Add an x-default alternate." if hreflangs and not has_xd else ""))
    p = urlparse(url)
    url_ok = len(p.path or "/") < 100 and "_" not in (p.path or "")
    out.append(_mk("a-url","URL structure","A-onpage","pass" if url_ok else "warning","ok" if url_ok else "warning",
        p.path or "/",src,str(p.path),"Clean URLs aid crawl/click.","Shorten path, use hyphens." if not url_ok else ""))
    # G: content
    text = soup.get_text(separator=" ", strip=True)
    words = len([w for w in text.split() if w.strip()])
    code_len = max(len(html),1); text_len = len(text)
    ratio = round(100*text_len/code_len,1)
    if words < 300:
        out.append(_mk("g-wordcount","Word count / thin content","G-content","warning","warning",f"{words} words (thin <300)",src,{"words":words,"ratio":ratio},
            "Thin pages rarely satisfy intent.","Expand to cover the query intent (no filler)."))
    else:
        out.append(_mk("g-wordcount","Word count","G-content","pass","ok",f"{words} words, text:code {ratio}%",src,{"words":words,"ratio":ratio},"Depth OK.",""))
    return out

def keyword_match_checks(url: str, html: str, keyword: str | None) -> list[CheckResult]:
    if not keyword:
        return [unavailable("g-kw","Target keyword match","G-content","user input","no target keyword supplied for this audit","Enter a target keyword to enable.")]
    soup = soup_of(html); kw = keyword.lower()
    title = (soup.title.string or "").lower() if soup.title and soup.title.string else ""
    h1 = " ".join(h.get_text().lower() for h in soup.find_all("h1"))
    body = soup.get_text(separator=" ").lower()
    rows = [("title", kw in title, title[:120]), ("h1", kw in h1, h1[:120]), ("body", kw in body, f"occurrences: {body.count(kw)}")]
    out = []
    for where, hit, ev in rows:
        out.append(_mk(f"g-kw-{where}",f"Keyword in {where}","G-content","pass" if hit else "warning","ok" if hit else "warning",
            f"'{keyword}' {'found' if hit else 'NOT found'} in {where}", "page text (case-insensitive)", ev,
            "Keyword placement is a basic relevance check, not a ranking guarantee.", f"Include '{keyword}' naturally in {where}." if not hit else ""))
    return out

def content_stats_checks(html: str) -> list[CheckResult]:
    """Deterministic, locally computed content stats. No LLM, no estimates — pure counts.
    Qualitative AI review (if an endpoint is configured) is a separate sampled signal in K."""
    import re as _re
    src = "computed from page text (deterministic)"
    try:
        soup = soup_of(html)
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
    except Exception as e:
        return [unavailable("g-stats", "Content stats", "G-content", src, f"text extraction failed: {str(e)[:100]}")]
    words = [w for w in text.split() if w.strip()]
    sents = [_re.split(r"[.!?]+", p) for p in text.split("\n")]
    sents = [s.strip() for grp in sents for s in grp if s.strip()]
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    nw, ns = len(words), max(len(sents), 1)
    avg = round(nw / ns, 1)
    minutes = max(round(nw / 200, 1), 0.1)
    out = [
        _mk("g-readtime", "Reading time", "G-content", "info", "info",
            f"{nw} words ≈ {minutes} min at 200 wpm", src, {"words": nw, "minutes": minutes},
            "Reading time sets expectations for depth.", "Match depth to query intent; split long guides."),
        _mk("g-sentences", "Sentence length", "G-content", "warning" if avg > 25 else "pass", "warning" if avg > 25 else "ok",
            f"{len(sents)} sentences, avg {avg} words/sentence", src, {"sentences": len(sents), "avg_words": avg},
            "Long sentences hurt readability and comprehension.", "Shorten sentences to ~15-20 words." if avg > 25 else ""),
        _mk("g-paras", "Paragraph structure", "G-content", "info", "info",
            f"{len(paras)} text blocks", src, {"paragraphs": len(paras)},
            "Short blocks scan better on mobile.", "One idea per paragraph; use subheads every ~300 words."),
    ]
    return out

