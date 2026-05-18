import pytest
import pandas as pd
import os
from pandas.testing import assert_frame_equal

# Import the functions we wrote earlier
from calendar_engine import get_ptd
from heuristics import alpha_a1_token_book, beta_b1_tick_summary

# ---------------------------------------------------------
# 1. TEST CALENDAR ENGINE (Base: Weekdays Only)
# ---------------------------------------------------------

def test_get_ptd_standard_weekday():
    """Test standard Tuesday -> Monday"""
    assert get_ptd("20260519") == "20260518"

def test_get_ptd_monday_to_friday():
    """Test Monday -> goes back to Friday (-3 days)"""
    assert get_ptd("20260518") == "20260515"

def test_get_ptd_sunday_to_friday():
    """Test Sunday -> goes back to Friday (-2 days)"""
    assert get_ptd("20260517") == "20260515"

# ---------------------------------------------------------
# 2. TEST A1: TOKEN BOOK (Joins, Filters, and Sorting)
# ---------------------------------------------------------

def test_alpha_a1_token_book(tmp_path):
    """
    Tests that A1 correctly inner joins, drops missing settle prices,
    carries lagged fields, and sorts lexicographically.
    """
    # 1. Setup Mock Input Data
    ref_file = tmp_path / "alpha_ref.csv"
    settle_file = tmp_path / "alpha_settle.csv"
    out_file = tmp_path / "alpha_token_book.csv"

    pd.DataFrame({
        'symbol': ['ZETA', 'ALPHA', 'BETA', 'GAMMA'],
        'asset_class': ['crypto', 'crypto', 'crypto', 'crypto'],
        'tier': [1, 1, 2, 2]
    }).to_csv(ref_file, index=False)

    pd.DataFrame({
        'symbol': ['ALPHA', 'BETA', 'ZETA', 'DELTA'], # DELTA is not in ref
        'settle_px': [100.5, None, 50.0, 200.0]       # BETA has missing price
    }).to_csv(settle_file, index=False)

    # 2. Execute Heuristic
    alpha_a1_token_book(str(ref_file), str(settle_file), str(out_file))

    # 3. Read Result
    result_df = pd.read_csv(out_file)

    # 4. Define Expected Output
    # Expected: 
    # - DELTA dropped (inner join failure)
    # - BETA dropped (missing settle_px)
    # - Sorted lexicographically (ALPHA then ZETA)
    expected_df = pd.DataFrame({
        'symbol': ['ALPHA', 'ZETA'],
        'asset_class': ['crypto', 'crypto'],
        'tier': [1, 1],
        'settle_px_prev': [100.5, 50.0]
    })

    # 5. Assert exact match (checks values, column types, and row order)
    assert_frame_equal(result_df, expected_df)

# ---------------------------------------------------------
# 3. TEST B1: TICK SUMMARY (OHLC & Volume Aggregation)
# ---------------------------------------------------------

def test_beta_b1_tick_summary(tmp_path):
    """
    Tests that B1 correctly aggregates ticks into Open, High, 
    Low, Close (OHLC) and filters out zero-volume assets.
    """
    ticks_file = tmp_path / "beta_ticks.csv"
    out_file = tmp_path / "beta_tick_summary.csv"

    # Input data: Deliberately out of chronological order to test sorting
    pd.DataFrame({
        'symbol': ['BTC', 'BTC', 'BTC', 'ETH', 'ETH'],
        'timestamp': [102, 100, 101, 100, 101], # Unsorted time
        'price': [62000, 60000, 59000, 3000, 3100],
        'volume': [1.5, 2.0, 0.5, 0.0, 0.0] # ETH has zero total volume
    }).to_csv(ticks_file, index=False)

    # Execute
    beta_b1_tick_summary(str(ticks_file), str(out_file))
    result_df = pd.read_csv(out_file)

    # Expected:
    # - ETH dropped entirely (total volume is 0)
    # - BTC sorted by time: 100(Open), 101(Low), 102(High/Close)
    # Open=60000, High=62000, Low=59000, Close=62000, Vol=4.0
    expected_df = pd.DataFrame({
        'symbol': ['BTC'],
        'open': [60000.0],
        'high': [62000.0],
        'low': [59000.0],
        'close': [62000.0],
        'total_volume': [4.0]
    })

    assert_frame_equal(result_df, expected_df)