#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build Fin4120 dual-pane beginner site from lecture extracts."""
from __future__ import annotations

import html
import pathlib
import re
from typing import List, Tuple, Dict, Optional

ROOT = pathlib.Path("/workspace/fin4120_beginner")
EXTRACT = pathlib.Path("/workspace/fin4120_extract")
MOD = ROOT / "modules"

MODULES = [
    {
        "id": "m0",
        "title": "导论：如何使用讲义原文+解析对照",
        "short": "双栏用法与学习路线",
        "deck": None,
        "file": None,
    },
    {
        "id": "m1",
        "title": "债券是什么 · Fundamentals of Bonds",
        "short": "定义、板块、要素、风险、报价",
        "deck": "Fundamentals of Bonds",
        "file": "01_fundamentals.txt",
    },
    {
        "id": "m2",
        "title": "债券怎么定价 · Pricing of Bonds",
        "short": "折现、票息-价格-收益率、干净价脏价",
        "deck": "Pricing of Bonds",
        "file": "02_pricing.txt",
    },
    {
        "id": "m3",
        "title": "收益率怎么算 · Yield of Bonds",
        "short": "各种 yield、组合、总回报与持有期",
        "deck": "Yield of Bonds",
        "file": "03_yield.txt",
    },
    {
        "id": "m4",
        "title": "国债与准国债 · Treasury Securities",
        "short": "美债种类、市场、STRIPS、GSE",
        "deck": "Treasury Securities",
        "file": "04_treasury.txt",
    },
    {
        "id": "m5",
        "title": "公司债 · Corporate Debt",
        "short": "三大支柱、清算瀑布、评级、CP/贷款",
        "deck": "Corporate Debt",
        "file": "05_corporate.txt",
    },
    {
        "id": "m6",
        "title": "国际债券 · International Bond",
        "short": "动机、市场分类、汇率对冲、指数",
        "deck": "International Bond",
        "file": "06_international.txt",
    },
    {
        "id": "m7",
        "title": "收益率曲线 · Yield Curve & Management",
        "short": "形状、PCA、理论、央行曲线管理",
        "deck": "Yield Curve & Yield Curve Management",
        "file": "07_yieldcurve.txt",
    },
    {
        "id": "m8",
        "title": "零息曲线怎么来 · Deriving Zero-Coupon Curve",
        "short": "样本筛选、bootstrap、插值、样条、NS",
        "deck": "Deriving The Zero-Coupon Yield Curve",
        "file": "08_zerocurve.txt",
    },
]

FOOTER_RE = re.compile(
    r"^\s*Fin\s*4120.*Prof\.?\s*Linlin\s*Ye.*\d*\s*$", re.I
)
PAGE_NUM_ONLY = re.compile(r"^\s*\d+\s*$")


def clean_page(raw: str) -> str:
    lines = []
    for ln in raw.splitlines():
        s = ln.rstrip()
        if FOOTER_RE.match(s.strip()):
            continue
        # light OCR fixes
        s = s.replace("tem s)", "terms)")
        s = s.replace("Insolvecie", "Insolvency")
        s = s.replace("Insolvecy", "Insolvency")
        lines.append(s)
    # collapse excessive blank lines
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def page_title(text: str) -> str:
    for ln in text.splitlines():
        t = ln.strip()
        if not t:
            continue
        if FOOTER_RE.match(t) or PAGE_NUM_ONLY.match(t):
            continue
        # compress whitespace
        t = re.sub(r"\s{2,}", " ", t)
        return t[:120]
    return "Slide"


def is_section_banner(text: str) -> bool:
    """True if mostly a big section title with little body."""
    body = re.sub(r"\s+", " ", text).strip()
    if len(body) < 80:
        return True
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) <= 3 and len(body) < 160:
        return True
    # ALL CAPS short titles
    if len(lines) <= 2 and lines and lines[0].isupper() and len(body) < 120:
        return True
    return False


def parse_chunks(path: pathlib.Path) -> List[Tuple[str, str]]:
    raw = path.read_text(encoding="utf-8")
    pages = [clean_page(p) for p in raw.split("\x0c")]
    # drop empty / reference-only trailing
    cleaned = []
    for p in pages:
        if not p:
            continue
        title = page_title(p).lower()
        if title in ("reference", "references") and len(p) < 200:
            continue
        cleaned.append(p)

    chunks: List[Tuple[str, str]] = []
    i = 0
    while i < len(cleaned):
        p = cleaned[i]
        # merge banner with following content page(s)
        if is_section_banner(p) and i + 1 < len(cleaned):
            title = page_title(p)
            body_parts = [cleaned[i + 1]]
            j = i + 2
            # optionally merge another tiny fragment
            while j < len(cleaned) and is_section_banner(cleaned[j]) is False:
                # stop if next looks like new numbered major section start AND we already have content
                nxt_title = page_title(cleaned[j])
                if re.match(r"^\d+\.\s", nxt_title) and len("\n".join(body_parts)) > 400:
                    break
                # don't absorb another full-size page into one mega-chunk unless banner was tiny
                if len(cleaned[j]) > 900 and len("\n".join(body_parts)) > 600:
                    break
                # only auto-merge one content page after banner by default
                break
            text = "\n\n".join(body_parts).strip()
            # if banner has unique words not in body, prepend
            if title.lower() not in text[:200].lower():
                text = title + "\n\n" + text
            chunks.append((title, text))
            i += 2
            continue
        title = page_title(p)
        chunks.append((title, p))
        i += 1

    # merge consecutive very short leftovers into next
    merged: List[Tuple[str, str]] = []
    k = 0
    while k < len(chunks):
        t, body = chunks[k]
        if len(body) < 100 and k + 1 < len(chunks) and not re.search(
            r"summary|quiz|roadmap", t, re.I
        ):
            t2, b2 = chunks[k + 1]
            merged.append((t if len(t) >= len(t2) else t2, (body + "\n\n" + b2).strip()))
            k += 2
            continue
        merged.append((t, body))
        k += 1
    return merged


