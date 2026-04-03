# 📊 Predictive Asset Allocation System

An end-to-end, AI-powered investment platform that orchestrates data retrieval, machine learning, and risk-matched portfolio optimization for the S&P 500 universe.

---

## 🏗️ System Architecture

```mermaid
flowchart TB
    subgraph "Data Sources"
        SEC[SEC EDGAR API]
        YF[Yahoo Finance API]
        SCF[SCF 2022 Survey Data]
    end

    subgraph "Pipeline Layer"
        Pipe[sp500_pipeline]
    end

    subgraph "ML Models"
        FundML[Fundamental Model<br/>LightGBM]
        TechML[Technical Model<br/>LightGBM]
        RiskML[Risk Tolerance Model<br/>Random Forest/XGBoost]
    end

    subgraph "Composite Layer"
        Comp[Composite Scorer]
        Port[Portfolio Builder<br/>PyPortfolioOpt]
    end

    subgraph "Presentation"
        GUI[Streamlit Dashboard]
    end

    SEC --> Pipe
    YF --> Pipe
    Pipe --> FundML
    Pipe --> TechML
    SCF --> RiskML
    FundML --> Comp
    TechML --> Comp
    RiskML --> Comp
    Comp --> Port
    Port --> GUI

    style Pipe fill:#1a1a2e,color:#fff
    style FundML fill:#16213e,color:#fff
    style TechML fill:#16213e,color:#fff
    style RiskML fill:#16213e,color:#fff
    style Comp fill:#0f3460,color:#fff
    style Port fill:#0f3460,color:#fff
    style GUI fill:#e94560,color:#fff
```

---

## 📂 Project Structure

```
.
├── sp500_pipeline/          # Data ingestion & ETL from SEC EDGAR
├── sp500_ml/                 # Fundamental analysis ML model
├── sp500_technical/         # Technical analysis ML model
├── risk prediction/         # Investor risk tolerance model
├── composite/               # Portfolio construction & optimization
├── gui/                     # Streamlit web interface
│   ├── components/          # UI components (charts, tables, etc.)
│   ├── core/                # Business logic (portfolio, backtest)
│   └── styles/              # Custom CSS theming
├── output/                  # Fundamental model outputs
├── output_technical/       # Technical model outputs
├── output_composite/        # Portfolio outputs
└── daily_prices_all.csv     # Historical price data
```

---

## 🔄 How It Works

### 1. Data Pipeline (`sp500_pipeline`)

```mermaid
flowchart LR
    A[SEC EDGAR API] --> P[Pipeline]
    B[Yahoo Finance API] --> P
    P --> C[Fetch S&P 500]
    C --> D[Extract XBRL]
    D --> E[Feature Engineering<br/>50+ Ratios]
    E --> F[Generate Target Returns]
    F --> G[Fundamental Dataset<br/>CSV/Parquet]
```

**Key Features:**
- Fetches company list from S&P 500
- Extracts XBRL financial statements (Balance Sheet, Income Statement, Cash Flow)
- Computes 50+ financial ratios (ROE, Debt-to-Equity, Operating Margin, etc.)
- Generates forward-looking excess returns relative to SPY

---

### 2. ML Models

#### 2.1 Fundamental Model (`sp500_ml`)

```mermaid
flowchart TB
    subgraph "Input"
        Data[Fundamental Dataset]
    end

    subgraph "Preprocessing"
        Clip[Outlier Clipping]
        ZScore[Sector Z-Scoring]
        Lag[Temporal Lag Features]
    end

    subgraph "Training"
        Train[LightGBM Training]
        Prune[Feature Pruning]
        CV[Walk-Forward CV]
    end

    subgraph "Output"
        Model[Model.pkl]
        Risk[Stock Risk Scores]
    end

    Data --> Clip --> ZScore --> Lag --> Train
    Train --> Prune --> CV --> Model
    CV --> Risk
```

