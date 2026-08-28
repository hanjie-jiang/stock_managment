"""English/Chinese text for the dashboard: static UI strings, plus templates
for the structured reason codes stock_toolkit.signals produces.

Kept as a plain module next to ui_common.py, not inside stock_toolkit -- this
is presentation, same reasoning ui_common.py already gives for staying
outside the toolkit package. See specs/001-bilingual-en-zh-toggle.md.
"""

import streamlit as st

STRINGS = {
    "en": {
        "app_title": "Family Stock Tracker",
        "nav_dashboard": "Stock Dashboard",
        "nav_briefing": "Today's Briefing",
        "add_stock_prompt": "Add a stock from the left panel to get started.",
        "language_label": "Language",
        "your_stocks": "Your stocks ({count})",
        "remove_confirm": "Remove **{name}**?",
        "yes_remove": "Yes, remove",
        "cancel": "Cancel",
        "add_a_stock": "Add a stock",
        "type_company_name": "Type a company name",
        "type_company_placeholder": "e.g. Apple, Tencent, Moutai",
        "no_matches": "No matches found. Try a different spelling.",
        "add_button": "Add {label}",
        "looking_up_industry": "Looking up industry...",
        "na": "n/a",
        "choose_stock": "Choose a stock to look at:",
        "fetching_data": "Fetching the latest data for {symbol}...",
        "current_price": "Current price",
        "risk_level": "Risk level",
        "long_term_fit": "Long-term fit",
        "signal_prefix": "Signal: {lean}",
        "tab_overview": "Overview",
        "tab_reasons": "Why?",
        "tab_report": "Latest Quarter",
        "tab_compare": "Compare",
        "price_history": "Price history",
        "time_range": "Time range",
        "period_1mo": "1 Month",
        "period_6mo": "6 Months",
        "period_1y": "1 Year",
        "period_5y": "5 Years",
        "no_price_history": "No price history available.",
        "in_plain_terms": "In plain terms",
        "bullet_analyst_upside": (
            "Wall Street analysts on average expect this stock to be worth "
            "{pct:+.0f}% from here over the next year."
        ),
        "bullet_dividend": "It pays a dividend yield of about {yield:.2f}%.",
        "bullet_has_risk_flags": "Risk checks found some things worth knowing about (see the 'Why?' tab).",
        "bullet_no_risk_flags": "No major risk flags from our checks.",
        "bullet_value_score": "Long-term value checklist: {score} criteria passed -- {verdict}.",
        "key_numbers": "Key numbers",
        "pe_ratio": "P/E ratio",
        "profit_margin": "Profit margin",
        "revenue_growth": "Revenue growth",
        "beta": "Beta (volatility)",
        "why_this_signal": "Why this signal?",
        "points_in_favor": "**Points in favor:**",
        "points_of_caution": "**Points of caution:**",
        "no_strong_signals": "No strong signals detected either way.",
        "risk_flags_header": "Risk flags",
        "no_risk_flags": "No risk flags from our checks.",
        "value_checklist_header": "Long-term value checklist",
        "quarter_ended": "Quarter ended **{date}**",
        "col_line_item": "Line item",
        "col_latest_quarter": "Latest quarter",
        "col_qoq": "vs. prior quarter",
        "col_yoy": "vs. a year ago",
        "compare_intro": "Comparing everything in your watchlist, grouped by industry:",
        "fetching_compare": "Fetching comparison data for {count} stocks...",
        "col_stock": "Stock",
        "col_price": "Price",
        "col_dividend_yield": "Dividend yield",
        "col_risk_beta": "Risk (beta)",
        "col_analyst_view": "Analyst view",
        "col_relative_rank": "Relative rank",
        "rank_single_stock": "n/a (only stock in this industry)",
        "rank_not_enough_data": "not enough data to rank",
        "rank_label": "#{rank} of {out_of} -- best on {best_factor}",
        "show_full_data": "Show full data (all metrics, ungrouped)",
        "industry_group_label": "{industry} ({count})",
        "briefing_header": "Today's Briefing",
        "ollama_unavailable": (
            "Today's Briefing needs [Ollama](https://ollama.com) running locally with the "
            "`{model}` model (`ollama pull {model}`). Everything else in this app works "
            "without it."
        ),
        "briefings_ready_status": (
            "{ready}/{total} briefings ready for today. {missing} missing (run "
            "`python jobs/run_daily_briefing.py` to pre-generate all of them in the "
            "background, or generate just the missing ones now)."
        ),
        "generate_missing_button": "Generate the {missing} missing briefings now",
        "progress_starting": "Starting...",
        "progress_status": "{done}/{total}: {symbol}",
        "no_explanation": "No explanation available.",
        "show_reasoning": "Show the reasoning ({used}/{total} headlines used)",
        "mark_used": "USED",
        "mark_skipped": "skipped",
        "show_top_holdings": "Show top holdings ({count})",
        "col_holding": "Holding",
        "col_pct_of_fund": "% of fund",
        "col_todays_move": "Today's move",
        "industry_briefing_label": "{industry} ({ready}/{total} ready)",
        "not_generated_yet": "**{name} ({symbol})** -- not generated yet.",
    },
    "zh": {
        "app_title": "家庭股票追踪器",
        "nav_dashboard": "股票仪表盘",
        "nav_briefing": "今日简报",
        "add_stock_prompt": "请从左侧面板添加一支股票以开始使用。",
        "language_label": "语言",
        "your_stocks": "你关注的股票 ({count})",
        "remove_confirm": "确定要移除 **{name}** 吗？",
        "yes_remove": "确定移除",
        "cancel": "取消",
        "add_a_stock": "添加股票",
        "type_company_name": "输入公司名称",
        "type_company_placeholder": "例如：苹果、腾讯、茅台",
        "no_matches": "未找到匹配项，请尝试其他拼写。",
        "add_button": "添加 {label}",
        "looking_up_industry": "正在查询行业信息...",
        "na": "暂无",
        "choose_stock": "选择要查看的股票：",
        "fetching_data": "正在获取 {symbol} 的最新数据...",
        "current_price": "当前价格",
        "risk_level": "风险等级",
        "long_term_fit": "长期价值评分",
        "signal_prefix": "信号：{lean}",
        "tab_overview": "概览",
        "tab_reasons": "原因？",
        "tab_report": "最新季报",
        "tab_compare": "对比",
        "price_history": "价格走势",
        "time_range": "时间范围",
        "period_1mo": "1个月",
        "period_6mo": "6个月",
        "period_1y": "1年",
        "period_5y": "5年",
        "no_price_history": "暂无价格走势数据。",
        "in_plain_terms": "通俗解读",
        "bullet_analyst_upside": (
            "华尔街分析师平均预计，未来一年这支股票的价值将变化 {pct:+.0f}%。"
        ),
        "bullet_dividend": "股息收益率约为 {yield:.2f}%。",
        "bullet_has_risk_flags": "风险检查发现了一些值得留意的地方（详见“原因？”标签页）。",
        "bullet_no_risk_flags": "我们的检查未发现明显的风险信号。",
        "bullet_value_score": "长期价值清单：通过 {score} 项 -- {verdict}。",
        "key_numbers": "关键数据",
        "pe_ratio": "市盈率",
        "profit_margin": "利润率",
        "revenue_growth": "营收增长",
        "beta": "贝塔系数（波动性）",
        "why_this_signal": "为什么给出这个信号？",
        "points_in_favor": "**有利因素：**",
        "points_of_caution": "**需谨慎的因素：**",
        "no_strong_signals": "未检测到明显的信号。",
        "risk_flags_header": "风险提示",
        "no_risk_flags": "我们的检查未发现风险提示。",
        "value_checklist_header": "长期价值清单",
        "quarter_ended": "季度截止于 **{date}**",
        "col_line_item": "项目",
        "col_latest_quarter": "最新季度",
        "col_qoq": "环比上季度",
        "col_yoy": "同比去年",
        "compare_intro": "按行业分组，对比你关注列表中的所有股票：",
        "fetching_compare": "正在获取 {count} 支股票的对比数据...",
        "col_stock": "股票",
        "col_price": "价格",
        "col_dividend_yield": "股息率",
        "col_risk_beta": "风险（贝塔）",
        "col_analyst_view": "分析师观点",
        "col_relative_rank": "相对排名",
        "rank_single_stock": "暂无（该行业只有这一支股票）",
        "rank_not_enough_data": "数据不足，无法排名",
        "rank_label": "第 {rank} 名，共 {out_of} 支 -- 优势在于{best_factor}",
        "show_full_data": "显示完整数据（所有指标，未分组）",
        "industry_group_label": "{industry}（{count}）",
        "briefing_header": "今日简报",
        "ollama_unavailable": (
            "今日简报需要在本地运行 [Ollama](https://ollama.com)，并安装 `{model}` 模型"
            "（`ollama pull {model}`）。本应用的其他功能无需它也能使用。"
        ),
        "briefings_ready_status": (
            "今天已生成 {ready}/{total} 份简报，还有 {missing} 份未生成（运行 "
            "`python jobs/run_daily_briefing.py` 可在后台预先生成全部简报，"
            "也可以现在只生成缺失的部分）。"
        ),
        "generate_missing_button": "立即生成缺失的 {missing} 份简报",
        "progress_starting": "正在开始...",
        "progress_status": "{done}/{total}：{symbol}",
        "no_explanation": "暂无解释。",
        "show_reasoning": "查看分析过程（使用了 {used}/{total} 条新闻）",
        "mark_used": "已采用",
        "mark_skipped": "已跳过",
        "show_top_holdings": "查看前 {count} 大持仓",
        "col_holding": "持仓",
        "col_pct_of_fund": "占基金比例",
        "col_todays_move": "今日涨跌",
        "industry_briefing_label": "{industry}（{ready}/{total} 已生成）",
        "not_generated_yet": "**{name} ({symbol})** -- 尚未生成。",
    },
}