# --------------- Explanation engine ---------------

def esc(s: str) -> str:
    return html.escape(s, quote=False)


def explain_for(mod_id: str, title: str, body: str) -> str:
    """Return HTML (no outer wrapper) Chinese explanation; not a verbatim copy."""
    t = title.lower()
    b = body.lower()
    parts: List[str] = []

    def add(p: str):
        parts.append(f"<p>{p}</p>")

    def kf(s: str):
        parts.append(f'<div class="kf">{esc(s)}</div>')

    def trap(s: str):
        parts.append(f'<div class="trap"><strong>易错点：</strong>{s}</div>')

    # --- generic routers by keywords ---
    if "roadmap" in t or "roadmap" in b[:300]:
        add("这一页是整份讲义的<strong>目录地图</strong>。先扫一眼各节标题，建立「这节课要解决什么问题」的心理框架，再进入细节。")
        add("建议学习法：每学完一节就回到这张 roadmap 打勾，避免只顾刷页码却不知道自己走到哪了。")
        return "\n".join(parts)

    if "summary" in t or "takeaway" in t:
        add("总结页请当成<strong>考前速查卡</strong>：能用自己的话复述每一条，才算真懂。")
        add("对照左边要点，问自己：对应公式是什么？适用假设是什么？常见反例是什么？")
        return "\n".join(parts)

    if "quick quiz" in t or t.startswith("quiz") or "quiz question" in t:
        add("先自己在草稿纸上答，再对答案。测验的价值在于暴露「以为懂了其实不会算」的缺口。")
        add("若卡住，回到该主题对应的讲义页，把符号定义抄一遍再重做。")
        return "\n".join(parts)

    if mod_id == "m1":
        if "what is a bond" in t or "i.o.u" in b or ("bond" in t and "what" in t):
            add("债券 = 借款人给你的 <strong>I.O.U.（欠条）</strong>：承诺定期付票息（coupon），到期还本金（principal / face / par）。")
            add("现金流时间线：前 N−1 期收票息 C；最后一期收 C + 面值 F。美国公司债常见每半年付一次息。")
            kf("CF_t = C (t < N);  CF_N = C + F")
            trap("「固定收益」≠ 零风险：票息合同可固定，但市价、通胀、违约、汇率仍会变。")
        elif "basic component" in t or "par value" in b and "coupon rate" in b:
            add("四大零件：<strong>Par Value</strong>（面值）、<strong>Coupon Rate</strong>（年票息率）、<strong>Maturity</strong>（到期）、<strong>Payment Frequency</strong>（付息频率）。")
            add("每期票息 ≈（票息率 × 面值）/ 年付息次数。美国常见面值 $1,000；中国国债常见面值 ¥100。")
            trap("票息率是合同写死的；收益率（yield）是按现价算出来的——两者只有在平价时才常相等。")
        elif "sector" in t or "regulator" in t:
            add("<strong>Sector</strong> = 按发行人/担保类型划分的市场板块。美国常见：Treasury、Agency、Municipal、Corporate、ABS/MBS、外国债/欧洲债等。")
            add("中国常见：国债、政策性银行债、公司债/企业债、商行债、ABS、熊猫债等。监管架构也不同：美国相对「机构分工」，中国更多「按品种分管」。")
            if "municipal" in b:
                add("市政债利息常有税收优惠，但<strong>免税 ≠ 无风险</strong>；GO（税收担保）与 Revenue（项目收入担保）风险来源不同。")
            if "regulator" in t or "sec" in b or "csrc" in b:
                add("看监管是为了理解：谁批准发行、谁管交易场所、违约时谁介入——这会影响流动性与信息透明度。")
        elif "special coupon" in t or "floating" in b and "coupon" in t:
            add("票息结构可以很花：固定、浮动（挂钩 SOFR/LPR 等）、零息、step-up、延期付息、PIK（用新债抵利息）等。")
            add("结构一变，利率风险与再投资风险的分配就会变——后面定价与收益率模块会反复用到。")
        elif "embedded option" in t or "callable" in b or "puttable" in b:
            add("嵌入期权改变「谁有提前终止权」：<strong>Callable</strong> 利好发行人；<strong>Puttable</strong> 利好投资者；还有 Convertible / Exchangeable 等。")
            trap("利率大降时，可赎回债容易被 call → 投资者面临再投资风险（call risk）。")
        elif "risk" in t or "main risks" in t:
            add("债券风险可粗分为两类：①市场/宏观（利率、通胀、汇率、曲线形态、波动）；②发行人/结构（信用违约、赎回、流动性、事件、税制变化）。")
            add("直觉：期限越长、票息越低，价格对利率越敏感；信用越差，利差补偿通常越高。")
        elif "identification" in t or "quoting" in t or "cusip" in b:
            add("报价记号例如「Coca-Cola 4.25s 5/15/2029」= 发行人 + 票息率 + 到期日。美国常用 <strong>CUSIP</strong> 识别码；跨境常用更长的 CINS 等。")
            add("记号往往不写付息频率——但美债公司债默认多半是半年付息，做题时要确认。")
        else:
            add(f"本页主题：<strong>{esc(title)}</strong>。先抓住左边的定义与分类清单，再问「这个概念会怎样影响价格或风险」。")
            add("把英文关键词圈出来（如 coupon、par、maturity），与术语表对照，方便以后直接读原课件。")

    elif mod_id == "m2":
        if "time value" in b or "vanilla" in t or "geometric" in b:
            add("定价第一性原理：债券价格 = 未来现金流的<strong>现值之和</strong>。利率越高，同样的未来钱今天越不值钱 → 价格越低。")
            kf("P = Σ C_t / (1+r)^t   +   F / (1+r)^N")
            add("等比数列求和公式是为了把「每期固定票息」收成闭式，考试常直接用年金公式加速计算。")
        elif "what is a yield" in t or ("yield" in t and "coupon" in t and "price" in t):
            add("<strong>Yield</strong> 是使模型价格等于市价的折现率（对息票债常称 YTM）。它把「价格」翻译成「年化回报语言」。")
            kf("Coupon ↑  →  Price ↑；  Yield ↑  →  Price ↓；  平价时 Yield ≈ Coupon Rate")
            trap("价格与收益率反向：利率升 → 旧债跌。不要把 coupon rate 当成你实际能锁定的回报。")
        elif "price-yield" in t or "relationship" in t:
            add("价格-收益率曲线是向下倾斜的凸曲线（convex）：收益率变动相同幅度时，价格上涨的幅度通常大于下跌幅度（正凸性）。")
            add("这解释了为什么「久期」只是一阶近似，大波动时还要看凸性修正。")
        elif "evolution" in t or "over time" in t or "pull to par" in b:
            add("即使收益率不变，折价债会随时间<strong>向面值靠拢（pull to par）</strong>；溢价债则逐渐回落至面值。")
            add("价格变化 = 时间流逝效应 + 收益率变动效应 +（若有）应计利息效应。分析时要拆开看。")
        elif "challenge" in t or "real-world" in t:
            add("现实难题：付息频率、节假日惯例、嵌入期权、信用风险、流动性折价、税收等都会让「教科书公式」需要调整。")
            add("课程后面会用更精细的折现曲线（零息曲线）来替代单一收益率假设。")
        elif "floater" in t or "inverse" in t:
            add("<strong>Floater</strong>（浮息债）票息随参考利率重置，久期通常较短，价格相对稳定。")
            add("<strong>Inverse floater</strong> 可理解为：固定票息债多头 + 浮息债空头的组合；杠杆放大利率敏感度。")
            kf("Fixed coupon bond ≈ Floater + Inverse floater  （在适当面值搭配下）")
            trap("逆浮息在利率上升时票息下降且价格往往更痛，风险不对称。")
        elif "clean" in t or "dirty" in t or "accrued" in b:
            add("<strong>Dirty price（全价）</strong> = 实际成交支付的钱；<strong>Clean price（净价）</strong> = 全价 − 应计利息，是行情常用报价。")
            kf("Dirty = Clean + Accrued Interest")
            trap("看到报价先问是 clean 还是 dirty；算回报时用的是你真正支付的 dirty price。")
        else:
            add(f"本页围绕定价主题「{esc(title)}」。核心仍是：选对现金流、选对折现率、注意计息惯例。")

    elif mod_id == "m3":
        if "irr" in t or "compute yield" in t:
            add("投资的 yield / IRR 是使 NPV=0 的折现率：把所有流出、流入放在时间轴上求解。")
            add("债券 YTM 就是把现价当作流出、票息与本金当作流入时的 IRR。通常需数值法（财务计算器 / Excel IRR）。")
            kf("0 = −P + Σ C_t/(1+y)^t + F/(1+y)^N")
        elif "various yield" in t or "current yield" in b or "ytm" in b or "ytc" in b:
            add("常见指标：Current Yield（年票息/市价）、YTM、YTC（按赎回价与赎回日算）、Yield to Worst、现金流收益率等。")
            add("可赎回债要同时看 YTM 与 YTC；发行人会选择对自己有利的时点，投资者应关注 <strong>yield to worst</strong>。")
            trap("Current yield 忽略本金损益与再投资，只能当粗指标。")
        elif "portfolio" in t or "floater" in t:
            add("组合收益率不是简单算术平均；更合理的是市值加权，或直接对组合现金流求 IRR。")
            add("浮息债常用 discount margin 等利差指标，而不是传统固定票息 YTM。")
        elif "total return" in t or "horizon" in t:
            add("<strong>Horizon analysis / total return</strong>：在给定持有期、再投资利率、期末卖出收益率假设下，估算实现总回报。")
            add("YTM 假设「持有到期 + 票息按 YTM 再投资」；一旦提前卖出或再投资利率不同，实现回报会偏离 YTM。")
            kf("Total future value = 再投资后的票息累积 + 期末卖出价；再换算持有期收益率")
        elif "tradeoff" in t or "trade-off" in b or "risk" in t:
            add("收益与风险权衡：追求更高 yield 往往意味着更长久期、更差信用或更低流动性。")
            add("没有免费的午餐——先问「多出来的那几百个 bp，买的是哪种风险？」")
        else:
            add(f"本页讲收益率度量「{esc(title)}」。先分清指标假设，再决定能不能拿来比较两只债券。")

    elif mod_id == "m4":
        if "key fact" in t or (t.strip().startswith("0") and "treasury" in b):
            add("美国国债通常被视为接近无信用风险的基准利率资产，市场规模大、流动性好，是全球定价锚。")
            add("关注：存量规模、所有权结构（国内外投资者）、以及它在折扣率/抵押品中的核心地位。")
        elif "types of treasur" in t:
            add("工具谱系：T-Bills（贴现短期）、T-Notes、T-Bonds、TIPS（通胀挂钩）、FRN 等；期限与计息方式不同。")
            add("TIPS 的实际收益率与名义国债之差近似 <strong>breakeven inflation</strong>（盈亏平衡通胀预期）。")
        elif "market structure" in t or "aspect" in t or "china" in t and "u.s" in t:
            add("美债市场：一级拍卖（Treasury auction）+ 二级 OTC 为主；有 when-issued（WI）市场做价格发现。")
            add("中美在托管、做市、投资者结构上有差异；比较表格时抓住「谁发行、谁交易、谁监管」。")
        elif "strip" in t:
            add("<strong>STRIPS</strong>：把附息国债的每笔票息与本金拆成独立零息债。无套利关系要求：附息债价格 ≈ 对应 STRIPS 包的价格之和。")
            kf("P_coupon bond ≈ Σ P_STRIP,i")
            trap("若拆开后更贵/更便宜，就存在重组或拆分套利空间（还需考虑摩擦与融资）。")
        elif "gse" in t or "agency" in t or "quasi" in t:
            add("GSE / Agency 证券：政府支持企业相关债务，信用介于国债与公司债之间，常带隐含或显性支持预期。")
            add("中国可对照政策性金融机构债等「准主权」品种，但法律支持力度并不相同，不能简单划等号。")
        else:
            add(f"本页属于国债模块「{esc(title)}」。记住：国债曲线是其它信用债定价的起点。")

    elif mod_id == "m5":
        if "three pillar" in t or "pillar" in b:
            add("公司债务三大支柱常被概括为：公司债券、中期票据（MTN）、商业票据（CP）/银行贷款等融资渠道——讲义按工具类型展开。")
            add("不同支柱在期限、信息披露、投资者群体、监管上不同，企业会「期限匹配」地选择融资。")
        elif "waterfall" in t or "liquidation" in t or "secured" in b:
            add("破产清偿大致优先级：<strong>Secured（有担保）≻ Unsecured senior ≻ Subordinated ≻ Equity</strong>。")
            add("同一层内部还可能有契约细节（担保品、保证、结构性后偿）。评级与价差高度依赖你在瀑布中的位置。")
            trap("「高级债」若无担保，仍可能损失惨重；看的是有效优先级与回收率，不只是名字。")
        elif "rating" in t or "notch" in t or "default" in t:
            add("评级是违约风险的「速记符号」；notch（如 A+ / A / A−）是微调。投资级 vs 投机级（高收益）是重要分界。")
            add("评级是滞后且离散的；市场信用利差往往更早反映恶化。历史违约率与回收率（recovery）用来粗估期望损失。")
            kf("Approx. expected loss ≈ default rate × (1 − recovery)")
        elif "traditional corporate" in t or "payment structure" in t or "coupon type" in t:
            add("公司债可按支付结构、票息类型、嵌入期权、担保情况分类。先画出现金流，再谈价差相对国债是多少。")
            add("契约条款（covenant）限制发行人行为，是信用分析的一部分，不只是看票息。")
        elif "medium-term" in t or "mtn" in t:
            add("<strong>MTN</strong> 是灵活的连续发行平台：发行人可在程序额度内选择币种、期限、结构，贴近投资者需求。")
            add("相对「一次到位的大额公募」，MTN 更强调定制与节奏控制。")
        elif "commercial paper" in t or t.strip().startswith("6."):
            if "commercial" in t or "cp" in b:
                add("<strong>CP</strong>：通常 ≤1 年的短期融资，属货币市场；很多以贴现发行。信用与展期（rollover）风险关键。")
                trap("CP 不是「短版债券」那么简单：披露、投资者、期限与监管框架都不同。")
            else:
                add(f"继续公司债工具谱系：{esc(title)}。")
        elif "bank loan" in t or "clo" in t:
            add("银行贷款常为浮动利率、可能有担保与严格契约；可被打包成 <strong>CLO</strong> 分层出售。")
            add("CLO 把信用风险切片：高层更安全、低层更厚收益更厚风险——本质是结构化优先级。")
        else:
            add(f"公司债主题「{esc(title)}」。始终问：现金流谁承诺、违约谁先赔、流动性够不够。")

    elif mod_id == "m6":
        if "motivation" in t or "diversification" in b:
            add("投国际债的动机：分散单一国家利率/信用风险、寻找更高实际收益、匹配外币负债等。")
            add("但分散化会被汇率波动「搅局」——后面必须谈 hedging。")
        elif "classification" in t or "eurobond" in b or "foreign bond" in b:
            add("常见分类：外国债（在某国国内市场、由外资发行人、以该国货币发行，如 Yankee / Samurai / Panda）vs <strong>Eurobond</strong>（在发行人母国以外、以离岸形式发行）。")
            add("也可按货币、发行人居住地、投资人类型划分。名字容易混，抓住「发行地 + 货币 + 监管」三要素。")
        elif "exchange" in t or "hedg" in t or "fx" in b:
            add("未对冲时，本币回报 ≈ 当地债券回报 + 汇率回报。外币升值增厚收益，贬值侵蚀收益。")
            kf("R_home ≈ R_local + R_FX")
            add("对冲可用远期/期货卖出外币本息；对冲后近似拿走利差，但有对冲成本（利率平价）。")
            trap("「当地债很香」可能只是货币风险溢价；对冲后超额收益可能消失。")
        elif "issuer" in t or "borrow" in t:
            add("谁能在国际市场借钱：主权、超主权、金融机构、公司等。准入取决于评级、披露与投资者需求。")
        elif "index" in t:
            add("全球债券指数决定被动资金的配置基准；纳入/剔除某国债券会引发大规模再平衡。")
            add("关注货币对冲指数 vs 未对冲指数——二者历史表现可差很多。")
        else:
            add(f"国际债主题「{esc(title)}」。跨境投资 = 利率观点 + 信用观点 + 汇率观点，三者要分开记账。")

    elif mod_id == "m7":
        if "interest rate" in t or "fisher" in b or "breakeven" in b or "tips" in b:
            add("Yield（YTM）常被当作该期限的市场利率锚。费雪关系粗略说：名义利率 ≈ 实际利率 + 预期通胀。")
            kf("i ≈ r + π^e")
            add("用名义国债与 TIPS 可估计盈亏平衡通胀。注意：还有通胀风险溢价与流动性溢价，不是纯预期。")
        elif "shape" in t or "increasing" in t or "decreasing" in t or "inverted" in b or "hump" in b:
            add("曲线形态：向上（正常）、平坦、倒挂（inverted）、驼峰等。倒挂常被当成衰退预警信号（短端高于长端）。")
            add("解释形态要结合：预期未来短端路径、期限溢价、供需与央行操作。")
            trap("倒挂是统计规律不是物理定律；要同时看倒挂深度与持续时间。")
        elif "over-time" in t or "propert" in t:
            add("曲线随时间移动：平行移动、变陡/变平、蝶式（弯曲）变化。风险管理常把这些模式分开做情景。")
            add("短端更受政策利率牵引，长端更受增长/通胀预期与量化宽松等存量影响。")
        elif "pca" in t or "eigen" in b or "factor" in b:
            add("<strong>PCA</strong> 显示国债收益率变动大部分可由少数因子解释，典型是 Level / Slope / Curvature。")
            kf("Δy ≈ β1·Level + β2·Slope + β3·Curvature")
            add("实务含义：组合风险可以按这三个「曲线动作」来表达，而不是看每一个到期日。")
        elif "theor" in t:
            add("经典理论：纯预期假说、流动性偏好（期限溢价为正）、分割市场假说等。它们给出「为什么长端通常更高」的不同故事。")
            add("现代观点常把收益率 = 预期短端路径 + 期限溢价；期限溢价可正可负。")
        elif "management" in t or "quantitative" in t or "qe" in b or "policy" in b or "reserves" in b:
            add("央行管理曲线：政策利率主要钉短端；QE/扭转操作等影响长端供需与期限溢价。")
            add("实体经济对长端利率更敏感（按揭、公司债融资）。在零利率下限附近，QE / 负利率成为工具箱选项。")
            kf("QE: 央行买入长久期债券 → 价格↑ → 长端 y↓")
        elif "why yield curve is" in t:
            add("曲线之所以重要：它是定价输入、宏观信号、政策传导渠道，也是银行净息差与风险偏好的关键变量。")
        else:
            add(f"收益率曲线主题「{esc(title)}」。先辨认形态，再解释「预期 vs 溢价 vs 供需」。")

    elif mod_id == "m8":
        if "coherent" in t or "basket" in t or "building" in t:
            add("构造零息曲线前，先筛<strong>干净样本</strong>：普通固息、流动性好、非异常报价；排除明显嵌入期权或特殊结构的券。")
            add("投票式「保留 / 剔除 / 再检查」是为了避免脏数据把曲线拧弯。")
        elif "linear system" in t or "direct method" in t:
            add("直接法：把每只券的定价方程写成对折现因子 B(0,t_i) 的线性关系，联立求解。")
            kf("P_j = Σ CF_{j,i} · DF(t_i)")
            add("若现金流日期不完全重合，需要插值或把问题变成「在函数空间里找一条曲线」。")
        elif "bootstrap" in t:
            add("<strong>Bootstrapping</strong>：从最短到期券开始，逐个剥离已知票息的现值，解出下一个折现因子。")
            add("步骤：已知更短 DF → 从附息债价格减去中间票息现值 → 剩余归到期本息 → 解 DF(T)。")
            trap("输入债券若含期权或流动性坑，bootstrap 会把误差一路传到长端。")
        elif "interpolation" in t or "fill in" in t:
            add("节点之间需要插值（线性即期、线性 DF、对数 DF、样条等）。不同插值会改变中间期限的远期利率平滑度。")
            add("线性插值即期利率假设曲率为零，可能造成远期不稳定；这是作业里常见的「插值 vs 直接 bootstrap」对比点。")
            trap("插值只是假设，不是市场真相；换插值方法，中间券的模型价可能跳几个 bp。")
        elif "indirect" in t or "general problem" in t or "least square" in b or "weight" in b:
            add("间接法：不逐点硬解，而是指定折现函数/即期函数的参数形式，最小化定价误差（常加权最小二乘）。")
            add("权重可按久期、流动性或买卖价差设计，避免「脏券」主导拟合。")
        elif "spline" in t:
            add("样条（如立方样条）用分段多项式拟合 DF 或利率，在节点处保持光滑。灵活，但要防过度拟合与远期振荡。")
            add("实务会加形状约束（正远期、平滑惩罚）。看讲义里的拟合步骤时，抓住「选节点 → 基函数 → 解系数」。")
        elif "nelson" in t or "siegel" in t or "parametric" in t:
            add("<strong>Nelson-Siegel</strong> 用少数参数刻画水平、斜率、曲率成分，整条曲线参数化，稳健且便于比较不同日曲线。")
            kf("y(τ) = β0 + β1·((1−e^{−λτ})/(λτ)) + β2·(((1−e^{−λτ})/(λτ)) − e^{−λτ})")
            add("扩展的 Svensson 模型再加一项，以捕捉更复杂的驼峰。参数有经济直觉，适合日常监控。")
        elif "discussion" in t:
            add("讨论页通常对比方法的偏差-方差权衡：直接 bootstrap 贴合样本但粗糙；参数法平滑但可能系统性误价某些券。")
            add("选择取决于用途：交易 desk 要贴市；风险管理要稳与可解释。")
        else:
            add(f"零息曲线主题「{esc(title)}」。目标始终是得到一致的折现因子 DF(t)，以便给任意现金流定价。")

    else:
        add(esc(title))

    if not parts:
        add(f"对照左边讲义原文阅读「{esc(title)}」。用自己的话写下：定义、公式、一个数字例子、一个反例。")

    # Always add a gentle study tip for dense pages
    if len(body) > 900 and "trap" not in "\n".join(parts):
        parts.append(
            '<div class="trap"><strong>学习提示：</strong>本页信息密度高，先标出 2–3 个核心公式/定义，再回头啃例子。</div>'
        )
    return "\n".join(parts)


