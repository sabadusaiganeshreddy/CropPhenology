import os
import sys
import pandas as pd
import numpy as np
import matplotlib.dates as mdates


REQUIRED_COLS = {'plot_id', 'NDVI', 'SAVI', 'NDWI', 'date'}

def find_input_csv():
    """Pick the first .csv in the current folder that contains the required columns."""
    csvs = [f for f in os.listdir('.') if f.lower().endswith('.csv')]
    if not csvs:
        raise FileNotFoundError("No CSV file found in the current directory.")
    for fname in csvs:
        try:
            # Read a small sample to check columns quickly
            preview = pd.read_csv(fname, nrows=5)
            if REQUIRED_COLS.issubset(set(map(str, preview.columns))):
                return fname
        except Exception:
            continue
    # Fallback: if none passed the column check, still use the first and let errors surface
    return csvs[0]

def clean_and_prepare(df: pd.DataFrame) -> pd.DataFrame:
    # Drop completely empty rows
    df = df.dropna(how='all').copy()

    # Remove accidental repeated header rows (e.g., when multiple CSVs were appended)
    def is_header_like_row(row) -> bool:
        try:
            return (
                str(row.get('date', '')).strip().lower() == 'date' or
                str(row.get('plot_id', '')).strip().lower() == 'plot_id' or
                str(row.get('ndvi', '')).strip().lower() == 'ndvi' or
                str(row.get('savi', '')).strip().lower() == 'savi' or
                str(row.get('ndwi', '')).strip().lower() == 'ndwi'
            )
        except Exception:
            return False

    header_mask = df.apply(is_header_like_row, axis=1)
    if header_mask.any():
        print(f"Removing {int(header_mask.sum())} repeated header-like row(s).")
        df = df.loc[~header_mask].copy()

    # Parse dates robustly
    date_str = df['date'].astype(str).str.strip()
    try:
        # pandas >= 2.0 supports format='mixed'
        parsed = pd.to_datetime(date_str, errors='coerce', format='mixed')
    except TypeError:
        # Fallback for older pandas: let pandas infer; coerce bad ones
        parsed = pd.to_datetime(date_str, errors='coerce')
    df['date'] = parsed

    bad_dates = df['date'].isna().sum()
    if bad_dates:
        print(f"Dropping {bad_dates} row(s) with invalid dates.")
        df = df.dropna(subset=['date']).copy()

    # Ensure numeric columns are numeric
    for col in ['plot_id', 'NDVI', 'SAVI', 'NDWI']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Drop rows with missing required numeric values
    before = len(df)
    df = df.dropna(subset=['plot_id', 'NDVI', 'SAVI', 'NDWI']).copy()
    dropped = before - len(df)
    if dropped:
        print(f"Dropped {dropped} row(s) with non-numeric values in required columns.")

    # Sort for time-diff calculations
    df = df.sort_values(by=['plot_id', 'date']).reset_index(drop=True)

    # Optionally cast plot_id to int if it's integral
    if np.all(np.mod(df['plot_id'], 1) == 0):
        df['plot_id'] = df['plot_id'].astype(int)

    return df

def calculate_slope(group: pd.DataFrame, column_name: str, window_days=16) -> pd.Series:
    """
    Calculate slope using a TEMPORAL 16-day window.
    For each observation, considers all points within ±8 days and computes median slope.
    This provides very smooth, stable slope estimates for phenology classification.
    
    Args:
        group: DataFrame for a single plot
        column_name: Name of the vegetation index column
        window_days: Temporal window in days (default 16)
    """
    slopes = []
    dates = group['date'].values
    values = group[column_name].values
    
    half_window = window_days / 2  # ±8 days from center point
    
    for i in range(len(group)):
        current_date = dates[i]
        
        # Find all points within the temporal window
        time_diffs_days = np.abs((dates - current_date).astype('timedelta64[D]').astype(float))
        within_window = time_diffs_days <= half_window
        
        # Need at least 2 points to calculate slope
        if within_window.sum() < 2:
            slopes.append(0)
            continue
        
        # Get points within window
        window_dates = dates[within_window]
        window_values = values[within_window]
        
        # Calculate pairwise slopes within the window and take median
        # This is more robust than simple linear regression
        pairwise_slopes = []
        for j in range(len(window_dates)):
            for k in range(j + 1, len(window_dates)):
                time_diff = (window_dates[k] - window_dates[j]).astype('timedelta64[D]').astype(float)
                if time_diff > 0:
                    value_diff = window_values[k] - window_values[j]
                    pairwise_slopes.append(value_diff / time_diff)
        
        if pairwise_slopes:
            # Use median of all pairwise slopes (very robust!)
            slopes.append(np.median(pairwise_slopes))
        else:
            slopes.append(0)
    
    return pd.Series(slopes, index=group.index).fillna(0).replace([np.inf, -np.inf], 0)

