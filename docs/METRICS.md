# Metrics Reference

What each metric in this toolkit actually measures, why it can mislead, and what a good
reading looks like across different kinds of businesses.

This file is deliberately **not** a list of thresholds -- those live next to the code that
uses them (`stock_toolkit/signals.py`'s docstrings, closest to `long_term_value_score`,
`buy_sell_signal`, and `risk_scan`), so they get updated by whoever next changes that
threshold instead of drifting out of sync here. This file is the study material: read it
to understand a metric, then go read the docstring to see the actual number this codebase
currently uses for it.

## Valuation

### Trailing P/E / Forward P/E
Price divided by earnings per share -- trailing uses the last 12 reported months, forward
uses analyst estimates for the next 12. What it's really asking: "how many years of
current/expected earnings am I paying for?" Misleads when earnings are temporarily
depressed or inflated (a one-off writedown makes P/E look absurdly high; a one-off gain
makes it look cheap) -- always sanity-check against the income statement, not the ratio
alone. Forward P/E is only as good as the analyst estimates behind it, and estimate
coverage thins out for smaller/less-followed stocks (more relevant for less-covered
A-share names than for AAPL/MSFT). Not comparable across sectors: a mature bank trading at
8x and a high-growth software company trading at 40x can both be fairly priced for what
they are.

### PEG ratio
P/E divided by expected earnings growth rate. Meant to answer "is this P/E justified by
how fast earnings are growing" -- a stock with a high P/E but also high growth can have a
*lower* (more attractive) PEG than a low-P/E, no-growth stock. Breaks down for
low/negative-growth companies (the ratio becomes meaningless or wildly volatile near zero
growth) and is very sensitive to which growth estimate is used (this toolkit takes
whatever `yfinance` reports, which may be forward or trailing PEG depending on
availability).

### Price-to-Book
Price divided by book (accounting) value of equity per share. Useful for
asset-heavy businesses (banks, insurers, industrials) where book value tracks something
real -- much less meaningful for asset-light software/services companies whose real value
is in intangibles (brand, IP, network effects) that accounting book value doesn't capture
well.

### EV/EBITDA
Enterprise value (market cap + debt - cash) divided by EBITDA. Better than P/E for
comparing companies with different capital structures or tax situations, since it's
capital-structure- and depreciation-policy-agnostic. Misleads for capital-intensive
businesses where "ignoring depreciation" ignores a real, recurring cash cost (a
railroad's EBITDA looks great; its EBITDA *minus the capex needed to maintain the
track* looks very different).

## Profitability

### Profit margin
Net income divided by revenue. Straightforward, but varies enormously by business model
by design, not by quality -- grocery retailers run on low-single-digit margins as normal;
software companies routinely run 20%+. Comparing margin across sectors tells you about the
sector, not which company is "better run."

### Return on Equity (ROE)
Net income divided by shareholder equity -- "how much profit per dollar shareholders have
tied up in the business." The metric most sensitive to capital structure: a company can
raise ROE purely by taking on more debt (shrinking the equity base) or buying back stock,
with zero change to how the underlying business actually performs. Always read ROE next
to debt/equity -- a high ROE on high leverage is a different (riskier) story than a high
ROE on a clean balance sheet.

## Growth

### Revenue growth / Earnings growth (YoY)
Straightforward year-over-year change. Earnings growth is noisier than revenue growth --
a single one-off item (asset sale, tax adjustment, impairment) can swing reported earnings
growth by tens of percentage points without reflecting anything about the ongoing
business, so a single quarter's earnings-growth number is weaker evidence than a
multi-year revenue trend. Negative growth isn't automatically bad -- a deliberate
restructuring, divestiture, or currency headwind can produce it without signalling
business decline; read the "why" from the actual quarterly report (`quarterly_report_summary`),
not just the sign.

## Leverage & Liquidity

### Debt-to-Equity
Total debt divided by shareholder equity. What counts as "normal" varies by an order of
magnitude by sector: utilities and financials routinely run leverage many software or
services companies would consider alarming, because their cash flows are far more stable
and predictable, or because leverage is core to the business model (banks). Reading this
number without knowing the sector's normal range is close to meaningless.

### Current ratio
Current assets divided by current liabilities -- a snapshot of whether short-term
obligations are covered by short-term resources. A subscription or service business that
collects cash upfront (deferred revenue sits as a *liability*) can run a "low" current
ratio while being financially healthy; a manufacturer sitting on large inventory can run
a "high" one while masking a real problem (inventory that won't actually sell). Read
alongside free cash flow, not in isolation.

### Free cash flow (FCF)
Operating cash flow minus capital expenditure -- cash actually left over after running
and maintaining the business, arguably harder to manipulate via accounting choices than
net income. Capital-intensive businesses (telecom, industrials, semiconductors) can show
strong net income but weak FCF in a heavy investment year; that's not automatically a red
flag if the capex is funding real future capacity.

## Risk

### Beta
Historical sensitivity of the stock's price to the broader market's moves (1.0 = moves
with the market; >1.0 = amplifies market moves; <1.0 = dampens them). It's backward-looking
and regime-dependent -- a beta measured over a calm multi-year window can understate how a
stock behaves in a real selloff, and a single-factor "sensitivity to the market" number
says nothing about company-specific risk (a lawsuit, a product recall, a regulatory
action).

### Annualized volatility / Max drawdown
Volatility: how much the daily price bounces around, annualized. Max drawdown: the worst
peak-to-trough decline seen in the lookback window. Both are pure historical description,
not a prediction -- a stock with a calm recent history can still have a violent future
one, and vice versa. Drawdown especially depends heavily on the chosen lookback window;
this toolkit's `risk_scan` uses a 2-year window, so a crash just outside that window won't
show up.

### Short percent of float
Share of publicly tradeable shares currently sold short. High short interest signals the
market has real, priced-in skepticism about the stock -- but it's a two-sided signal, not
a pure bearish one: heavily shorted stocks can also be prone to sharp short-covering
rallies ("short squeezes") on any positive surprise, since short sellers buying back
shares to close positions itself pushes the price up.

## Technicals

### RSI (14-day)
Momentum oscillator (0-100) comparing the magnitude of recent gains to recent losses.
Conventionally read as "oversold" below 30 and "overbought" above 70 -- but in a strong
sustained trend, RSI can sit in "overbought"/"oversold" territory for a long stretch
while the trend just continues; it's a momentum reading, not a reversal prediction.

### SMA50 / SMA200 (moving averages)
Simple average of closing price over the trailing 50 or 200 trading days -- smooths out
day-to-day noise to show the underlying trend direction. Price above both is a
conventional "uptrend" read, below both a "downtrend" read; both are lagging by
construction (built from past prices), so they confirm a trend already underway rather
than predicting a turn.

## Analyst data

### Analyst target price / recommendation
Wall Street sell-side analysts' published price targets and Buy/Hold/Sell consensus.
Well-documented industry-wide optimism bias -- sell-side "Sell" ratings are rare across
the board (relationship/access incentives with the companies covered), so several
well-covered peers all showing "Buy" is normal, not a signal that they're equally good
picks (see `relative_rank` for a way to differentiate peers `compare_stocks()` alone
can't). Coverage itself is uneven -- smaller and less-followed stocks (more common among
this toolkit's A-share/HK holdings) may have very few analysts behind the number, making
a single outlier estimate swing the average heavily.
