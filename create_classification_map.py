import pandas as pd
import folium
from folium import plugins

# Configuration
TARGET_DATE = "2025-01-26"  # Date to show classifications for
OUTPUT_FILE = "phenology_map_with_classifications.html"

print(f"Creating phenology classification map for {TARGET_DATE}...")

# Load plot coordinates
try:
    coords_df = pd.read_csv("figures/plots - Sheet1.csv")
    print(f"Loaded coordinates for {coords_df['plot_id'].nunique()} plots")
except FileNotFoundError:
    print("Error: 'figures/plots - Sheet1.csv' not found!")
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

# Parse coordinates
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
plot_coords = plot_coords.dropna(subset=['lon', 'lat'])

print(f"Calculated centroids for {len(plot_coords)} plots")

# Filter data to target date
target_df = data_df[data_df['date'] == TARGET_DATE].copy()

if target_df.empty:
    print(f"Warning: No data found for date {TARGET_DATE}")
    print("Available dates:", data_df['date'].dt.date.unique()[:10])
    exit(1)

# Get one observation per plot (take first if multiple)
target_df = target_df.groupby('plot_id').first().reset_index()

# Merge coordinates with classification data
map_data = plot_coords.merge(
    target_df[['plot_id', 'stage4_code', 'stage_4', 'NDVI', 'SAVI', 'NDWI']], 
    on='plot_id', 
    how='left'
)

# Remove plots without classification data
map_data = map_data.dropna(subset=['stage4_code'])

print(f"Plots with classification data on {TARGET_DATE}: {len(map_data)}")

# Define phenology stage colors
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
    <p style="margin: 5px 0; font-size: 12px; text-align: center;"><b>Date:</b> {TARGET_DATE}</p>
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
m.save(OUTPUT_FILE)

print(f"\n✅ Classification map created successfully!")
print(f"Saved: {OUTPUT_FILE}")
print(f"Date: {TARGET_DATE}")
print(f"Plots mapped: {len(map_data)}")
print(f"\nClassification breakdown:")
for stage_code in sorted(stage_names.keys()):
    count = len(map_data[map_data['stage4_code'] == stage_code])
    if count > 0:
        print(f"  {stage_names[stage_code]}: {count} plots")

print(f"\nOpen '{OUTPUT_FILE}' in your web browser to view the map")
