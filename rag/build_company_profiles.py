from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from tools.fundamentals import fetch_fundamentals

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPANY_DOCS_DIR = PROJECT_ROOT / "rag" / "docs" / "companies"

TOP_10_SP500 = [
    "NVDA",
    "AAPL",
    "MSFT",
    "AMZN",
    "GOOGL",
    "GOOG",
    "AVGO",
    "META",
    "TSLA",
    "BRK-B",
]

PROFILE_NOTES: dict[str, dict[str, str]] = {
    "NVDA": {
        "biz_model": "NVIDIA sells GPUs, accelerated computing platforms, networking products, and software used across data centers, AI training and inference, gaming, professional visualization, automotive, and edge computing. Its data center segment is the main growth engine, supported by AI accelerator demand and an expanding software ecosystem.",
        "moat": "The moat is built around GPU architecture leadership, CUDA and developer ecosystem lock-in, high-performance networking, scale advantages, and deep relationships with cloud providers, hyperscalers, enterprises, and OEM partners.",
        "market_context": "The key market context is AI infrastructure buildout. Demand is tied to hyperscaler capex, enterprise AI adoption, inference workloads, supply availability, and competitive pressure from custom silicon and alternative accelerators.",
        "risks": "Key risks include valuation compression, semiconductor cyclicality, export restrictions, customer concentration, supply constraints, and the possibility that AI infrastructure spending normalizes after a major buildout cycle.",
        "portfolio_role": "Quality growth and AI infrastructure exposure; usually a growth satellite or large-cap technology core position depending on risk appetite.",
    },
    "AAPL": {
        "biz_model": "Apple generates revenue through iPhone, Mac, iPad, Wearables, and high-margin Services such as App Store, iCloud, Apple Music, Apple TV+, payments, licensing, and subscriptions. The company monetizes a large installed base through an integrated hardware-software-services ecosystem.",
        "moat": "Apple's moat comes from brand strength, high switching costs, proprietary iOS ecosystem, custom silicon, retail reach, privacy positioning, and tight integration across devices and services.",
        "market_context": "The smartphone market is mature, so growth depends on premium upgrades, services monetization, emerging markets, wearables, and AI-enabled device refresh cycles. Apple Intelligence is an important catalyst but the company is watched closely for execution versus AI leaders.",
        "risks": "Key risks include regulatory pressure on App Store economics, China manufacturing and demand exposure, slower upgrade cycles, FX headwinds, and potential disruption from AI-native devices or new computing interfaces.",
        "portfolio_role": "Quality compounder and mega-cap technology core holding; suitable for balanced and quality-oriented portfolios.",
    },
    "MSFT": {
        "biz_model": "Microsoft generates revenue from cloud infrastructure, productivity software, enterprise subscriptions, Windows, security, LinkedIn, gaming, and AI services. Azure and Microsoft 365 are central recurring revenue engines.",
        "moat": "The moat is built on enterprise distribution, switching costs, developer tools, Windows and Office ecosystems, Azure scale, security platform breadth, and deep AI integration through Copilot and cloud services.",
        "market_context": "Microsoft is positioned at the intersection of enterprise cloud migration, AI adoption, productivity automation, cybersecurity, and developer infrastructure. AI monetization and Azure growth are key market debates.",
        "risks": "Key risks include cloud growth deceleration, AI capex pressure, margin dilution from infrastructure investment, regulatory scrutiny, cybersecurity incidents, and intense competition from AWS, Google Cloud, and open-source AI ecosystems.",
        "portfolio_role": "Quality growth core position with enterprise software and cloud exposure; often suitable for balanced, growth, and quality portfolios.",
    },
    "AMZN": {
        "biz_model": "Amazon operates e-commerce marketplaces, first-party retail, Prime subscriptions, advertising, logistics, devices, and AWS cloud infrastructure. AWS and advertising are major profit drivers compared with lower-margin retail operations.",
        "moat": "Amazon's moat comes from logistics scale, Prime membership flywheel, marketplace network effects, AWS infrastructure depth, advertising data, and strong customer habituation.",
        "market_context": "Market context includes cloud AI workloads, retail margin recovery, advertising growth, logistics efficiency, and consumer spending. AWS growth and AI infrastructure demand are critical catalysts.",
        "risks": "Key risks include retail margin pressure, cloud competition, regulatory and antitrust scrutiny, labor costs, consumer slowdown, and heavy capital expenditure requirements.",
        "portfolio_role": "Growth and platform exposure with both consumer and cloud drivers; usually a growth satellite or core mega-cap position.",
    },
    "GOOGL": {
        "biz_model": "Alphabet generates most revenue from Google Search, YouTube, network advertising, subscriptions, devices, and Google Cloud. Search advertising remains the core profit engine, while Cloud and YouTube provide growth diversification.",
        "moat": "The moat is based on search distribution, data scale, AI research depth, YouTube network effects, Android ecosystem reach, and high-margin advertising infrastructure.",
        "market_context": "Alphabet faces a major transition as generative AI changes search behavior and advertising workflows. Google Cloud, AI infrastructure, YouTube monetization, and regulatory outcomes are key debates.",
        "risks": "Key risks include antitrust remedies, search distribution changes, AI disruption to search monetization, ad cycle sensitivity, cloud competition, and rising AI compute costs.",
        "portfolio_role": "Large-cap quality growth exposure to digital advertising, AI, and cloud; suitable for balanced, growth, and quality portfolios.",
    },
    "GOOG": {
        "biz_model": "Alphabet Class C shares represent economic exposure to the same Alphabet business: Search, YouTube, Google Cloud, Android, subscriptions, devices, and other bets.",
        "moat": "The moat mirrors Alphabet's broader advantages: search dominance, data scale, AI capabilities, YouTube, Android distribution, and advertising infrastructure.",
        "market_context": "The market context is driven by generative AI's impact on search, Google Cloud growth, YouTube monetization, regulatory remedies, and AI capex efficiency.",
        "risks": "Key risks include antitrust pressure, AI-driven search disruption, ad cyclicality, rising infrastructure costs, and competition from cloud and AI-native products.",
        "portfolio_role": "Same business exposure as GOOGL; usually use one Alphabet share class in a portfolio to avoid duplicate exposure unless intentionally mirroring index weights.",
    },
    "AVGO": {
        "biz_model": "Broadcom sells semiconductor solutions and infrastructure software. Its chips serve networking, broadband, wireless, storage, and AI data center use cases, while software assets add recurring enterprise revenue.",
        "moat": "Broadcom's moat comes from mission-critical chip franchises, customer relationships, scale, high switching costs in infrastructure software, disciplined M&A integration, and strong free cash flow generation.",
        "market_context": "Broadcom is tied to AI networking, custom silicon, data center connectivity, VMware integration, and enterprise infrastructure spending. AI-related semiconductor demand is a major catalyst.",
        "risks": "Key risks include integration risk, customer concentration, semiconductor cyclicality, regulatory scrutiny around acquisitions, and valuation sensitivity after AI-driven multiple expansion.",
        "portfolio_role": "Quality growth and semiconductor infrastructure exposure; useful as a technology satellite with income/free-cash-flow characteristics.",
    },
    "META": {
        "biz_model": "Meta generates most revenue from advertising across Facebook, Instagram, Messenger, WhatsApp, and Reels, with additional investments in AI infrastructure, business messaging, and Reality Labs.",
        "moat": "Meta's moat is built on massive social graphs, advertiser scale, engagement data, AI ranking systems, distribution across multiple apps, and high operating leverage in advertising.",
        "market_context": "Market context includes digital ad demand, AI-driven ad targeting and content recommendations, Reels monetization, business messaging, and the cost discipline versus metaverse investment debate.",
        "risks": "Key risks include regulatory scrutiny, privacy changes, platform competition, content moderation costs, Reality Labs losses, and cyclicality in advertising budgets.",
        "portfolio_role": "Growth and cash-flow compounder tied to digital advertising and AI monetization; suitable for growth and balanced portfolios.",
    },
    "TSLA": {
        "biz_model": "Tesla generates revenue from electric vehicles, energy generation and storage, services, software features, charging, and regulatory credits. The long-term thesis often includes autonomy, robotics, and energy storage optionality.",
        "moat": "Tesla's moat includes brand, manufacturing learning curve, EV software integration, charging network, battery and powertrain know-how, and real-world driving data for autonomy development.",
        "market_context": "The EV market is increasingly competitive, with pricing pressure, changing subsidies, China competition, and slower adoption in some regions. Autonomy, robotaxi, energy storage, and margin recovery are key catalysts.",
        "risks": "Key risks include valuation sensitivity, EV margin pressure, execution risk in autonomy, competition from Chinese and legacy automakers, key-person risk, regulatory scrutiny, and demand cyclicality.",
        "portfolio_role": "High-volatility growth satellite; better suited for aggressive portfolios than conservative portfolios.",
    },
    "BRK-B": {
        "biz_model": "Berkshire Hathaway is a diversified holding company with insurance, railroad, energy, manufacturing, retail, services, and a large public equity portfolio. Insurance float and operating cash flows fund long-term capital allocation.",
        "moat": "The moat comes from insurance float, decentralized operating culture, conservative balance sheet, disciplined capital allocation, tax-efficient compounding, and diversified operating businesses.",
        "market_context": "Berkshire is often viewed as a defensive quality compounder. Market context includes insurance underwriting cycles, interest income on cash, railroad/energy performance, equity portfolio exposure, and succession execution.",
        "risks": "Key risks include succession risk, large cash drag if opportunities are limited, insurance catastrophe losses, equity market exposure, and slower growth due to Berkshire's size.",
        "portfolio_role": "Defensive quality core or ballast position; useful for balanced, defensive, and quality portfolios.",
    },
}