def dual_block(anchor: str, title: str, lecture: str, explain_html: str) -> str:
    return f'''
<p class="section-anchor" id="{esc(anchor)}">§ {esc(title)}</p>
<div class="dual-block">
  <section class="pane lecture" aria-label="讲义原文">
    <div class="pane-label">讲义原文</div>
    <div class="pane-body">
      <h3 class="lecture-title">{esc(title)}</h3>
      <pre class="lecture-text">{esc(lecture)}</pre>
    </div>
  </section>
  <section class="pane explain" aria-label="解析">
    <div class="pane-label">解析</div>
    <div class="pane-body explain-body">
      {explain_html}
    </div>
  </section>
</div>
'''


def nav_html(idx: int) -> str:
    prev_m = MODULES[idx - 1] if idx > 0 else None
    next_m = MODULES[idx + 1] if idx + 1 < len(MODULES) else None
    left = (
        f'<a href="{prev_m["id"]}.html"><span class="dir">上一模块</span>{esc(prev_m["title"].split("·")[0].strip())}</a>'
        if prev_m
        else "<span></span>"
    )
    right = (
        f'<a href="{next_m["id"]}.html"><span class="dir">下一模块</span>{esc(next_m["title"].split("·")[0].strip())}</a>'
        if next_m
        else '<a href="../index.html"><span class="dir">完成</span>返回学习路径</a>'
    )
    return f'<div class="nav-mod">{left}{right}</div>'


