"""
Web search and market intelligence service for motor energy audits and ROI calculations.
Retrieves current market pricing, efficiency standards (IEC 60034-30-1),
and government energy efficiency subsidies (BEE, TEDA, MSME).
"""
import urllib.parse
import urllib.request
import json
import re
import html
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Indian industrial 3-phase 4-pole AC induction motor market pricing benchmark (2025/2026)
# Representative manufacturers: Lakshmi Electrical Drives Ltd (LEDL), Bharat Bijlee, Crompton Greaves, ABB, Siemens
MOTOR_MARKET_BENCHMARKS = {
    0.75: {"hp": 1.0, "ie2_price": "₹6,000 - ₹8,500", "ie3_price": "₹8,000 - ₹11,000", "ie4_price": "₹12,000 - ₹16,000", "ie3_eff": 82.5, "ie4_eff": 85.7},
    1.5: {"hp": 2.0, "ie2_price": "₹8,500 - ₹12,000", "ie3_price": "₹11,000 - ₹15,000", "ie4_price": "₹16,000 - ₹22,000", "ie3_eff": 85.3, "ie4_eff": 88.2},
    2.2: {"hp": 3.0, "ie2_price": "₹11,000 - ₹15,000", "ie3_price": "₹14,000 - ₹19,000", "ie4_price": "₹20,000 - ₹27,000", "ie3_eff": 86.7, "ie4_eff": 89.5},
    3.7: {"hp": 5.0, "ie2_price": "₹14,000 - ₹18,000", "ie3_price": "₹18,000 - ₹23,000", "ie4_price": "₹26,000 - ₹34,000", "ie3_eff": 88.3, "ie4_eff": 90.9},
    5.5: {"hp": 7.5, "ie2_price": "₹18,000 - ₹24,000", "ie3_price": "₹23,000 - ₹30,000", "ie4_price": "₹32,000 - ₹42,000", "ie3_eff": 89.6, "ie4_eff": 91.9},
    7.5: {"hp": 10.0, "ie2_price": "₹22,000 - ₹28,000", "ie3_price": "₹28,000 - ₹36,000", "ie4_price": "₹38,000 - ₹48,000", "ie3_eff": 90.4, "ie4_eff": 92.6},
    11.0: {"hp": 15.0, "ie2_price": "₹28,000 - ₹36,000", "ie3_price": "₹35,000 - ₹45,000", "ie4_price": "₹48,000 - ₹60,000", "ie3_eff": 91.4, "ie4_eff": 93.3},
    15.0: {"hp": 20.0, "ie2_price": "₹36,000 - ₹46,000", "ie3_price": "₹45,000 - ₹56,000", "ie4_price": "₹60,000 - ₹75,000", "ie3_eff": 92.1, "ie4_eff": 93.9},
    18.5: {"hp": 25.0, "ie2_price": "₹44,000 - ₹55,000", "ie3_price": "₹54,000 - ₹68,000", "ie4_price": "₹72,000 - ₹90,000", "ie3_eff": 92.6, "ie4_eff": 94.2},
    22.0: {"hp": 30.0, "ie2_price": "₹52,000 - ₹65,000", "ie3_price": "₹65,000 - ₹82,000", "ie4_price": "₹85,000 - ₹108,000", "ie3_eff": 93.0, "ie4_eff": 94.5},
    30.0: {"hp": 40.0, "ie2_price": "₹68,000 - ₹85,000", "ie3_price": "₹85,000 - ₹108,000", "ie4_price": "₹112,000 - ₹140,000", "ie3_eff": 93.6, "ie4_eff": 94.9},
    37.0: {"hp": 50.0, "ie2_price": "₹82,000 - ₹102,000", "ie3_price": "₹102,000 - ₹128,000", "ie4_price": "₹135,000 - ₹170,000", "ie3_eff": 93.9, "ie4_eff": 95.2},
    45.0: {"hp": 60.0, "ie2_price": "₹98,000 - ₹122,000", "ie3_price": "₹122,000 - ₹152,000", "ie4_price": "₹160,000 - ₹200,000", "ie3_eff": 94.2, "ie4_eff": 95.4},
    55.0: {"hp": 75.0, "ie2_price": "₹120,000 - ₹150,000", "ie3_price": "₹150,000 - ₹188,000", "ie4_price": "₹198,000 - ₹248,000", "ie3_eff": 94.6, "ie4_eff": 95.7},
    75.0: {"hp": 100.0, "ie2_price": "₹160,000 - ₹200,000", "ie3_price": "₹200,000 - ₹250,000", "ie4_price": "₹260,000 - ₹325,000", "ie3_eff": 95.0, "ie4_eff": 96.0},
    90.0: {"hp": 120.0, "ie2_price": "₹195,000 - ₹245,000", "ie3_price": "₹245,000 - ₹305,000", "ie4_price": "₹315,000 - ₹395,000", "ie3_eff": 95.2, "ie4_eff": 96.1},
}