# Templates for the {"code", "params", "text"} structured reason entries that
# stock_toolkit.signals produces (bullish/bearish signals, risk flags, and the
# long-term value checklist). `text` on each entry is always the English
# sentence -- these templates are looked up by `code` to render the same
# sentence in Chinese; reason_text() falls back to `text` for English or for
# any code without a template, so the toolkit's own prints/notebook usage
# (always English) never needs to change.
REASON_TEMPLATES = {
    "zh": {
        "analyst_upside": "分析师目标价隐含约 {pct:.1f}% 的上涨空间",
        "analyst_downside": "现价已高出分析师目标价约 {pct:.1f}%",
        "forward_pe_below_trailing": "预期市盈率明显低于历史市盈率（预期盈利将追上股价）",
        "forward_pe_above_trailing": "预期市盈率高于历史市盈率（预期盈利可能走弱）",
        "near_52w_low": "接近52周低点（处于区间的 {rp:.0f}%）-- 可能是价值买点，也可能是继续下跌",
        "near_52w_high": "接近52周高点（处于区间的 {rp:.0f}%）-- 动能强劲，但安全边际较低",
        "rsi_oversold": "14日RSI = {rsi:.0f}（超卖）",
        "rsi_overbought": "14日RSI = {rsi:.0f}（超买）",
        "above_both_sma": "股价同时高于50日和200日均线（上升趋势）",
        "below_both_sma": "股价同时低于50日和200日均线（下降趋势）",
        "negative_revenue_growth": "营收同比负增长（{pct:.1f}%）",
        "negative_earnings_growth": "盈利同比负增长（{pct:.1f}%）",
        "high_beta": "贝塔系数偏高（{beta:.2f}）-- 波动性高于大盘",
        "high_leverage": "杠杆率偏高 -- 负债权益比 {de:.0f}",
        "low_current_ratio": "流动比率 {cr:.2f} < 1 -- 短期流动性可能承压",
        "high_volatility": "年化波动率偏高（{vol:.0f}%）",
        "deep_drawdown": "历史上出现过较深的回撤（回顾期内峰值到谷底跌幅 {dd:.0f}%）",
        "elevated_short_interest": "卖空比例偏高（占流通股的 {pct:.1f}%）",
        "unprofitable": "目前处于亏损状态（利润率为负）",
        "roe_check": "净资产收益率 (ROE) > 15%",
        "margin_check": "利润率为正",
        "fcf_check": "自由现金流为正",
        "leverage_check": "杠杆水平可控（负债权益比 < 100）",
        "revenue_growth_check": "营收同比增长",
        "earnings_growth_check": "盈利同比增长",
        "revenue_trend_check": "多年营收趋势整体向上",
        "current_ratio_check": "流动比率 > 1.2（财务缓冲充足）",
        "lean_buy": "偏向买入",
        "lean_sell": "偏向卖出 / 不建议加仓",
        "lean_hold": "中性 / 持有 -- 没有明显信号",
        "risk_high": "高",
        "risk_moderate": "中等",
        "risk_low": "低（基于这些检查）",
        "verdict_strong": "长期价值良好",
        "verdict_reasonable": "尚可，存在一些薄弱之处",
        "verdict_weak": "在这些标准下长期/价值属性较弱",
        "horizon_technical": "短期（数周）-- 基于价格走势",
        "horizon_fundamental": "中长期（数季度）-- 基于基本面",
        "horizon_mixed": "综合期限 -- 技术面与基本面指向一致",
        "dim_valuation": "估值",
        "dim_profitability": "盈利能力",
        "dim_growth": "成长性",
        "dim_analyst_upside": "分析师上涨空间",
    },
}