def page_shell(mod: dict, idx: int, body: str, extra_head: str = "") -> str:
    mid = mod["id"]
    title = mod["title"]
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>模块 {mid[1:]} · {esc(title)} · Fin4120 零基础学习站</title>
<link rel="stylesheet" href="../assets/style.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"
  onload="renderMathInElement(document.body, {{delimiters:[{{left:'$$',right:'$$',display:true}},{{left:'$',right:'$',display:false}}],throwOnError:false}});"></script>
{extra_head}
</head>
<body>
<header class="site">
  <div class="inner">
    <a class="brand" href="../index.html">Fin4120 零基础固收</a>
    <nav>
      <a href="../index.html">学习路径</a>
      <a href="../glossary.html">术语表</a>
      <a href="../index.html#progress">进度</a>
    </nav>
  </div>
</header>
<div class="wrap wide">
  <p class="muted"><a href="../index.html">← 返回首页</a></p>
  <h1 class="mod-title">模块 {mid[1:]} · {esc(title)}</h1>
  {body}
  <div class="card checklist">
    <label>
      <input type="checkbox" data-module-check="{mid}">
      <span>我已完成本模块（对照讲义原文 + 解析），标记进度</span>
    </label>
  </div>
  {nav_html(idx)}
</div>
<footer class="site">
  <p>讲义原文摘自港中深 <strong>Fin4120 Fixed Income Securities</strong>（Prof. Linlin Ye, CUHKSZ），仅供个人学习对照。右侧解析为学习辅助改写，不构成对原课件的署名主张。</p>