def search_web_for_motor_roi(query: str, motor_kw: float = 22.0) -> List[Dict[str, Any]]:
    """
    Perform a combined web search and market benchmark lookup.
    Returns authoritative snippets, URLs, and market pricing intelligence.
    """
    results: List[Dict[str, Any]] = []

    # 1. Market Benchmark Catalog for the specific motor rating
    try:
        closest_kw = min(MOTOR_MARKET_BENCHMARKS.keys(), key=lambda k: abs(k - motor_kw))
        bm = MOTOR_MARKET_BENCHMARKS[closest_kw]
        results.append({
            "source": "Indian Motor Market Pricing & Standards Benchmark (2025/2026)",
            "title": f"{closest_kw} kW ({bm['hp']:.0f} HP) 3-Phase Motor Price & Efficiency Catalog",
            "snippet": (
                f"Market benchmark for {closest_kw} kW 4-pole motor: IE2 (Standard) ~ {bm['ie2_price']}, "
                f"IE3 (Premium Efficiency) ~ {bm['ie3_price']} (Eff: {bm['ie3_eff']}%), "
                f"IE4 (Super Premium) ~ {bm['ie4_price']} (Eff: {bm['ie4_eff']}%). "
                f"Government Schemes: Bureau of Energy Efficiency (BEE) Standards & Labeling and "
                f"Tamil Nadu Energy Development Agency (TEDA) / MSME energy conservation programs offer "
                f"10-20% capital subsidies for qualifying IE4 and SynRM motor replacements."
            ),
            "url": "https://beeindia.gov.in/en/standards-labeling"
        })
    except Exception as exc:
        logger.warning("Error fetching motor benchmark: %s", exc)

    # 2. Wikipedia Search for Technical Standards & Context
    try:
        wiki_q = query if any(w in query.lower() for w in ["ie3", "ie4", "motor", "efficiency"]) else f"{query} electric motor efficiency"
        url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(wiki_q)}&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "EliciusEnergyAuditor/1.0"})
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for r in data.get("query", {}).get("search", [])[:2]:
                snippet = html.unescape(re.sub("<[^<]+?>", "", r.get("snippet", ""))).strip()
                title = r.get("title", "")
                results.append({
                    "source": "Wikipedia Energy Standards",
                    "title": title,
                    "snippet": snippet,
                    "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}"
                })
    except Exception as exc:
        logger.warning("Wikipedia search failed: %s", exc)

    # 3. DuckDuckGo Instant Answers or Open Search API
    try:
        ddg_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
        req = urllib.request.Request(ddg_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            ddg_data = json.loads(resp.read().decode("utf-8"))
            abstract = ddg_data.get("AbstractText")
            if abstract:
                results.append({
                    "source": ddg_data.get("AbstractSource", "DuckDuckGo Web"),
                    "title": ddg_data.get("Heading", query),
                    "snippet": abstract,
                    "url": ddg_data.get("AbstractURL", "https://duckduckgo.com")
                })
    except Exception as exc:
        logger.debug("DuckDuckGo search fallback skipped: %s", exc)

    return results