def get_lang():
    return st.session_state.get("lang", "en")


def t(key, **kwargs):
    """Look up a static UI string in the active language and format it.
    Falls back to English, then to the raw key, if a translation is missing.
    """
    lang = get_lang()
    template = STRINGS.get(lang, {}).get(key) or STRINGS["en"].get(key, key)
    return template.format(**kwargs) if kwargs else template


def code_text(code, fallback):
    """Look up a bare reason code (no params) in the active language, e.g.
    buy_sell_signal()'s lean_code -- falls back to the English string already
    computed by stock_toolkit when there's no translation."""
    lang = get_lang()
    return REASON_TEMPLATES.get(lang, {}).get(code, fallback)


def reason_text(entry):
    """Render a structured {"code", "params", "text"} reason entry (from
    stock_toolkit.signals) in the active language. English (or a code with no
    template) falls back to the entry's own English `text`.
    """
    lang = get_lang()
    if lang == "en":
        return entry["text"]
    template = REASON_TEMPLATES.get(lang, {}).get(entry["code"])
    if not template:
        return entry["text"]
    try:
        return template.format(**entry.get("params", {}))
    except (KeyError, ValueError):
        return entry["text"]


def dim_label(dim_name):
    """Translate a relative_rank() dimension name (e.g. "valuation") for
    display -- these come back as raw English strings in best_factor/
    worst_factor, same reasoning as reason_text() above."""
    lang = get_lang()
    key = "dim_" + dim_name.replace(" ", "_")
    return REASON_TEMPLATES.get(lang, {}).get(key, dim_name)
