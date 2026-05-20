# Running this project

Step-by-step setup and run instructions, including a VS Code walk-through.

## Prerequisites

- Python 3.10 or newer (developed on 3.13)
- No API keys or accounts. Prices are downloaded from the public
  [SMARD.de](https://www.smard.de/en) endpoints on first run and cached locally.

## 1. Get the code and install dependencies

```bash
git clone https://github.com/CodingxFaisal/power-spread-trader.git
cd power-spread-trader
```

Create and activate a virtual environment (recommended):

```bash
python -m venv .venv
```

- Windows (PowerShell): `.\.venv\Scripts\Activate.ps1`
- Windows (cmd): `.\.venv\Scripts\activate.bat`
- macOS / Linux: `source .venv/bin/activate`

Then install:

```bash
pip install -r requirements.txt
```

## 2. Open in VS Code

1. `File -> Open Folder...` and select this project folder.
2. Install the Microsoft **Python** extension if prompted.
3. Select the interpreter: `Ctrl+Shift+P` -> "Python: Select Interpreter" ->
   choose the `.venv` you just created.
4. Open a terminal with `` Ctrl+` ``. It starts in the project root.

## 3. Reproduce everything

Downloads the data once (about two minutes the first time, then cached) and runs
the backtest, cost-sensitivity and robustness steps, writing charts and CSVs to
`results/`:

```bash
python scripts/run_all.py
```

## 4. Or run one step at a time

```bash
python scripts/download_prices.py       # SMARD multi-zone day-ahead prices
python scripts/run_backtest.py          # portfolio backtest, in-sample vs out-of-sample
python scripts/run_cost_sensitivity.py  # Sharpe vs transaction cost, break-even
python scripts/run_robustness.py        # lag-decay, parameter heatmap, shuffled-null test
```

## 5. Run the tests

```bash
pytest
```

Expected: **20 passed**. The tests cover the no-lookahead P&L shift, the
hysteresis logic, cost accounting, and null/trend sanity checks.

## Outputs

Everything lands in `results/`:

- `equity_curve.png`, `drawdown.png`, `per_instrument_sharpe.png`,
  `signal_example.png`, `cost_sensitivity.png`, `lag_decay.png`,
  `param_heatmap.png`
- `portfolio_metrics.csv`, `per_instrument_oos_metrics.csv`,
  `cost_sensitivity.csv`, `param_heatmap.csv`

## Troubleshooting

- **Import errors running a script directly:** run from the project root. The
  scripts add `src/` to the path themselves.
- **First run is slow:** it is downloading several years of hourly prices for
  seven zones from SMARD. Later runs read the local cache in `data/`.