</footer>
<script src="../assets/app.js"></script>
</body>
</html>
'''


def build_m0() -> str:
    body = '''
<div class="source-note">本模块无对应单份幻灯片；说明如何使用「左讲义原文 / 右解析」双栏学习法。</div>
<div class="dual-legend">
  <span><i class="dot L"></i> 左侧：讲义原文（英文为主，保留术语）</span>
  <span><i class="dot R"></i> 右侧：零基础解析（中文 + 公式 + 易错点）</span>
</div>
<div class="card">
  <h2>怎么用这个站点</h2>
  <ol>
    <li>先扫右侧解析，建立直觉；再读左侧原文，对齐老师课件用语。</li>
    <li>桌面端两栏并排，可各自滚动；手机端变为「先原文、后解析」的区块堆叠。</li>
    <li>每学完一个模块，底部打卡；首页进度条会更新（存在本机浏览器）。</li>
    <li>遇到生词，打开 <a href="../glossary.html">术语表</a>；术语也会在讲义原文栏原样出现。</li>
  </ol>
</div>
<div class="callout tip">
  <div class="label">学习顺序</div>
  模块 1→3 打地基（工具、定价、收益率）→ 4→6 认识市场产品 → 7→8 曲线与零息构造。不要跳过 2/3 直接啃 8。
