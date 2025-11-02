import pandas as pd
import folium
from folium import plugins

# Configuration
TARGET_DATES = [
    "2024-12-27",
    "2025-01-11", "2025-01-19", "2025-01-26", "2025-01-29", "2025-01-31",
    "2025-02-03", "2025-02-08", "2025-02-10", "2025-02-13", "2025-02-15", "2025-02-18", "2025-02-23",
    "2025-03-02", "2025-03-05", "2025-03-07", "2025-03-10", "2025-03-12", "2025-03-15",
    "2025-03-22", "2025-03-25", "2025-03-27", "2025-03-29", "2025-03-30",
    "2025-04-01", "2025-04-06", "2025-04-09", "2025-04-11"
]
COORDINATES_FILE = "figures/new-coordinates.xlsx"
OUTPUT_DIR = "phenology_maps"

import os
os.makedirs(OUTPUT_DIR, exist_ok=True)

print(f"Creating phenology classification maps for {len(TARGET_DATES)} dates...")
print(f"Using coordinates from: {COORDINATES_FILE}")

# Load new coordinates from Excel
try:
    coords_df = pd.read_excel(COORDINATES_FILE)
    print(f"Loaded Excel file with shape: {coords_df.shape}")
    
    # The Excel file has 4 columns, each containing "lat, lon" pairs
    # Let's rename them for clarity
    coords_df.columns = ['coordinate1', 'coordinate2', 'coordinate3', 'coordinate4']
    
    # Add plot_id as row number (starting from 1)
    coords_df['plot_id'] = range(1, len(coords_df) + 1)
    
    print(f"Loaded coordinates for {len(coords_df)} plots")
except FileNotFoundError:
    print(f"Error: '{COORDINATES_FILE}' not found!")
    exit(1)

# Load plot data with classifications
try:
    data_df = pd.read_csv("plot_data_with_slopes.csv")
    # Convert date to datetime
    data_df['date'] = pd.to_datetime(data_df['date'])
    print(f"Loaded classification data: {len(data_df)} rows")
except FileNotFoundError:
    print("Error: 'plot_data_with_slopes.csv' not found!")
    print("Please run laddu.py first to generate the classification data.")
    exit(1)

# Parse coordinates - note: format is "lat, lon" (reversed from typical lon,lat)
def parse_coord(coord_str):
    """Parse 'lat, lon' string into (lon, lat) tuple - note the order swap!"""
    try:
        parts = str(coord_str).strip().split(',')
        lat = float(parts[0].strip())
        lon = float(parts[1].strip())
        return lon, lat  # Return as (lon, lat) for consistency
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

# Calculate centroids
coords_df[['lon', 'lat']] = coords_df.apply(calculate_centroid, axis=1)
coords_df = coords_df.dropna(subset=['lon', 'lat'])

print(f"Calculated centroids for {len(coords_df)} plots")
print(f"Coordinate range: Lat {coords_df['lat'].min():.6f} to {coords_df['lat'].max():.6f}")
print(f"                  Lon {coords_df['lon'].min():.6f} to {coords_df['lon'].max():.6f}")

# Define phenology stage colors (used in all maps)
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

# Loop through all target dates
print(f"\n{'='*60}")
print(f"Generating maps for {len(TARGET_DATES)} dates")
print(f"{'='*60}\n")

for date_idx, TARGET_DATE in enumerate(TARGET_DATES, 1):
    print(f"\n[{date_idx}/{len(TARGET_DATES)}] Processing date: {TARGET_DATE}")
    
    # Filter data to target date
    target_df = data_df[data_df['date'] == TARGET_DATE].copy()

    if target_df.empty:
        print(f"  ⚠ Warning: No data found for date {TARGET_DATE}, skipping...")
        continue
    
    # Get one observation per plot (take first if multiple)
    target_df = target_df.groupby('plot_id').first().reset_index()
    
    # Merge coordinates with classification data
    map_data = coords_df.merge(
        target_df[['plot_id', 'stage4_code', 'stage_4', 'NDVI', 'SAVI', 'NDWI']], 
        on='plot_id', 
        how='left'
    )
    
    # Separate plots with and without classification data
    plots_with_data = map_data.dropna(subset=['stage4_code'])
    plots_without_data = map_data[map_data['stage4_code'].isna()]
    
    print(f"  Plots with data: {len(plots_with_data)}, without data: {len(plots_without_data)}")
    
    # Calculate center of all plots for map initialization
    all_plots = pd.concat([plots_with_data, plots_without_data])
    center_lat = all_plots['lat'].mean()
    center_lon = all_plots['lon'].mean()
    
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
    
    # Add markers for plots WITH classification data
    for _, row in plots_with_data.iterrows():
        stage = int(row['stage4_code'])
        color = stage_colors.get(stage, '#808080')
        stage_name = stage_names.get(stage, 'Unknown')
        
        # Create popup with detailed information
        popup_html = f"""
        <div style="font-family: Arial; min-width: 200px;">
            <h4 style="margin: 5px 0; color: #333;">Plot #{int(row['plot_id'])}</h4>
            <hr style="margin: 5px 0;">
            <b>Date:</b> {TARGET_DATE}<br>
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
        
        # Create circle marker with phenology color
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
    
    # Add markers for plots WITHOUT classification data (gray markers)
    for _, row in plots_without_data.iterrows():
        popup_html = f"""
        <div style="font-family: Arial; min-width: 200px;">
            <h4 style="margin: 5px 0; color: #333;">Plot #{int(row['plot_id'])}</h4>
            <hr style="margin: 5px 0;">
            <b>Status:</b> <span style="color: red;">No classification data</span><br>
            <hr style="margin: 5px 0;">
            <small>Lat: {row['lat']:.6f}, Lon: {row['lon']:.6f}</small>
        </div>
        """
        
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=10,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"Plot {int(row['plot_id'])}: No data",
            color='gray',
            weight=2,
            fill=True,
            fillColor='lightgray',
            fillOpacity=0.5
        ).add_to(m)
        
        folium.Marker(
            location=[row['lat'], row['lon']],
            icon=folium.DivIcon(
                html=f'''<div style="
                    font-size: 10px; 
                    font-weight: bold; 
                    color: gray;
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
        <p style="margin: 5px 0;"><span style="background-color: lightgray; border: 1px solid gray; padding: 3px 8px; border-radius: 3px;">⬤</span> No data</p>
        <hr style="margin: 10px 0;">
        <p style="margin: 5px 0; font-size: 12px; text-align: center;"><b>Date:</b> {TARGET_DATE}</p>
        <p style="margin: 5px 0; font-size: 12px; text-align: center;"><b>With data:</b> {len(plots_with_data)}/{len(all_plots)}</p>
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
    OUTPUT_FILE = f"{OUTPUT_DIR}/map_{TARGET_DATE.replace('-', '_')}.html"
    m.save(OUTPUT_FILE)
    
    print(f"  ✅ Map saved: {OUTPUT_FILE}")
    if len(plots_with_data) > 0:
        stage_breakdown = plots_with_data['stage4_code'].value_counts().sort_index()
        breakdown_str = ", ".join([f"{stage_names[int(k)]}: {v}" for k, v in stage_breakdown.items()])
        print(f"     {breakdown_str}")

# Final summary
print(f"\n{'='*60}")
print(f"✅ All maps generated successfully!")
print(f"Total maps created: {len(TARGET_DATES)}")
print(f"Output directory: {OUTPUT_DIR}")
print(f"{'='*60}")