def _fmt(value: Any, suffix: str = "") -> str:
    if value in (None, "", []):
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4g}{suffix}"
    return f"{value}{suffix}"


def _front_matter(ticker: str, fundamentals: dict[str, Any]) -> str:
    return "\n".join(
        [
            "---",
            f"ticker: {ticker}",
            f"company: {fundamentals.get('company_name') or PROFILE_NOTES[ticker]['biz_model'].split(' ')[0]}",
            f"sector: {fundamentals.get('sector') or 'n/a'}",
            f"industry: {fundamentals.get('industry') or 'n/a'}",
            "doc_type: company_note",
            f"generated_at: {date.today().isoformat()}",
            "status: draft_for_manual_review",
            "---",
            "",
        ]
    )


def build_markdown(ticker: str, fundamentals: dict[str, Any]) -> str:
    notes = PROFILE_NOTES[ticker]
    company = fundamentals.get("company_name") or ticker
    lines = [
        _front_matter(ticker, fundamentals),
        f"# {company} ({ticker})",
        "",
        "> Draft company knowledge base note for manual review. Dynamic financial figures should be rechecked before publication.",
        "",
        "## Snapshot",
        "",
        f"- Sector: {_fmt(fundamentals.get('sector'))}",
        f"- Industry: {_fmt(fundamentals.get('industry'))}",
        f"- Country: {_fmt(fundamentals.get('country'))}",
        f"- Market cap: {_fmt(fundamentals.get('market_cap_fmt'))}",
        f"- Revenue TTM: {_fmt(fundamentals.get('revenue_ttm_fmt'))}",
        f"- Gross margin: {_fmt(fundamentals.get('gross_margin'))}",
        f"- Operating margin: {_fmt(fundamentals.get('operating_margin'))}",
        f"- Net margin: {_fmt(fundamentals.get('net_margin'))}",
        f"- Forward P/E: {_fmt(fundamentals.get('pe_forward'))}",
        f"- Beta: {_fmt(fundamentals.get('beta'))}",
        f"- Analyst recommendation: {_fmt(fundamentals.get('analyst_recommendation'))}",
        "",
        "## Business Summary",
        "",
        fundamentals.get("description") or "No yfinance business description available.",
        "",
        "## Business Model",
        "",
        notes["biz_model"],
        "",
        "## Moat",
        "",
        notes["moat"],
        "",
        "## Market Context",
        "",
        notes["market_context"],
        "",
        "## Key Risks",
        "",
        notes["risks"],
        "",
        "## Portfolio Role",
        "",
        notes["portfolio_role"],
        "",
        "## Data Notes",
        "",
        "This note combines current yfinance fundamentals with internal draft narrative notes. It is intended for RAG context only and must not override deterministic scoring, portfolio weights, or live market data.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Build draft company KB markdown files for top S&P 500 companies.")
    parser.add_argument("--tickers", nargs="*", default=TOP_10_SP500)
    parser.add_argument("--out-dir", default=str(COMPANY_DOCS_DIR))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for ticker in args.tickers:
        normalized = ticker.upper().replace(".", "-")
        if normalized not in PROFILE_NOTES:
            print(f"skip {ticker}: no draft notes configured")
            continue
        try:
            fundamentals = fetch_fundamentals(normalized)
        except Exception as exc:
            print(f"warn {normalized}: fundamentals unavailable ({exc})")
            fundamentals = {"ticker": normalized}

        path = out_dir / f"{normalized}.md"
        path.write_text(build_markdown(normalized, fundamentals), encoding="utf-8")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
