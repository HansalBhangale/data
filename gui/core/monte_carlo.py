"""
Monte Carlo Simulation Module - Future Portfolio Projections

Provides forward-looking projections based on:
1. Three-tier return scenarios (Optimistic/Base/Conservative)
2. Bayesian shrinkage toward market return for Base tier
3. Monthly time stepping for realistic path dynamics
4. Stress scenarios (2008, COVID, Dot-com crashes)

ENHANCEMENTS APPLIED:
- Three-tier μ: Optimistic (full backtest), Base (Bayesian shrinkage), Conservative (50/50 blend)
- Bayesian shrinkage formula: μ_base = (n / (n + k)) × μ_backtest + (k / (n + k)) × μ_market
- Monthly stepping (dt = 1/12) for better intra-year dynamics
- Correlation calculated from actual backtest data
- Conservative as default tier for compliance
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from scipy.stats import t as t_distribution
import warnings

warnings.filterwarnings('ignore')


# Configuration
N_SIMULATIONS = 10000
TIME_HORIZONS = [1, 3, 5, 10]
TRADING_DAYS = 252
STEPS_PER_YEAR = 12  # Monthly stepping

# Bayesian shrinkage parameters
K_PARAM = 36  # Confidence parameter (3 years of market confidence)
MARKET_RETURN = 0.10  # Long-run market return assumption
MAX_BACKTEST_MONTHS = 120  # Cap at 10 years to prevent overconfidence

# Student's t degrees of freedom (lower = fatter tails)
T_DEGREES_OF_FREEDOM = 5


def calculate_shrinkage_return(
    backtest_return: float,
    n_months: int,
    k: int = K_PARAM,
    market_return: float = MARKET_RETURN
) -> float:
    """
    Calculate Bayesian shrinkage return toward market return.
    
    μ_base = (n / (n + k)) × μ_backtest + (k / (n + k)) × μ_market
    
    Parameters
    ----------
    backtest_return : float
        Annual return from backtest (e.g., 0.48 for 48%)
    n_months : int
        Number of months of backtest data
    k : int
        Confidence parameter (default: 36, representing 3 years)
    market_return : float
        Long-run market return assumption (default: 10%)
    
    Returns
    -------
    float
        Shrunk annual return toward market
    """
    n = min(n_months, MAX_BACKTEST_MONTHS)  # Cap at 10 years
    weight_backtest = n / (n + k)
    weight_market = k / (n + k)
    
    shrunk_return = weight_backtest * backtest_return + weight_market * market_return
    
    return shrunk_return


def get_three_tier_returns(
    backtest_return: float,
    n_months: int
) -> Dict[str, float]:
    """
    Calculate three tiers of expected returns.
    
    Parameters
    ----------
    backtest_return : float
        Annual return from backtest
    n_months : int
        Number of months of backtest data
    
    Returns
    -------
    Dict with three tiers and metadata
    """
    # Optimistic: Full backtest return (strategy ceiling)
    optimistic_return = backtest_return
    
    # Base: Bayesian shrinkage toward market
    base_return = calculate_shrinkage_return(backtest_return, n_months)
    
    # Conservative: 50% backtest + 50% market return (compliance-safe)
    conservative_return = 0.5 * backtest_return + 0.5 * MARKET_RETURN
    
    return {
        'optimistic': {
            'return': optimistic_return,
            'description': 'Full backtest return (strategy ceiling)',
            'formula': f'μ = {backtest_return:.1%}'
        },
        'base': {
            'return': base_return,
            'description': 'Bayesian shrinkage toward market',
            'formula': f'μ = ({n_months}/({n_months}+36)) × {backtest_return:.1%} + (36/(36+{n_months})) × 10%',
            'n_months': n_months,
            'shrinkage_factor': n_months / (n_months + K_PARAM)
        },
        'conservative': {
            'return': conservative_return,
            'description': '50% backtest + 50% market (compliance-safe)',
            'formula': f'μ = 0.5 × {backtest_return:.1%} + 0.5 × 10%'
        }
    }


def calculate_correlation_from_returns(
    portfolio_returns: np.ndarray,
    spy_returns: np.ndarray,
    min_periods: int = 30
) -> float:
    """
    Calculate correlation from return arrays, floor at 0.3.
    
    Parameters
    ----------
    portfolio_returns : np.ndarray
        Portfolio daily/periodic returns
    spy_returns : np.ndarray
        S&P 500 daily/periodic returns
    min_periods : int
        Minimum periods required (default: 30)
    
    Returns
    -------
    float
        Correlation coefficient, floored at 0.3
    """
    if len(portfolio_returns) < min_periods or len(spy_returns) < min_periods:
        return 0.5  # Default if insufficient data
    
    # Remove NaN values
    mask = ~(np.isnan(portfolio_returns) | np.isnan(spy_returns))
    port_clean = portfolio_returns[mask]
    spy_clean = spy_returns[mask]
    
    if len(port_clean) < min_periods:
        return 0.5
    
    correlation = np.corrcoef(port_clean, spy_clean)[0, 1]
    
    if np.isnan(correlation):
        return 0.5
    
    # Floor at 0.3 to prevent unrealistically low correlation
    return max(0.3, correlation)


STRESS_SCENARIOS = {
    '2008_crash': {
        'name': '2008 Financial Crisis',
        'crash_return': -0.37,  # Year 1 crash
        'recovery_return': 0.08,  # Subsequent years (slower recovery)
        'crash_vol': 0.50,
        'recovery_vol': 0.25,
        'description': '37% crash in year 1, slow recovery over 3+ years'
    },
    'covid_crash': {
        'name': 'COVID-19 Crash (2020)',
        'crash_return': -0.34,  # March 2020
        'recovery_return': 0.15,  # Fast recovery
        'crash_vol': 0.80,  # Extreme volatility during crash
        'recovery_vol': 0.22,
        'description': '34% crash with V-shaped recovery within months'
    },
    'dot_com': {
        'name': 'Dot-com Crash (2000-2002)',
        'crash_return': -0.49,
        'recovery_return': -0.02,  # Continued decline in subsequent years
        'crash_vol': 0.35,
        'recovery_vol': 0.20,
        'description': '49% crash, followed by 2 more years of decline'
    },
    'inflation_2022': {
        'name': '2022 Inflation Crisis',
        'crash_return': -0.19,
        'recovery_return': 0.12,
        'crash_vol': 0.28,
        'recovery_vol': 0.18,
        'description': '19% decline due to Fed rate hikes, steady recovery'
    }
}


def _generate_random_shocks(n: int, use_fat_tails: bool = True) -> np.ndarray:
    """
    Generate random shocks using Student's t-distribution for fat tails.

    Parameters
    ----------
    n : int
        Number of random values to generate
    use_fat_tails : bool
        If True, use Student's t (fat tails). If False, use normal.

    Returns
    -------
    np.ndarray
        Array of random values scaled to unit variance
    """
    if use_fat_tails:
        # Student's t with df=5 has fatter tails than normal
        # Scale to unit variance (t distribution has variance = df/(df-2))
        raw = t_distribution.rvs(T_DEGREES_OF_FREEDOM, size=n)
        # Normalize variance
        variance = T_DEGREES_OF_FREEDOM / (T_DEGREES_OF_FREEDOM - 2)
        return raw / np.sqrt(variance)
    else:
        return np.random.standard_normal(n)


def run_monte_carlo(
    initial_capital: float,
    annual_return: float,
    annual_vol: float,
    spy_return: float = 0.10,
    spy_vol: float = 0.15,
    n_simulations: int = N_SIMULATIONS,
    time_horizons: List[int] = TIME_HORIZONS,
    seed: int = 42,
    use_fat_tails: bool = True,
    n_months: int = 12,
    correlation: float = 0.5,
    tier: str = 'conservative',
    portfolio_returns: np.ndarray = None,
    spy_returns: np.ndarray = None
) -> Dict:
    """
    Run Monte Carlo simulation with three-tier scenarios and monthly stepping.
    
    Parameters
    ----------
    initial_capital : float
        Starting portfolio value
    annual_return : float
        Expected annual return (from backtest)
    annual_vol : float
        Annual volatility (from backtest)
    spy_return : float
        S&P 500 expected annual return (default: 10%)
    spy_vol : float
        S&P 500 annual volatility (default: 15%)
    n_simulations : int
        Number of simulation paths (default: 10000)
    time_horizons : List[int]
        Years to project (default: [1, 3, 5, 10])
    seed : int
        Random seed for reproducibility
    use_fat_tails : bool
        If True, use Student's t distribution (realistic crash frequency)
    n_months : int
        Number of months of backtest data (for shrinkage calculation)
    correlation : float
        Portfolio-SP500 correlation (default: 0.5)
    tier : str
        Return tier: 'optimistic', 'base', or 'conservative' (default: 'conservative')
    portfolio_returns : np.ndarray, optional
        Historical portfolio returns for correlation calculation
    spy_returns : np.ndarray, optional
        Historical S&P returns for correlation calculation
    
    Returns
    -------
    Dict with projection data for all tiers
    """
    np.random.seed(seed)
    
    # Calculate correlation from data if provided
    if portfolio_returns is not None and spy_returns is not None:
        calculated_corr = calculate_correlation_from_returns(portfolio_returns, spy_returns)
        correlation = calculated_corr
    
    # Get three-tier returns based on backtest data
    tier_returns = get_three_tier_returns(annual_return, n_months)
    
    # Select the appropriate return for the requested tier
    selected_return = tier_returns[tier]['return']
    
    # For stress scenarios, use conservative as baseline
    stress_base_return = tier_returns['conservative']['return']
    
    result = {
        'initial_capital': initial_capital,
        'time_horizons': time_horizons,
        'params': {
            'backtest_return': annual_return,
            'selected_return': selected_return,
            'volatility': annual_vol,
            'spy_vol': spy_vol,
            'spy_backtest_return': spy_return,
            'n_simulations': n_simulations,
            'n_months': n_months,
            'tier': tier,
            'correlation': correlation,
            'time_step': 'monthly',
            'use_fat_tails': use_fat_tails
        },
        'tiers': tier_returns,
        # Main projection using selected tier
        'actual': _run_scenario_simulations_monthly(
            initial_capital, selected_return, annual_vol,
            n_simulations, time_horizons, f'{tier.title()} Tier',
            use_fat_tails=use_fat_tails
        ),
        # Blend with S&P using calculated correlation
        'blend': _run_blend_simulation_monthly(
            initial_capital, selected_return, annual_vol,
            spy_return, spy_vol, n_simulations, time_horizons,
            use_fat_tails=use_fat_tails, correlation=correlation
        ),
        # Stress scenarios using conservative tier return
        'stress': _run_stress_scenarios_monthly(
            initial_capital, n_simulations, time_horizons,
            use_fat_tails=use_fat_tails, base_return=stress_base_return
        ),
        'spy_baseline': _run_spy_projections_monthly(
            initial_capital, spy_return, spy_vol,
            n_simulations, time_horizons,
            use_fat_tails=use_fat_tails
        ),
    }
    
    # Calculate BOTH beat probabilities from correlated simulations
    result['beat_spy_probability'] = {}
    result['beat_spy_probability_conservative'] = {}
    
    for horizon in time_horizons:
        result['beat_spy_probability'][horizon] = calculate_beat_spy_probability(
            result, horizon, use_conservative_spy=False
        )
        result['beat_spy_probability_conservative'][horizon] = calculate_beat_spy_probability(
            result, horizon, use_conservative_spy=True, spy_backtest_return=spy_return
        )

    return result


def _run_scenario_simulations_monthly(
    initial_capital: float,
    annual_return: float,
    annual_vol: float,
    n_simulations: int,
    time_horizons: List[int],
    scenario_name: str,
    use_fat_tails: bool = True
) -> Dict:
    """
    Run GBM simulations with monthly time stepping (dt = 1).
    
    More realistic path dynamics, better capture of intra-year drawdowns.
    """
    max_years = max(time_horizons)
    total_months = max_years * STEPS_PER_YEAR
    dt = 1.0  # Each step represents 1 month (not 1/12)
    
    # Convert annual parameters to MONTHLY
    # Monthly drift = (annual return - 0.5 * annual vol^2) / 12
    # This is correct: the annual drift is distributed across 12 months
    monthly_drift = (annual_return - 0.5 * annual_vol**2) / STEPS_PER_YEAR
    monthly_vol = annual_vol / np.sqrt(STEPS_PER_YEAR)
    
    # Track values at yearly checkpoints
    yearly_checkpoints = [y * STEPS_PER_YEAR for y in time_horizons]
    
    simulations = np.zeros((n_simulations, len(yearly_checkpoints) + 1))
    simulations[:, 0] = initial_capital
    
    current_values = np.full(n_simulations, initial_capital)
    
    for month in range(1, total_months + 1):
        # Generate random shocks with fat tails
        z = _generate_random_shocks(n_simulations, use_fat_tails)
        
        # GBM with monthly time step (dt = 1 month = 1 unit)
        # S(t+1) = S(t) * exp(monthly_drift + monthly_vol * Z)
        current_values = current_values * np.exp(
            monthly_drift * dt + monthly_vol * np.sqrt(dt) * z
        )
        
        # Store at yearly checkpoints
        if month in yearly_checkpoints:
            idx = yearly_checkpoints.index(month)
            simulations[:, idx + 1] = current_values
    
    # Build percentiles at each horizon
    percentiles = {}
    for i, years in enumerate(time_horizons):
        values = simulations[:, i + 1]  # +1 because index 0 is year 0
        percentiles[years] = {
            'p5': float(np.percentile(values, 5)),
            'p10': float(np.percentile(values, 10)),
            'p25': float(np.percentile(values, 25)),
            'p50': float(np.percentile(values, 50)),
            'p75': float(np.percentile(values, 75)),
            'p90': float(np.percentile(values, 90)),
            'p95': float(np.percentile(values, 95)),
            'mean': float(np.mean(values)),
            'std': float(np.std(values)),
            'all_values': values.tolist()
        }
    
    return {
        'name': scenario_name,
        'return': annual_return,
        'volatility': annual_vol,
        'percentiles': percentiles
    }


def _run_blend_simulation_monthly(
    initial_capital: float,
    port_return: float,
    port_vol: float,
    spy_return: float,
    spy_vol: float,
    n_simulations: int,
    time_horizons: List[int],
    use_fat_tails: bool = True,
    correlation: float = 0.6
) -> Dict:
    """
    Run monthly simulation with properly blended volatility.
    """
    w1, w2 = 0.5, 0.5
    
    # Proper variance blending with correlation
    blended_var = (w1**2 * port_vol**2 +
                   w2**2 * spy_vol**2 +
                   2 * w1 * w2 * correlation * port_vol * spy_vol)
    blended_vol = np.sqrt(blended_var)
    
    blended_return = w1 * port_return + w2 * spy_return
    
    return _run_scenario_simulations_monthly(
        initial_capital, blended_return, blended_vol,
        n_simulations, time_horizons, 'Blended Volatility (Monthly)',
        use_fat_tails=use_fat_tails
    )


def _run_stress_scenarios_monthly(
    initial_capital: float,
    n_simulations: int,
    time_horizons: List[int],
    use_fat_tails: bool = True,
    base_return: float = 0.10
) -> Dict:
    """Run monthly stress scenarios with crash/recovery dynamics."""
    stress_results = {}
    max_years = max(time_horizons)
    total_months = max_years * STEPS_PER_YEAR
    dt = 1.0  # Each step = 1 month
    
    yearly_checkpoints = [y * STEPS_PER_YEAR for y in time_horizons]
    
    for scenario_key, scenario_data in STRESS_SCENARIOS.items():
        simulations = np.zeros((n_simulations, len(yearly_checkpoints) + 1))
        simulations[:, 0] = initial_capital
        
        current_values = np.full(n_simulations, initial_capital)
        
        crash_months = 12  # First 12 months = crash period
        crash_return = scenario_data['crash_return']
        crash_vol = scenario_data['crash_vol']
        recovery_return = scenario_data['recovery_return']
        recovery_vol = scenario_data['recovery_vol']
        
        # Convert annual to monthly properly
        monthly_crash_drift = (crash_return - 0.5 * crash_vol**2) / 12
        monthly_crash_vol = crash_vol / np.sqrt(12)
        monthly_recovery_drift = (recovery_return - 0.5 * recovery_vol**2) / 12
        monthly_recovery_vol = recovery_vol / np.sqrt(12)
        
        for month in range(1, total_months + 1):
            z = _generate_random_shocks(n_simulations, use_fat_tails)
            
            if month <= crash_months:
                month_drift = monthly_crash_drift
                month_vol = monthly_crash_vol
            else:
                # Recovery phase
                if scenario_key == 'covid_crash' and month <= 18:
                    recovery_annual = 0.35
                    recovery_vol_val = 0.25
                    month_drift = (recovery_annual - 0.5 * recovery_vol_val**2) / 12
                    month_vol = recovery_vol_val / np.sqrt(12)
                elif scenario_key == 'dot_com' and month <= 36:
                    decline_annual = -0.10
                    decline_vol = 0.28
                    month_drift = (decline_annual - 0.5 * decline_vol**2) / 12
                    month_vol = decline_vol / np.sqrt(12)
                else:
                    month_drift = monthly_recovery_drift
                    month_vol = monthly_recovery_vol
            
            current_values = current_values * np.exp(
                month_drift * dt + month_vol * np.sqrt(dt) * z
            )
            
            if month in yearly_checkpoints:
                idx = yearly_checkpoints.index(month)
                simulations[:, idx + 1] = current_values
        
        percentiles = {}
        for i, years in enumerate(time_horizons):
            values = simulations[:, i + 1]
            percentiles[years] = {
                'p5': float(np.percentile(values, 5)),
                'p10': float(np.percentile(values, 10)),
                'p25': float(np.percentile(values, 25)),
                'p50': float(np.percentile(values, 50)),
                'p75': float(np.percentile(values, 75)),
                'p90': float(np.percentile(values, 90)),
                'p95': float(np.percentile(values, 95)),
                'mean': float(np.mean(values)),
            }
        
        stress_results[scenario_key] = {
            'name': scenario_data['name'],
            'description': scenario_data['description'],
            'annual_return': crash_return,
            'volatility': crash_vol,
            'percentiles': percentiles
        }
    
    return stress_results


def _run_spy_projections_monthly(
    initial_capital: float,
    spy_return: float,
    spy_vol: float,
    n_simulations: int,
    time_horizons: List[int],
    use_fat_tails: bool = True
    ) -> Dict:
    """Run S&P 500 monthly baseline projections."""
    return _run_scenario_simulations_monthly(
        initial_capital, spy_return, spy_vol,
        n_simulations, time_horizons, 'S&P 500 (Monthly)',
        use_fat_tails=use_fat_tails
    )


def calculate_beat_spy_probability(
    mc_result: Dict,
    horizon: int,
    correlation: float = None,
    use_conservative_spy: bool = False,
    spy_backtest_return: float = None
) -> float:
    """
    Calculate probability that portfolio beats S&P using CORRELATED simulations.
    
    Two modes:
    1. Historical baseline (use_conservative_spy=False): S&P at 10% (historical long-term)
    2. Conservative comparison (use_conservative_spy=True): S&P with same 50/50 blend methodology
    
    Parameters
    ----------
    mc_result : Dict
        Monte Carlo result from run_monte_carlo
    horizon : int
        Year horizon (1, 3, 5, or 10)
    correlation : float, optional
        Correlation between portfolio and S&P. If None, uses from mc_result params.
    use_conservative_spy : bool
        If True, apply Conservative 50/50 blend methodology to S&P
        If False, use historical S&P baseline (10%)
    spy_backtest_return : float, optional
        S&P backtest return (annual). If provided, used for Conservative calculation.
    
    Returns
    -------
    float
        Probability (0-1) that portfolio value > S&P value
    """
    params = mc_result.get('params', {})
    initial_capital = mc_result.get('initial_capital', 100000)
    
    # Get portfolio parameters
    port_return = params.get('selected_return', 0.10)
    port_vol = params.get('volatility', 0.20)
    
    # Determine S&P parameters based on mode
    if use_conservative_spy:
        # Apply same Conservative (50/50 blend) methodology to S&P
        # Use provided backtest return or default to historical S&P
        spy_bt = spy_backtest_return if spy_backtest_return is not None else params.get('spy_backtest_return', 0.10)
        # Conservative blend: 50% backtest + 50% market return
        spy_return = 0.5 * spy_bt + 0.5 * MARKET_RETURN
    else:
        # Historical S&P baseline
        spy_return = 0.10
    
    spy_vol = params.get('spy_vol', 0.15)
    
    # Get or use default correlation
    if correlation is None:
        correlation = params.get('correlation', 0.5)
    
    n_simulations = params.get('n_simulations', 10000)
    
    # Calculate drifts
    port_drift = port_return - 0.5 * port_vol**2
    spy_drift = spy_return - 0.5 * spy_vol**2
    
    # Generate correlated random shocks
    z_portfolio = np.random.standard_normal(n_simulations)
    z_spy = correlation * z_portfolio + np.sqrt(max(0, 1 - correlation**2)) * np.random.standard_normal(n_simulations)
    
    # Calculate outcomes at horizon using GBM
    port_outcomes = initial_capital * np.exp(port_drift * horizon + port_vol * np.sqrt(horizon) * z_portfolio)
    spy_outcomes = initial_capital * np.exp(spy_drift * horizon + spy_vol * np.sqrt(horizon) * z_spy)
    
    # Paired comparison
    beat_count = np.sum(port_outcomes > spy_outcomes)
    probability = beat_count / n_simulations
    
    return float(probability)


def calculate_var(
    mc_result: Dict,
    horizon: int,
    confidence_level: float = 0.95
) -> Dict:
    """
    Calculate Value at Risk (VaR) and Conditional VaR (CVaR).

    Parameters
    ----------
    mc_result : Dict
        Monte Carlo result
    horizon : int
        Year horizon
    confidence_level : float
        Confidence level (default: 95%)

    Returns
    -------
    Dict with VaR and CVaR metrics
    """
    if horizon not in mc_result['actual']['percentiles']:
        return {}

    values = np.array(mc_result['actual']['percentiles'][horizon]['all_values'])
    initial = mc_result['initial_capital']

    # Calculate returns
    returns = (values - initial) / initial

    # VaR: Loss at confidence level
    var_pct = np.percentile(returns, (1 - confidence_level) * 100)
    var_dollar = initial * var_pct

    # CVaR: Expected loss beyond VaR
    cvar_mask = returns <= var_pct
    if np.any(cvar_mask):
        cvar_pct = np.mean(returns[cvar_mask])
    else:
        cvar_pct = var_pct
    cvar_dollar = initial * cvar_pct

    return {
        'confidence': confidence_level,
        'var_pct': float(var_pct),
        'var_dollar': float(var_dollar),
        'cvar_pct': float(cvar_pct),
        'cvar_dollar': float(cvar_dollar),
        'worst_case': float(np.min(returns)),
        'best_case': float(np.max(returns)),
    }


def get_projection_summary(
    mc_result: Dict,
    horizon: int
) -> Dict:
    """Get summary projection data for a specific horizon."""

    if horizon not in mc_result['actual']['percentiles']:
        return {}

    actual = mc_result['actual']['percentiles'][horizon]
    blend = mc_result['blend']['percentiles'][horizon]
    spy = mc_result['spy_baseline']['percentiles'][horizon]

    beat_prob = mc_result.get('beat_spy_probability', {}).get(horizon, 0.5)
    var_metrics = calculate_var(mc_result, horizon)

    stress_summary = {}
    for scenario_key, scenario_data in mc_result.get('stress', {}).items():
        if horizon in scenario_data['percentiles']:
            stress_summary[scenario_key] = {
                'name': scenario_data['name'],
                'p50': scenario_data['percentiles'][horizon]['p50'],
                'p10': scenario_data['percentiles'][horizon]['p10'],
            }

    return {
        'horizon': horizon,
        'initial_capital': mc_result['initial_capital'],
        'actual': {
            'p5': actual['p5'],
            'p10': actual['p10'],
            'p25': actual['p25'],
            'p50': actual['p50'],
            'p75': actual['p75'],
            'p90': actual['p90'],
            'p95': actual['p95'],
            'mean': actual['mean'],
        },
        'blend': {
            'p50': blend['p50'],
        },
        'spy': {
            'p50': spy['p50'],
        },
        'beat_spy_probability': beat_prob,
        'var': var_metrics,
        'stress_scenarios': stress_summary
    }


def generate_projection_chart_data(
    mc_result: Dict,
    backtest_cumulative: pd.Series = None,
    backtest_dates: List[str] = None
) -> Dict:
    """
    Generate data for combined backtest + future chart.

    Returns data structure suitable for plotting with both
    historical backtest and future projections.
    """

    max_years = max(TIME_HORIZONS)
    all_years = list(range(max_years + 1))

    result = {
        'years': all_years,
        'actual': {},
        'spy': {},
        'stress': {},
        'backtest': None
    }

    for years in all_years:
        if years == 0:
            result['actual'][years] = {'p50': mc_result['initial_capital']}
            result['spy'][years] = {'p50': mc_result['initial_capital']}
        elif years in mc_result['actual']['percentiles']:
            p = mc_result['actual']['percentiles'][years]
            result['actual'][years] = {
                'p5': p['p5'],
                'p10': p['p10'],
                'p25': p['p25'],
                'p50': p['p50'],
                'p75': p['p75'],
                'p90': p['p90'],
                'p95': p['p95'],
            }

            sp = mc_result['spy_baseline']['percentiles'][years]
            result['spy'][years] = {
                'p50': sp['p50'],
            }

    # Add stress scenario paths
    for scenario_key, scenario_data in mc_result.get('stress', {}).items():
        result['stress'][scenario_key] = {
            'name': scenario_data['name'],
            'values': {y: scenario_data['percentiles'].get(y, {}).get('p50')
                      for y in all_years if y in scenario_data['percentiles'] or y == 0}
        }
        result['stress'][scenario_key]['values'][0] = mc_result['initial_capital']

    if backtest_cumulative is not None and len(backtest_cumulative) > 0:
        result['backtest'] = {
            'values': backtest_cumulative.tolist(),
            'dates': backtest_dates if backtest_dates else list(backtest_cumulative.index.astype(str))
        }

    return result


def run_monte_carlo_with_backtest(
    initial_capital: float,
    backtest_returns: pd.Series,
    spy_returns: pd.Series = None,
    n_simulations: int = N_SIMULATIONS,
    time_horizons: List[int] = TIME_HORIZONS,
    seed: int = 42
) -> Dict:
    """
    Run Monte Carlo using actual backtest returns for calibration.

    This is the recommended approach - uses historical return distribution
    instead of assuming a parametric model.

    Parameters
    ----------
    initial_capital : float
        Starting portfolio value
    backtest_returns : pd.Series
        Historical daily/weekly returns from backtest
    spy_returns : pd.Series, optional
        Historical S&P 500 returns for comparison
    n_simulations : int
        Number of simulation paths
    time_horizons : List[int]
        Years to project
    seed : int
        Random seed

    Returns
    -------
    Dict with projection data
    """
    np.random.seed(seed)

    # Calculate annualized return and volatility from backtest
    n_periods = len(backtest_returns)
    total_return = (1 + backtest_returns).prod() - 1

    # Assume returns are daily if > 50 periods
    if n_periods > 50:
        periods_per_year = 252
    elif n_periods > 12:
        periods_per_year = 12
    else:
        periods_per_year = 1

    # Annualized return
    years = n_periods / periods_per_year
    annual_return = (1 + total_return) ** (1 / years) - 1

    # Annualized volatility
    annual_vol = backtest_returns.std() * np.sqrt(periods_per_year)

    # Use bootstrap for more realistic simulation
    result = run_monte_carlo(
        initial_capital=initial_capital,
        annual_return=annual_return,
        annual_vol=annual_vol,
        n_simulations=n_simulations,
        time_horizons=time_horizons,
        seed=seed
    )

    result['calibration'] = {
        'method': 'historical_annualization',
        'backtest_periods': n_periods,
        'periods_per_year': periods_per_year,
        'total_return': float(total_return),
        'annualized_return': float(annual_return),
        'annualized_volatility': float(annual_vol),
    }

    return result