</div>
<div class="card">
  <h2>你会反复用到的三个直觉</h2>
  <ul class="clean">
    <li><strong>利率 ↑ → 旧债价格 ↓</strong></li>
    <li><strong>票息率 ≠ 收益率</strong>（除非大致平价）</li>
    <li><strong>多出来的收益，通常买的是某种风险</strong>（久期 / 信用 / 流动性 / 汇率）</li>
  </ul>
</div>
<div class="card">
  <h2>八份讲义对照表</h2>
  <table class="simple">
    <tr><th>模块</th><th>讲义</th></tr>
    <tr><td>m1</td><td>Fundamentals of Bonds</td></tr>
    <tr><td>m2</td><td>Pricing of Bonds</td></tr>
    <tr><td>m3</td><td>Yield of Bonds</td></tr>
    <tr><td>m4</td><td>Treasury Securities</td></tr>
    <tr><td>m5</td><td>Corporate Debt</td></tr>
    <tr><td>m6</td><td>International Bond</td></tr>
    <tr><td>m7</td><td>Yield Curve &amp; Management</td></tr>
    <tr><td>m8</td><td>Deriving Zero-Coupon Curve</td></tr>
  </table>
</div>
'''
    return body


def build_module_from_extract(mod: dict, idx: int) -> None:
    mid = mod["id"]
    if mid == "m0":
        html_out = page_shell(mod, idx, build_m0())
        (MOD / f"{mid}.html").write_text(html_out, encoding="utf-8")
        print(f"wrote {mid} (orientation)")
        return

    chunks = parse_chunks(EXTRACT / mod["file"])
    # skip pure title cover if first chunk is cover
    if chunks and len(chunks[0][1]) < 120 and "roadmap" not in chunks[0][0].lower():
        chunks = chunks[1:]

    toc_items = []
    blocks = []
    for n, (title, body) in enumerate(chunks, 1):
        anchor = f"s{n}"
        toc_items.append(f'<a href="#{anchor}">{n}. {esc(title[:80])}</a>')
        expl = explain_for(mid, title, body)
        blocks.append(dual_block(anchor, title, body, expl))

    intro = f'''
