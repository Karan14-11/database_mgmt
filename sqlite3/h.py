import pandas as pd
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(processName)s - %(message)s')

def alpha_a1_token_book(ref_path: str, settle_path: str, out_path: str) -> str:

    
    if not os.path.exists(ref_path):
        raise FileNotFoundError(f"Missing dependency: {ref_path}")
    if not os.path.exists(settle_path):
        raise FileNotFoundError(f"Missing dependency: {settle_path}")

    ref_df = pd.read_csv(ref_path)
    chunk_size = 100_000 
    
    if os.path.exists(out_path):
        os.remove(out_path)

    with pd.read_csv(settle_path, chunksize=chunk_size) as settle_reader:
        for i, settle_chunk in enumerate(settle_reader):
            
            merged = pd.merge(
                ref_df, 
                settle_chunk, 
                on='ponny', 
                how='inner', 
                suffixes=('_ref', '_settle')
            )
            
            merged = merged.dropna(subset=['settle_px'])
            result_chunk = pd.DataFrame({
                'symbol': merged['symbol'],
                'asset_class': merged['asset_class'],
                'tier': merged['tier'],
                'settle_px_prev': merged['settle_px']
            })
            
            # 5. Append to disk
            write_header = (i == 0)
            result_chunk.to_csv(out_path, mode='a', index=False, header=write_header)

    # 6. Final sort (assuming the heavily filtered output now fits in RAM)
    final_df = pd.read_csv(out_path)
    final_df = final_df.sort_values(by='symbol', ascending=True, kind='mergesort')
    final_df.to_csv(out_path, index=False)
    
    logging.info("Completed A1 Heuristic.")
    return out_path


def alpha_a2_flow_risk(flow_path: str, token_book_path: str, out_path: str) -> str:
    """
    Heuristic 4.2: ALPHA_FLOW_RISK
    Requires the output of A1 (token_book) to run.
    """
    logging.info(f"Starting A2 Heuristic. Output: {out_path}")
    
    # Read dependencies
    flow_df = pd.read_csv(flow_path)
    book_df = pd.read_csv(token_book_path)
    
    buy_vol = flow_df[flow_df['side'] == 'buy'].groupby('symbol')['volume'].sum()
    sell_vol = flow_df[flow_df['side'] == 'sell'].groupby('symbol')['volume'].sum()
    
    net_flow = pd.DataFrame({'buy_vol': buy_vol, 'sell_vol': sell_vol}).fillna(0)
    net_flow['net_position'] = net_flow['buy_vol'] - net_flow['sell_vol']
    net_flow = net_flow.reset_index()
    
    # 2. Join with token book
    risk_df = pd.merge(net_flow, book_df, on='symbol', how='inner')
    
    # 3. Calculate risk
    risk_df['notional_risk'] = risk_df['net_position'] * risk_df['settle_px_prev']
    
    # 4. Sort and save
    risk_df['abs_risk'] = risk_df['notional_risk'].abs()
    risk_df = risk_df.sort_values(by=['abs_risk', 'symbol'], ascending=[False, True], kind='mergesort')
    risk_df.drop(columns=['abs_risk']).to_csv(out_path, index=False)
    
    logging.info("Completed A2 Heuristic.")
    return out_path






def beta_b1_tick_summary(ticks_path: str, out_path: str) -> str:
    """Calculates OHLC (Open, High, Low, Close) from raw ticks."""
    logging.info(f"Running B1 Heuristic...")
    df = pd.read_csv(ticks_path)
    
    # Sort by timestamp to ensure 'first' and 'last' represent Open/Close correctly
    df = df.sort_values(by=['symbol', 'timestamp'])
    
    agg_funcs = {
        'price': ['first', 'max', 'min', 'last'],
        'volume': 'sum'
    }
    
    summary = df.groupby('symbol').agg(agg_funcs)
    summary.columns = ['open', 'high', 'low', 'close', 'total_volume']
    summary = summary.reset_index()
    
    # Filter 0 volume and sort lexicographically
    summary = summary[summary['total_volume'] > 0]
    summary = summary.sort_values('symbol', kind='mergesort')
    summary.to_csv(out_path, index=False)
    return out_path

def beta_b2_member_fees(ticks_path: str, members_path: str, policy_path: str, out_path: str) -> str:
    """Calculates member fees based on trading volume and policy tiers."""
    logging.info(f"Running B2 Heuristic...")
    ticks = pd.read_csv(ticks_path)
    members = pd.read_csv(members_path)
    policy = pd.read_csv(policy_path)
    
    # Calculate notional traded per member
    ticks['notional'] = ticks['price'] * ticks['volume']
    member_vol = ticks.groupby('member_id')['notional'].sum().reset_index()
    
    # Join tiers and fee rates
    df = pd.merge(member_vol, members, on='member_id', how='inner')
    df = pd.merge(df, policy, on='tier', how='inner')
    
    # Calculate fee
    df['total_fees'] = df['notional'] * df['fee_rate']
    
    df[['member_id', 'tier', 'notional', 'total_fees']].sort_values('member_id').to_csv(out_path, index=False)
    return out_path

# --- CONSOLIDATED HEURISTICS ---

def consolidated_c1_report(alpha_a1_path: str, beta_b1_path: str, out_path: str) -> str:
    """Reconciles ALPHA's Previous Settlement with BETA's Current Close."""
    logging.info(f"Running C1 Heuristic...")
    alpha = pd.read_csv(alpha_a1_path)
    beta = pd.read_csv(beta_b1_path)
    
    # Outer join to catch symbols unique to one exchange
    df = pd.merge(
        alpha[['symbol', 'settle_px_prev']], 
        beta[['symbol', 'close']], 
        on='symbol', 
        how='outer'
    )
    
    # Fill missing with 0.0 for math safety
    df = df.fillna({'settle_px_prev': 0.0, 'close': 0.0})
    df['price_diff'] = df['close'] - df['settle_px_prev']
    
    df = df.sort_values('symbol', kind='mergesort')
    df.to_csv(out_path, index=False)
    return out_path