def main():
    print("Starting data processing...")
    try:
        input_file_path = find_input_csv()
        print(f"Using input file: {input_file_path}")
    except Exception as e:
        print(f"Error selecting input CSV: {e}")
        sys.exit(1)

    # Load full CSV now that we chose one
    try:
        df = pd.read_csv(input_file_path)
    except Exception as e:
        print(f"Failed to read '{input_file_path}': {e}")
        sys.exit(1)

    # Validate columns
    missing = REQUIRED_COLS - set(map(str, df.columns))
    if missing:
        print(f"Input file is missing required columns: {missing}")
        sys.exit(1)

    # Clean & prepare
    df = clean_and_prepare(df)
    print("Data loading and cleaning complete.")
    print(f"Rows after cleaning: {len(df)}")

    # Compute slopes
    print("Calculating slopes for NDVI, SAVI, and NDWI...")
    grouped = df.groupby('plot_id', group_keys=False)

    df['NDVI_slope'] = grouped.apply(lambda g: calculate_slope(g, 'NDVI'), include_groups=False)
    df['SAVI_slope'] = grouped.apply(lambda g: calculate_slope(g, 'SAVI'), include_groups=False)
    df['NDWI_slope'] = grouped.apply(lambda g: calculate_slope(g, 'NDWI'), include_groups=False)
    print("Slope calculation finished.")
    # --- Rule-based phenology classification --------------------------------------
    # --- Four-stage phenology classification (Seedling, Tillering, Growth, Ripening) ---
    from typing import Dict

    def add_four_stage_classification(df: pd.DataFrame, params: Dict = None) -> pd.DataFrame:
        """
        Crop phenology classification based on greenness and slope trends.
        Thresholds are DATA-DRIVEN from field observations (percentiles of actual measurements).
        
        Adds:
          - G (0.6*NDVI + 0.4*SAVI): Combined greenness index
          - W (=NDWI): Water content index
          - sG (avg slope of NDVI & SAVI): Rate of greenness change
          - G_sm, sG_sm, W_sm: Rolling-median smoothed versions
          - stage_4: one of {"Bare","Seedling","Tillering","Growth","Ripening"}
          - stage4_code: {0,1,2,3,4}
        
        Classification Logic (data-driven thresholds):
          0. BARE (0): Low greenness + flat slope → no crop / fallow / bare soil
          1. SEEDLING (1): Low greenness (<0.30) + RISING → early establishment
          2. TILLERING (2): Mid greenness (0.30-0.50) + RISING → canopy establishment
          3. GROWTH (3): High greenness (≥0.50) + rising/stable → peak vegetative
          4. RIPENING (4): Any falling trend (slope < -0.001) → senescence/maturation
          
        Note: Requires ACTIVE rising slope for Seedling/Tillering to distinguish from bare fields.
        """
        if params is None:
            # Data-driven defaults based on actual field measurements
            # These thresholds are derived from the dataset percentiles
            params = {
                # Greenness bands (G ≈ canopy vigor)
                # Based on quartiles of observed greenness values
                "G_seed_max": 0.30,   # <0.30 early establishment (below 25th percentile)
                "G_till_max": 0.50,   # 0.30-0.50 tillering/establishment (25-50th percentile)
                "G_high": 0.50,       # >=0.50 peak growth (above median)

                # Slopes (per day) - based on observed slope distribution
                "rise_strong": 0.0068,   # strong green-up (75th percentile)
                "rise_weak": 0.0010,     # modest rise
                "flat_abs": 0.0010,      # near-flat (-0.001 to +0.001)
                "fall_weak": -0.0010,    # modest decline
                "fall_strong": -0.0135,  # clear senescence (10th percentile)

                # Water override (kept conservative)
                "W_water": 0.45,  # very wet + low greenness → treat as Seedling-ish

                # Smoothing
                "roll_window": 3,
            }

        out = df.copy()

        # Features
        out["G"] = 0.6 * out["NDVI"] + 0.4 * out["SAVI"]
        out["W"] = out["NDWI"]
        out["sG"] = 0.5 * (out["NDVI_slope"] + out["SAVI_slope"])

        # Smooth per plot (rolling median)
        def _smooth(g):
            w = params["roll_window"]
            g = g.sort_values("date")
            g["G_sm"] = g["G"].rolling(w, center=True, min_periods=1).median()
            g["sG_sm"] = g["sG"].rolling(w, center=True, min_periods=1).median()
            g["W_sm"] = g["W"].rolling(w, center=True, min_periods=1).median()
            return g

        out = out.groupby("plot_id", group_keys=False).apply(_smooth)

        P = params
        G = out["G_sm"]
        sG = out["sG_sm"]
        W = out["W_sm"]

        # Helper masks
        rising_str = sG >= P["rise_strong"]
        rising_weak = (sG >= P["rise_weak"]) & ~rising_str
        flatish = sG.abs() <= P["flat_abs"]
        falling_weak = (sG <= P["fall_weak"]) & (sG > P["fall_strong"])
        falling_str = sG <= P["fall_strong"]

        stage = np.empty(len(out), dtype=object)
        code = np.empty(len(out), dtype=int)
        stage[:] = "Bare"  # default fallback for uncategorized (likely bare/fallow fields)
        code[:] = 0  # 0 = Bare/No-Crop

        # Classification in priority order (later rules override earlier ones only when appropriate)
        
        # 1. RIPENING: Any falling trend (must check first to avoid conflicts)
        #    - Crop senescence/maturation phase
        m = (falling_weak | falling_str)
        stage[m] = "Ripening"
        code[m] = 4

        # 2. GROWTH: High greenness with rising or stable trend (peak vegetative growth)
        #    - Requires rising/flat trend to distinguish from bare fields at plateau
        m = (G >= P["G_high"]) & (rising_str | rising_weak | flatish)
        stage[m] = "Growth"
        code[m] = 3

        # 3. TILLERING: Mid-range greenness with ACTIVE rising trend (establishment phase)
        #    - Must be BELOW Growth threshold to avoid overlap
        #    - Requires rising slope to avoid classifying static bare fields
        m = (G >= P["G_seed_max"]) & (G < P["G_high"]) & (rising_str | rising_weak)
        stage[m] = "Tillering"
        code[m] = 2
        
        # 3b. TILLERING (plateau): Mid greenness that's flat but came from rising
        #     - Allow flat slope ONLY if greenness is reasonably high (>0.35)
        m = (G >= 0.35) & (G < P["G_high"]) & flatish
        stage[m] = "Tillering"
        code[m] = 2

        # 4. SEEDLING: Low greenness with rising trend (early establishment)
        #    - MUST have rising slope to distinguish from bare soil
        m = (G < P["G_seed_max"]) & (rising_str | rising_weak)
        stage[m] = "Seedling"
        code[m] = 1

        # 5. SEEDLING (water override): Very wet conditions with low greenness (transplanted/flooded)
        #    - Special case for flooded/transplanted fields
        m = (W >= P["W_water"]) & (G < 0.35)
        stage[m] = "Seedling"
        code[m] = 1
        
        # 6. Handle ambiguous low greenness with flat/falling trend in early season
        #    If greenness is very low and flat (not rising), likely still establishing
        m = (G < P["G_seed_max"]) & flatish & (stage == "Growth")  # Only override default
        stage[m] = "Seedling"
        code[m] = 1

        out["stage_4"] = stage
        out["stage4_code"] = code

        # (Optional) print stage transitions per plot
        def _transitions(g):
            g = g.sort_values("date")
            pid = g["plot_id"].iloc[0]
            runs = (g["stage_4"] != g["stage_4"].shift()).fillna(True)
            for d, s in zip(g.loc[runs, "date"], g.loc[runs, "stage_4"]):
                print(f"plot {pid}: {d.date()} → {s}")
            return g

        out = out.groupby("plot_id", group_keys=False).apply(_transitions)
        return out

    # Apply 4-stage classification (replace previous add_phenology_classification call)
    df = add_four_stage_classification(df)

    # (Optional) Save first occurrence of each stage per plot
    summary4 = (
        df.sort_values(["plot_id", "date"])
        .drop_duplicates(subset=["plot_id", "stage_4"])
        .loc[:, ["plot_id", "stage_4", "date"]]
        .sort_values(["plot_id", "date"])
    )
    summary4.to_csv("phenology_stage4_transitions.csv", index=False)
    print("Saved: phenology_stage4_transitions.csv")

    # Save
    output_file_path = 'plot_data_with_slopes.csv'
    try:
        df.to_csv(output_file_path, index=False)
    except Exception as e:
        print(f"Failed to write output CSV: {e}")
        sys.exit(1)

    # Small summary
    n_plots = df['plot_id'].nunique()
    date_min = df['date'].min()
    date_max = df['date'].max()
    print("\n✅ Success!")
    print(f"Saved: {output_file_path}")
    print(f"Plots: {n_plots}, Rows: {len(df)}, Date range: {date_min.date()} → {date_max.date()}")
    
    return df  # Return the DataFrame so it can be used for plotting