**Process:**
1. Preprocessing: Outlier clipping, sector-based z-scoring, temporal lag features
2. Two-pass training to identify high-impact features
3. Walk-forward cross-validation for robust validation
4. Generates Stock Risk Scores (0-100) based on model uncertainty, volatility, sector stability

#### 2.2 Technical Model (`sp500_technical`)

```mermaid
flowchart TB
    Prices[Daily OHLCV Data] --> Indicators[Compute Indicators<br/>RSI, MACD, Bollinger, etc.]
    Indicators --> Train[LightGBM Training]
    Train --> TechModel[Technical Model.pkl]
```

**Indicators Used:**
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence/Divergence)
- Bollinger Bands
- Moving Average Crossovers
- ADX (Average Directional Index)
- Volume Profiles

#### 2.3 Risk Tolerance Model (`risk prediction`)

```mermaid
flowchart TB
    subgraph "Input"
        A[Age]
        E[Education]
        O[Occupation]
        I[Income]
        N[Net Worth]
        As[Asset Mix]
    end

    subgraph "Training"
        T[Random Forest/XGBoost]
        M[Risk Model.pkl]
    end

    subgraph "Output"
        S[Risk Score 0-100]
    end

    A --> T
    E --> T
    O --> T
    I --> T
    N --> T
    As --> T
    T --> M
    M --> S
```

**Description:**
- **Source:** 2022 Survey of Consumer Finances (SCF) dataset with ~30,000 households
- **Model:** Random Forest / XGBoost classifier
- **Features:** Age, Education, Occupation, Income, Net Worth, Asset Mix
- **Output:** 0-100 Investor Risk Score

---

### 3. Composite Scoring & Portfolio Construction (`composite`)

```mermaid
flowchart TB
    subgraph "Inputs"
        FundPred[Fundamental Predictions]
        TechPred[Technical Predictions]
        RiskScore[Investor Risk Score]
        StockRisk[Stock Risk Scores]
    end

    subgraph "Composite Scorer"
        Blend[Blend 40% Fund + 60% Tech]
        Bucket[Map to Risk Buckets 1-5]
    end

    subgraph "Portfolio Builder"
        Filter[Filter by Bucket]
        Rank[Rank by Composite Score]
        Opt[PyPortfolioOpt Optimization]
    end

    subgraph "Output"
        Port[10-Stock Portfolio<br/>with Weights]
    end

    FundPred --> Blend
    TechPred --> Blend
    RiskScore --> Bucket
    StockRisk --> Filter
    Blend --> Rank
    Bucket --> Filter
    Rank --> Opt
    Opt --> Port
```

**Risk Buckets:**
| Bucket | Description | Profile |
|--------|-------------|---------|
| 1 | Ultra-Conservative | Low volatility, high stability |
| 2 | Conservative | Moderate risk |
| 3 | Moderate | Balanced |
| 4 | Growth | Higher risk, higher return |
| 5 | Ultra-Aggressive | High momentum, high volatility |

**Key Features:**
- Weighted blending of Fundamental (40%) and Technical (60%) predictions
- Maps investor risk score to appropriate stock risk buckets
- Uses PyPortfolioOpt for mean-variance optimization
- Generates exactly 10 stocks in the portfolio

---

### 4. Backtesting

```mermaid
sequenceDiagram
    participant Portfolio
    participant Prices
    participant SPY
    participant Calc

    Portfolio->>Prices: Get historical prices
    Prices->>Calc: Daily returns
    SPY->>Calc: SPY daily returns
    Calc->>Calc: Calculate metrics
    Calc->>Calc: Alpha, Beta, Sharpe, Drawdown

    Note over Calc: Compare Portfolio vs SPY
    Calc-->>Portfolio: Performance Report
```

**Metrics Calculated:**
- Annual Return (%)
- Annual Volatility (%)
- Sharpe Ratio
- Alpha (%)
- Beta
- Maximum Drawdown (%)
- Outperformance vs S&P 500