<div class="source-note">
  <strong>Source:</strong> Fin4120 slides — <em>{esc(mod["deck"])}</em>, Prof. Linlin Ye (CUHKSZ) — for personal study.
  左侧为讲义文本摘录（按幻灯片分页整理）；右侧为学习解析，非讲义原文照搬。
</div>
<div class="dual-legend">
  <span><i class="dot L"></i> 讲义原文</span>
  <span><i class="dot R"></i> 解析（中文）</span>
</div>
<div class="card">
  <h2>本模块目录（共 {len(chunks)} 节）</h2>
  <div class="toc-dual">
    {"".join(toc_items)}
  </div>
</div>
'''
    html_out = page_shell(mod, idx, intro + "\n".join(blocks))
    (MOD / f"{mid}.html").write_text(html_out, encoding="utf-8")
    print(f"wrote {mid}: {len(chunks)} sections from {mod['file']}")


def write_index():
    cards = []
    for m in MODULES:
        cards.append(f'''<a class="mod-card" data-mod-card="{m["id"]}" href="modules/{m["id"]}.html">
  <div class="num">模块 {m["id"][1:]} <span data-done-mark="{m["id"]}"></span></div>
  <h3>{esc(m["title"].split("·")[0].strip())}</h3>
  <p>{esc(m["short"])}</p>
