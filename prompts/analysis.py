"""
Loads analysis.xml and renders it with market data.
To change the prompt — edit analysis.xml only.
"""

from pathlib import Path
import xml.etree.ElementTree as ET


def build_prompt(p: dict, f: dict, news_text: str) -> str:
    xml_path = Path(__file__).parent / "analysis.xml"
    tree = ET.parse(xml_path)
    root = tree.getroot()

    def text(tag: str) -> str:
        el = root.find(tag)
        return el.text.strip() if el is not None and el.text else ""

    role = text("role")
    price_block = text("market_data/price").format(price=p)
    fund_block = text("market_data/fundamentals").format(fund=f)
    news_block = text("market_data/news").format(news=news_text)
    instructions = text("output_instructions")

    return f"""<role>
{role}
</role>

<market_data>
<price>
{price_block}
</price>

<fundamentals>
{fund_block}
</fundamentals>

<news>
{news_block}
</news>
</market_data>

<output_instructions>
{instructions}
</output_instructions>
"""