# --- 5. Plot slopes for plot 1 and plot 2 ---
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def visualize_phenology_classification(df, plot_id, outdir="figures"):
    """
    Visualize phenology classification for a specific plot showing:
    - NDVI, SAVI, NDWI over time
    - Combined greenness index (G)
    - Classified phenology stages as colored background regions
    """
    os.makedirs(outdir, exist_ok=True)
    
    # Filter data for the specific plot
    plot_data = df[df['plot_id'] == plot_id].copy()
    if plot_data.empty:
        print(f"Warning: no data for plot_id={plot_id}; skipping.")
        return
    
    # Ensure date is datetime and sort
    if not np.issubdtype(plot_data['date'].dtype, np.datetime64):
        try:
            plot_data['date'] = pd.to_datetime(plot_data['date'], errors='coerce', format='mixed')
        except TypeError:
            plot_data['date'] = pd.to_datetime(plot_data['date'], errors='coerce')
    plot_data = plot_data.sort_values('date').reset_index(drop=True)
    
    # Define colors for each stage
    stage_colors = {
        'Bare': '#D3D3D3',        # Light gray
        'Seedling': '#90EE90',    # Light green
        'Tillering': '#FFD700',   # Gold
        'Growth': '#228B22',      # Forest green
        'Ripening': '#FF8C00'     # Dark orange
    }
    
    # Create figure with subplots
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    fig.suptitle(f'Phenology Classification - Plot {plot_id}', fontsize=16, fontweight='bold')
    
    # Plot 1: NDVI, SAVI, NDWI
    ax1 = axes[0]
    ax1.plot(plot_data['date'], plot_data['NDVI'], 'o-', label='NDVI', linewidth=2, markersize=5)
    ax1.plot(plot_data['date'], plot_data['SAVI'], 's-', label='SAVI', linewidth=2, markersize=5)
    ax1.plot(plot_data['date'], plot_data['NDWI'], '^-', label='NDWI', linewidth=2, markersize=5)
    ax1.set_ylabel('Index Value', fontsize=11)
    ax1.set_title('Vegetation Indices', fontsize=12, fontweight='bold')
    ax1.legend(loc='best', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Combined Greenness (G) with smoothed version
    ax2 = axes[1]
    if 'G' in plot_data.columns:
        ax2.plot(plot_data['date'], plot_data['G'], 'o-', label='G (0.6*NDVI + 0.4*SAVI)', 
                 linewidth=2, markersize=5, alpha=0.5, color='lightgreen')
    if 'G_sm' in plot_data.columns:
        ax2.plot(plot_data['date'], plot_data['G_sm'], 's-', label='G smoothed', 
                 linewidth=2.5, markersize=6, color='darkgreen')
    ax2.set_ylabel('Greenness Index', fontsize=11)
    ax2.set_title('Combined Greenness Index', fontsize=12, fontweight='bold')
    ax2.legend(loc='best', fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Phenology Stage Code with colored regions
    ax3 = axes[2]
    if 'stage4_code' in plot_data.columns:
        ax3.plot(plot_data['date'], plot_data['stage4_code'], 'ko-', 
                 linewidth=2, markersize=7, label='Stage Code')
        ax3.set_ylabel('Stage Code', fontsize=11)
        ax3.set_yticks([0, 1, 2, 3, 4])
        ax3.set_yticklabels(['Bare\n(0)', 'Seedling\n(1)', 'Tillering\n(2)', 'Growth\n(3)', 'Ripening\n(4)'])
    
    # Add colored background regions for each stage
    if 'stage_4' in plot_data.columns:
        current_stage = None
        start_idx = 0
        
        for idx in range(len(plot_data)):
            stage = plot_data.iloc[idx]['stage_4']
            
            if stage != current_stage:
                # When stage changes, fill the previous region
                if current_stage is not None and start_idx < idx:
                    color = stage_colors.get(current_stage, '#CCCCCC')
                    for ax in axes:
                        ax.axvspan(plot_data.iloc[start_idx]['date'], 
                                  plot_data.iloc[idx]['date'],
                                  alpha=0.2, color=color, zorder=0)
                
                current_stage = stage
                start_idx = idx
        
        # Fill the last region
        if current_stage is not None and start_idx < len(plot_data):
            color = stage_colors.get(current_stage, '#CCCCCC')
            for ax in axes:
                ax.axvspan(plot_data.iloc[start_idx]['date'], 
                          plot_data.iloc[-1]['date'],
                          alpha=0.2, color=color, zorder=0)
    
    ax3.set_title('Phenology Stage Classification', fontsize=12, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.set_xlabel('Date', fontsize=11)
    
    # Detect dates where phenology class changes
    transition_dates = []
    if 'stage_4' in plot_data.columns and len(plot_data) > 0:
        # Add first date
        transition_dates.append(plot_data.iloc[0]['date'])
        
        # Find all dates where stage changes
        for idx in range(1, len(plot_data)):
            if plot_data.iloc[idx]['stage_4'] != plot_data.iloc[idx-1]['stage_4']:
                transition_dates.append(plot_data.iloc[idx]['date'])
        
        # Add last date
        if plot_data.iloc[-1]['date'] not in transition_dates:
            transition_dates.append(plot_data.iloc[-1]['date'])
    else:
        # Fallback: use all dates if stage_4 not available
        transition_dates = plot_data['date'].tolist()
    
    # Format x-axis for all subplots with transition dates only
    for ax in axes:
        ax.set_xticks(transition_dates)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.tick_params(axis='x', rotation=45, labelsize=9)
    
    # Create custom legend for stages
    from matplotlib.patches import Patch
    stage_patches = [Patch(facecolor=stage_colors[stage], alpha=0.5, label=stage) 
                     for stage in ['Bare', 'Seedling', 'Tillering', 'Growth', 'Ripening']]
    ax3.legend(handles=stage_patches, loc='upper left', fontsize=10, 
               title='Phenology Stages', framealpha=0.9)
    
    plt.tight_layout()
    
    # Save figure
    fname = os.path.join(outdir, f"plot_{plot_id}_phenology_classification.png")
    fig.savefig(fname, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {fname}")


def plot_slopes_for_plots(df, plot_ids=(1, 2), outdir="figures"):
    os.makedirs(outdir, exist_ok=True)

    # Ensure 'date' is datetime and data is sorted
    if not np.issubdtype(df['date'].dtype, np.datetime64):
        df = df.copy()
        try:
            df['date'] = pd.to_datetime(df['date'], errors='coerce', format='mixed')
        except TypeError:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date'])
    df = df.sort_values(['plot_id', 'date'])

    metrics = ['NDVI', 'NDWI', 'SAVI']
    for pid in plot_ids:
        g = df.loc[df['plot_id'] == pid].copy()
        if g.empty:
            print(f"Warning: no rows for plot_id={pid}; skipping.")
            continue

        for m in metrics:
            slope_col = f"{m}_slope"
            if slope_col not in g.columns:
                print(f"Warning: '{slope_col}' column not found; skipping.")
                continue

            fig, ax = plt.subplots(figsize=(12, 5))
            
            # Plot the slope line
            ax.plot(g['date'], g[slope_col], linewidth=2, color='#1f77b4', alpha=0.8)
            
            # Add horizontal line at y=0 to show transitions clearly
            ax.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='Zero slope')
            
            # Set x-axis to show ticks at 10-day intervals
            dates = g['date'].values
            
            # Create 10-day interval ticks
            start_date = pd.to_datetime(dates[0])
            end_date = pd.to_datetime(dates[-1])
            
            # Generate ticks every 10 days from start to end
            tick_dates = pd.date_range(start=start_date, end=end_date, freq='10D')
            
            # Convert to numpy datetime64 for consistency
            tick_dates_np = tick_dates.to_numpy()
            
            # Set the ticks
            ax.set_xticks(tick_dates_np)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.tick_params(axis='x', labelsize=9, rotation=45)

            # Titles/labels/grid
            ax.set_title(f"{m} Slope for Plot {pid} (16-day window)", fontsize=12, fontweight='bold')
            ax.set_xlabel("Date", fontsize=10)
            ax.set_ylabel(f"Δ{m}/day", fontsize=10)
            ax.grid(True, which='major', linewidth=0.5, alpha=0.3)
            ax.legend(loc='best', fontsize=9)

            # Layout so labels aren't clipped
            plt.tight_layout()

            # Save
            fname = os.path.join(outdir, f"plot_{pid}_{m.lower()}_slope.png")
            fig.savefig(fname, dpi=150, bbox_inches='tight')
            plt.close(fig)
            print(f"Saved: {fname}")


def plot_comparison_charts(df, plot_ids=(1, 2, 3), outdir="figures"):
    """
    Generate comparison plots for multiple plots:
    1. Side-by-side comparison of NDVI, SAVI, NDWI
    2. Timeline comparison showing all three indices on same plot
    """
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    
    os.makedirs(outdir, exist_ok=True)
    
    # Filter data for the specified plots
    plot_data = df[df['plot_id'].isin(plot_ids)].copy()
    
    if plot_data.empty:
        print(f"No data found for plots {plot_ids}")
        return
    
    # === Plot 1: Side-by-side comparison ===
    fig, axes = plt.subplots(3, len(plot_ids), figsize=(6*len(plot_ids), 12))
    if len(plot_ids) == 1:
        axes = axes.reshape(-1, 1)
    
    indices = ['NDVI', 'SAVI', 'NDWI']
    colors = {'NDVI': 'green', 'SAVI': 'orange', 'NDWI': 'blue'}
    
    for col_idx, pid in enumerate(plot_ids):
        plot_df = plot_data[plot_data['plot_id'] == pid].sort_values('date')
        
        for row_idx, index_name in enumerate(indices):
            ax = axes[row_idx, col_idx]
            
            if not plot_df.empty:
                ax.plot(plot_df['date'], plot_df[index_name], 
                       color=colors[index_name], linewidth=2, marker='o', markersize=4)
                ax.set_title(f"Plot {pid} - {index_name}", fontsize=11, fontweight='bold')
                ax.set_xlabel("Date", fontsize=9)
                ax.set_ylabel(index_name, fontsize=9)
                ax.grid(True, alpha=0.3)
                ax.tick_params(axis='x', rotation=45, labelsize=8)
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            else:
                ax.text(0.5, 0.5, f'No data for Plot {pid}', 
                       ha='center', va='center', transform=ax.transAxes)
    
    plt.tight_layout()
    fname = os.path.join(outdir, f"comparison_plots_{'_'.join(map(str, plot_ids))}.png")
    fig.savefig(fname, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {fname}")
    
    # === Plot 2: Timeline comparison (all indices on same plot) ===
    fig, axes = plt.subplots(len(plot_ids), 1, figsize=(14, 5*len(plot_ids)))
    if len(plot_ids) == 1:
        axes = [axes]
    
    for idx, pid in enumerate(plot_ids):
        ax = axes[idx]
        plot_df = plot_data[plot_data['plot_id'] == pid].sort_values('date')
        
        if not plot_df.empty:
            for index_name in indices:
                ax.plot(plot_df['date'], plot_df[index_name], 
                       label=index_name, color=colors[index_name], 
                       linewidth=2, marker='o', markersize=4, alpha=0.7)
            
            ax.set_title(f"Plot {pid} - All Vegetation Indices Timeline", 
                        fontsize=12, fontweight='bold')
            ax.set_xlabel("Date", fontsize=10)
            ax.set_ylabel("Index Value", fontsize=10)
            ax.legend(loc='best', fontsize=10)
            ax.grid(True, alpha=0.3)
            ax.tick_params(axis='x', rotation=45, labelsize=9)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        else:
            ax.text(0.5, 0.5, f'No data for Plot {pid}', 
                   ha='center', va='center', transform=ax.transAxes)
    
    plt.tight_layout()
    fname = os.path.join(outdir, f"timeline_comparison_{'_'.join(map(str, plot_ids))}.png")
    fig.savefig(fname, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {fname}")


def plot_classification_comparison(df, plot_ids=(1, 2), outdir="figures"):
    """
    Compare phenology classifications for two plots side-by-side
    """
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    
    os.makedirs(outdir, exist_ok=True)
    
    # Define colors for each stage
    stage_colors = {
        'Bare': '#D3D3D3',        # Light gray
        'Seedling': '#90EE90',    # Light green
        'Tillering': '#FFD700',   # Gold
        'Growth': '#228B22',      # Forest green
        'Ripening': '#FF8C00'     # Dark orange
    }
    
    fig, axes = plt.subplots(len(plot_ids), 1, figsize=(14, 6*len(plot_ids)), sharex=False)
    if len(plot_ids) == 1:
        axes = [axes]
    
    fig.suptitle('Phenology Classification Comparison', fontsize=16, fontweight='bold')
    
    for idx, pid in enumerate(plot_ids):
        ax = axes[idx]
        plot_data = df[df['plot_id'] == pid].copy()
        
        if plot_data.empty:
            ax.text(0.5, 0.5, f'No data for Plot {pid}', 
                   ha='center', va='center', transform=ax.transAxes)
            continue
        
        # Ensure date is datetime
        if not np.issubdtype(plot_data['date'].dtype, np.datetime64):
            try:
                plot_data['date'] = pd.to_datetime(plot_data['date'], errors='coerce', format='mixed')
            except TypeError:
                plot_data['date'] = pd.to_datetime(plot_data['date'], errors='coerce')
        plot_data = plot_data.sort_values('date').reset_index(drop=True)
        
        # Plot stage code
        if 'stage4_code' in plot_data.columns:
            ax.plot(plot_data['date'], plot_data['stage4_code'], 'ko-', 
                   linewidth=2.5, markersize=8, label='Stage Code')
        
        # Add colored background regions
        if 'stage_4' in plot_data.columns:
            current_stage = None
            start_idx = 0
            
            for i in range(len(plot_data)):
                stage = plot_data.iloc[i]['stage_4']
                
                if stage != current_stage:
                    if current_stage is not None and start_idx < i:
                        color = stage_colors.get(current_stage, '#CCCCCC')
                        ax.axvspan(plot_data.iloc[start_idx]['date'], 
                                  plot_data.iloc[i]['date'],
                                  alpha=0.3, color=color, zorder=0)
                    current_stage = stage
                    start_idx = i
            
            # Fill the last region
            if current_stage is not None and start_idx < len(plot_data):
                color = stage_colors.get(current_stage, '#CCCCCC')
                ax.axvspan(plot_data.iloc[start_idx]['date'], 
                          plot_data.iloc[-1]['date'],
                          alpha=0.3, color=color, zorder=0)
        
        # Detect transition dates for x-axis
        transition_dates = []
        if 'stage_4' in plot_data.columns and len(plot_data) > 0:
            transition_dates.append(plot_data.iloc[0]['date'])
            for i in range(1, len(plot_data)):
                if plot_data.iloc[i]['stage_4'] != plot_data.iloc[i-1]['stage_4']:
                    transition_dates.append(plot_data.iloc[i]['date'])
            if plot_data.iloc[-1]['date'] not in transition_dates:
                transition_dates.append(plot_data.iloc[-1]['date'])
        
        # Format plot
        ax.set_title(f'Plot {pid} - Phenology Classification', fontsize=13, fontweight='bold')
        ax.set_ylabel('Stage Code', fontsize=11)
        ax.set_yticks([0, 1, 2, 3, 4])
        ax.set_yticklabels(['Bare\n(0)', 'Seedling\n(1)', 'Tillering\n(2)', 'Growth\n(3)', 'Ripening\n(4)'])
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('Date', fontsize=11)
        
        if transition_dates:
            ax.set_xticks(transition_dates)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.tick_params(axis='x', rotation=45, labelsize=9)
    
    # Create legend
    from matplotlib.patches import Patch
    stage_patches = [Patch(facecolor=stage_colors[stage], alpha=0.5, label=stage) 
                     for stage in ['Bare', 'Seedling', 'Tillering', 'Growth', 'Ripening']]
    fig.legend(handles=stage_patches, loc='upper right', fontsize=10, 
               title='Phenology Stages', framealpha=0.9)
    
    plt.tight_layout()
    fname = os.path.join(outdir, f"classification_comparison_{'_'.join(map(str, plot_ids))}.png")
    fig.savefig(fname, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {fname}")


def plot_classification_map(df: pd.DataFrame, target_date: str, max_plots: int = 30, outdir: str = "figures"):
    """
    Create an INTERACTIVE MAP visualization showing phenology classification for first N plots on a specific date.
    Uses folium to create a real geographical map with satellite imagery.
    
    Args:
        df: DataFrame with plot_id, date, stage4_code columns
        target_date: Date string in format 'YYYY-MM-DD'
        max_plots: Maximum number of plots to display (default 30)
        outdir: Output directory for the HTML map file
    """
    import folium
    from folium import plugins
    
    # Load plot coordinates
    try:
        coords_df = pd.read_csv("figures/plots - Sheet1.csv")
    except FileNotFoundError:
        print("Warning: Plot coordinates file not found. Cannot create map.")
        return
    
    # Parse coordinates and get unique plots
    def parse_coord(coord_str):
        """Parse 'lon,lat' string into (lon, lat) tuple"""
        try:
            parts = coord_str.strip().split(',')
            return float(parts[0]), float(parts[1])
        except:
            return None, None
    
    # Calculate centroid from all 4 coordinates for each plot
    def calculate_centroid(row):
        """Calculate the centroid (center) of the field from all 4 corner coordinates"""
        lons = []
        lats = []
        for col in ['coordinate1', 'coordinate2', 'coordinate3', 'coordinate4']:
            if col in row and pd.notna(row[col]):
                lon, lat = parse_coord(row[col])
                if lon is not None and lat is not None:
                    lons.append(lon)
                    lats.append(lat)
        
        if lons and lats:
            return pd.Series({'lon': sum(lons) / len(lons), 'lat': sum(lats) / len(lats)})
        else:
            return pd.Series({'lon': None, 'lat': None})
    
    # Get unique plots and calculate centroids
    plot_coords = coords_df.groupby('plot_id').first().reset_index()
    plot_coords[['lon', 'lat']] = plot_coords.apply(calculate_centroid, axis=1)
    
    # Filter to first max_plots
    plot_coords = plot_coords[plot_coords['plot_id'] <= max_plots].copy()
    
    # Filter data to target date and merge with coordinates
    target_df = df[df['date'] == target_date].copy()
    
    # Get one observation per plot (take first if multiple)
    target_df = target_df.groupby('plot_id').first().reset_index()
    
    # Merge with coordinates
    map_data = plot_coords.merge(target_df[['plot_id', 'stage4_code', 'stage_4', 'NDVI', 'SAVI', 'NDWI']], 
                                   on='plot_id', how='left')
    
    # Remove plots without data
    map_data = map_data.dropna(subset=['stage4_code'])
    
    # Define phenology stage colors (matching other visualizations)
    stage_colors = {
        0: '#D3D3D3',      # Bare - light gray
        1: '#90EE90',      # Seedling - light green
        2: '#FFD700',      # Tillering - gold
        3: '#228B22',      # Growth - forest green
        4: '#FF8C00'       # Ripening - dark orange
    }
    
    stage_names = {
        0: 'Bare',
        1: 'Seedling',
        2: 'Tillering',
        3: 'Growth',
        4: 'Ripening'
    }
    
    # Calculate center of all plots for map initialization
    center_lat = map_data['lat'].mean()
    center_lon = map_data['lon'].mean()
    
    # Create folium map with satellite imagery
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=15,
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri World Imagery'
    )
    
    # Add alternative tile layers
    folium.TileLayer('OpenStreetMap', name='Street Map').add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite',
        overlay=False,
        control=True
    ).add_to(m)
    
    # Add markers for each plot
    for _, row in map_data.iterrows():
        stage = int(row['stage4_code'])
        color = stage_colors.get(stage, '#808080')
        stage_name = stage_names.get(stage, 'Unknown')
        
        # Create popup with detailed information
        popup_html = f"""
        <div style="font-family: Arial; min-width: 200px;">
            <h4 style="margin: 5px 0; color: #333;">Plot #{int(row['plot_id'])}</h4>
            <hr style="margin: 5px 0;">
            <b>Date:</b> {target_date}<br>
            <b>Phenology Stage:</b> <span style="color: {color}; font-weight: bold;">{stage_name}</span> (Stage {stage})<br>
            <hr style="margin: 5px 0;">
            <b>Vegetation Indices:</b><br>
            • NDVI: {row['NDVI']:.4f}<br>
            • SAVI: {row['SAVI']:.4f}<br>
            • NDWI: {row['NDWI']:.4f}<br>
            <hr style="margin: 5px 0;">
            <small>Lat: {row['lat']:.6f}, Lon: {row['lon']:.6f}</small>
        </div>
        """
        
        # Create circle marker with custom styling
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=12,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"Plot {int(row['plot_id'])}: {stage_name}",
            color='black',
            weight=2,
            fill=True,
            fillColor=color,
            fillOpacity=0.8
        ).add_to(m)
        
        # Add plot number as a label
        folium.Marker(
            location=[row['lat'], row['lon']],
            icon=folium.DivIcon(
                html=f'''<div style="
                    font-size: 10px; 
                    font-weight: bold; 
                    color: black;
                    text-align: center;
                    text-shadow: 1px 1px 2px white, -1px -1px 2px white;
                    ">{int(row['plot_id'])}</div>'''
            )
        ).add_to(m)
    
    # Add custom legend
    legend_html = f'''
    <div style="position: fixed; 
                top: 10px; right: 10px; width: 220px; 
                background-color: white; 
                border:2px solid grey; z-index:9999; 
                font-size:14px;
                padding: 10px;
                border-radius: 5px;
                box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
        <h4 style="margin-top:0; margin-bottom:10px; text-align:center;">Phenology Stages</h4>
        <p style="margin: 5px 0;"><span style="background-color: {stage_colors[0]}; border: 1px solid black; padding: 3px 8px; border-radius: 3px;">⬤</span> 0: Bare</p>
        <p style="margin: 5px 0;"><span style="background-color: {stage_colors[1]}; border: 1px solid black; padding: 3px 8px; border-radius: 3px;">⬤</span> 1: Seedling</p>
        <p style="margin: 5px 0;"><span style="background-color: {stage_colors[2]}; border: 1px solid black; padding: 3px 8px; border-radius: 3px;">⬤</span> 2: Tillering</p>
        <p style="margin: 5px 0;"><span style="background-color: {stage_colors[3]}; border: 1px solid black; padding: 3px 8px; border-radius: 3px;">⬤</span> 3: Growth</p>
        <p style="margin: 5px 0;"><span style="background-color: {stage_colors[4]}; border: 1px solid black; padding: 3px 8px; border-radius: 3px;">⬤</span> 4: Ripening</p>
        <hr style="margin: 10px 0;">
        <p style="margin: 5px 0; font-size: 12px; text-align: center;"><b>Date:</b> {target_date}</p>
        <p style="margin: 5px 0; font-size: 12px; text-align: center;"><b>Plots:</b> {len(map_data)}</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Add fullscreen button
    plugins.Fullscreen(
        position='topleft',
        title='Enter fullscreen mode',
        title_cancel='Exit fullscreen mode',
        force_separate_button=True
    ).add_to(m)
    
    # Add measure control for distance measurements
    plugins.MeasureControl(position='bottomleft', primary_length_unit='meters').add_to(m)
    
    # Save map as HTML
    os.makedirs(outdir, exist_ok=True)
    fname = os.path.join(outdir, f"classification_map_{target_date.replace('-', '')}.html")
    m.save(fname)
    
    print(f"Saved: {fname}")
    print(f"  Interactive map with {len(map_data)} plots")
    print(f"  Open the HTML file in a web browser to view the map")
    print(f"  Plotted {len(map_data)} plots with classification data")


if __name__ == "__main__":
    df = main()  # Capture the returned DataFrame

    # Only visualize plots 1 and 2 (Green and Blue fields)
    plot_ids_to_viz = [1, 2]
    print("\nGenerating visualizations for plots 1 and 2 (Green and Blue fields)")
    
    # Generate map visualization for first 30 plots on specific date
    print("\nGenerating map visualization for ALL plots on 2025-01-26...")
    plot_classification_map(df, target_date="2025-01-26", max_plots=999, outdir="figures")
    
    # Generate slope plots
    try:
        plot_slopes_for_plots(df, plot_ids=tuple(plot_ids_to_viz), outdir="figures")
    except NameError:
        # If df is not in scope (e.g., you moved code), load from CSV:
        df = pd.read_csv("plot_data_with_slopes.csv")
        try:
            df['date'] = pd.to_datetime(df['date'], errors='coerce', format='mixed')
        except TypeError:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        plot_slopes_for_plots(df, plot_ids=tuple(plot_ids_to_viz), outdir="figures")
    
    # Generate phenology classification visualizations
    print(f"\nGenerating phenology classification visualizations for plots: {plot_ids_to_viz}...")
    for plot_id in plot_ids_to_viz:
        visualize_phenology_classification(df, plot_id=plot_id, outdir="figures")
    
    # Generate comparison plots
    print(f"\nGenerating comparison plots for plots: {plot_ids_to_viz}...")
    plot_comparison_charts(df, plot_ids=tuple(plot_ids_to_viz), outdir="figures")
    
    # Generate classification comparison plot
    print(f"\nGenerating classification comparison plot for plots: {plot_ids_to_viz}...")
    plot_classification_comparison(df, plot_ids=tuple(plot_ids_to_viz), outdir="figures")