</a>''')
    text = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>学习路径 · Fin4120 零基础学习站</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="site">
  <div class="inner">
    <a class="brand" href="index.html">Fin4120 零基础固收</a>
    <nav>
      <a href="index.html">学习路径</a>
      <a href="glossary.html">术语表</a>
      <a href="index.html#progress">进度</a>
    </nav>
  </div>
</header>

<div class="wrap">
  <section class="hero">
    <div class="badge">CUHKSZ · Fin4120 · 讲义原文 + 解析对照</div>
    <h1>固定收益证券：左原文 · 右解析</h1>
    <p>把叶琳琳老师（Prof. Linlin Ye）Fin4120 八份讲义做成<strong>双栏对照</strong>：左边是讲义原文摘录，右边是零基础中文解析与公式直觉。共 9 个模块（含导论）。</p>
    <p style="opacity:.9">桌面端左右并排；手机端按「每一节：先原文、后解析」堆叠。</p>
  </section>

  <div class="card">
    <h2 id="progress">我的学习进度</h2>
    <p class="muted" data-progress-text>0 / 9 模块已完成（0%）</p>
    <div class="progress-bar-wrap"><div class="progress-bar" data-progress-bar></div></div>
    <p class="muted">进度存在本机浏览器，换设备不会同步。</p>
  </div>

  <div class="card">
    <h2>怎么读双栏</h2>
    <ul class="clean">
      <li><strong>讲义原文</strong>：保留课件英文术语与结构，便于和 PDF 对照。</li>
      <li><strong>解析</strong>：中文讲解、关键公式、易错点；不是把左边再抄一遍。</li>
      <li>建议顺序：先看解析建立直觉，再精读原文标记老师原话。</li>
    </ul>
  </div>

  <h2>推荐学习路线</h2>
  <div class="road">
    <div class="step"><span class="n">0</span><div><strong>导论</strong> — 双栏用法与名词直觉</div></div>
    <div class="step"><span class="n">1</span><div><strong>债券是什么</strong> — Fundamentals</div></div>
    <div class="step"><span class="n">2</span><div><strong>怎么定价</strong> — Pricing</div></div>
    <div class="step"><span class="n">3</span><div><strong>收益率</strong> — Yield</div></div>
    <div class="step"><span class="n">4–6</span><div><strong>市场工具</strong> — Treasury → Corporate → International</div></div>
    <div class="step"><span class="n">7–8</span><div><strong>曲线</strong> — Yield Curve → Zero Curve</div></div>
  </div>

  <div class="grid" style="margin-top:1.4rem">
{"".join(cards)}
  </div>

  <div class="card" style="margin-top:1.6rem">
    <h2>使用说明</h2>
    <ul class="clean">
      <li>每模块含：讲义原文分节 + 对应解析、目录锚点、进度打卡、上一/下一模块。</li>
      <li>术语亦可在 <a href="glossary.html">全站术语表</a> 查阅；讲义原文栏会出现同样的英文词。</li>
      <li>源讲义：Fin4120 lecture slides by Prof. Linlin Ye (CUHKSZ)。原文归授课教师；本站解析为个人学习辅助。</li>
    </ul>
  </div>
</div>

<footer class="site">
  <p>讲义原文摘自港中深 <strong>Fin4120 Fixed Income Securities</strong>（Prof. Linlin Ye, CUHKSZ）。本站为教育用途的原文+解析对照，非官方教材，请勿替代原课件。</p>
  <p>本地进度保存在浏览器 localStorage，不会上传。</p>
</footer>
<script src="assets/app.js"></script>
</body>
</html>
'''
    (ROOT / "index.html").write_text(text, encoding="utf-8")
    print("wrote index.html")


def patch_glossary():
    path = ROOT / "glossary.html"
    text = path.read_text(encoding="utf-8")
    note = '<p class="muted">按英文字母序。定义以 Fin4120 讲义概念为准，做了零基础改写。模块页左侧「讲义原文」中也会出现同一批英文术语，可对照阅读。</p>'
    text2 = re.sub(
        r'<p class="muted">按英文字母序。.*?</p>',
        note,
        text,
        count=1,
        flags=re.S,
    )
    path.write_text(text2, encoding="utf-8")
    print("patched glossary.html")


def main():
    MOD.mkdir(parents=True, exist_ok=True)
    for i, m in enumerate(MODULES):
        build_module_from_extract(m, i)
    write_index()
    patch_glossary()
    print("DONE")


if __name__ == "__main__":
    main()