---

### 5. GUI Dashboard (`gui`)

```mermaid
flowchart TB
    subgraph "User Flow"
        Q[Investor Questionnaire<br/>12 Questions]
        Risk[Predict Risk Score]
        Port[Generate Portfolio]
        Backtest[Run Backtest]
    end

    subgraph "Display Sections"
        RiskDisp[Risk Assessment<br/>Gauge + Metrics]
        PortDisp[Portfolio Allocation<br/>Pie + Table]
        PerfDisp[Performance vs S&P<br/>Chart + Metrics]
    end

    Q --> Risk
    Risk --> Port
    Port --> Backtest
    Q --> RiskDisp
    Risk --> PortDisp
    Port --> PerfDisp
```

**Questionnaire Fields:**
1. Age (18-85)
2. Education Level
3. Occupation Status
4. Annual Income Range
5. Net Worth Range
6. Total Assets Range
7. Emergency Fund (Yes/No)
8. Savings Account (Yes/No)
9. Mutual Funds (Yes/No)
10. Retirement Account (Yes/No)
11. Investment Capital

**Display Layout:**
1. **Risk Assessment** - Gauge showing risk score (0-100), category, equity allocation
2. **Portfolio Allocation** - Pie chart and table of 10 stocks with weights
3. **Performance vs S&P 500** - Line chart comparing portfolio vs SPY, metrics table

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- SEC User-Agent string (configured in `sp500_pipeline/config.py`)

### Installation

```bash
# Clone repository
git clone <repository-url>
cd predictive-asset-allocation

# Install dependencies
pip install -r requirements.txt
pip install -r gui/requirements.txt
```

### Running the System

```bash
# 1. Run data pipeline (if needed)
python run_pipeline.py

# 2. Train fundamental model
python run_ml.py

# 3. Train technical model
python run_technical.py

# 4. Generate portfolios
python run_composite.py --profile moderate

# 5. Launch dashboard
streamlit run gui/app.py
```

### Quick Start (Dashboard Only)

If data and models are already generated:

```bash
streamlit run gui/app.py
```

---

## 📊 Portfolio Examples

### Conservative Profile (Risk Score ≤ 35)
- Lower equity allocation
- Focus on stable, low-volatility stocks
- Smaller exposure to growth buckets

### Moderate Profile (Risk Score 36-50)
- Balanced equity allocation
- Mix of stability and growth
- Optimal risk-return tradeoff

### Aggressive Profile (Risk Score > 70)
- Higher equity allocation
- Focus on high-momentum stocks
- Allocations to higher-risk buckets

---

## 📈 Performance Validation

- **Information Coefficient (IC)** for model quality
- **Decile Spread** for ranking effectiveness
- **Backtest Comparison**: Portfolio vs S&P 500 (SPY)
- **Metrics**: Sharpe Ratio, Sortino Ratio, Maximum Drawdown

---

## ⚠️ Disclaimer

This software is for educational and research purposes only. It does not constitute financial advice. Always consult with a certified financial advisor before making investment decisions.

---

## 📁 Key Files

| File | Description |
|------|-------------|
| `run_pipeline.py` | Data ingestion from SEC EDGAR |
| `run_ml.py` | Train fundamental model |
| `run_technical.py` | Train technical model |
| `run_composite.py` | Build portfolios |
| `run_backtest.py` | Run backtests |
| `gui/app.py` | Streamlit dashboard entry point |
| `requirements.txt` | Python dependencies |
| `gui/requirements.txt` | GUI dependencies |

---

## 🛠️ Technology Stack

- **Data Processing**: pandas, numpy
- **ML Models**: LightGBM, XGBoost, Random Forest
- **Optimization**: PyPortfolioOpt
- **Visualization**: Plotly, Streamlit
- **Data Sources**: SEC EDGAR, Yahoo Finance, SCF 2022