import pandas as pd
import folium
from folium import plugins

# Load plot coordinates
coords_df = pd.read_csv("figures/plots - Sheet1.csv")

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

# Remove any plots without valid coordinates
plot_coords = plot_coords.dropna(subset=['lon', 'lat'])

print(f"Found {len(plot_coords)} plots with valid coordinates")

# Calculate center of all plots for map initialization
center_lat = plot_coords['lat'].mean()
center_lon = plot_coords['lon'].mean()

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

# Add markers for each plot (simple blue markers)
for _, row in plot_coords.iterrows():
    # Create popup with plot information
    popup_html = f"""
    <div style="font-family: Arial; min-width: 150px;">
        <h4 style="margin: 5px 0; color: #333;">Plot #{int(row['plot_id'])}</h4>
        <hr style="margin: 5px 0;">
        <small>Lat: {row['lat']:.6f}<br>Lon: {row['lon']:.6f}</small>
    </div>
    """
    
    # Create circle marker
    folium.CircleMarker(
        location=[row['lat'], row['lon']],
        radius=10,
        popup=folium.Popup(popup_html, max_width=250),
        tooltip=f"Plot {int(row['plot_id'])}",
        color='blue',
        weight=2,
        fill=True,
        fillColor='lightblue',
        fillOpacity=0.7
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

# Add title
title_html = '''
<div style="position: fixed; 
            top: 10px; left: 50px; width: 300px; 
            background-color: white; 
            border:2px solid grey; z-index:9999; 
            font-size:16px;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
    <h3 style="margin:0; text-align:center;">Field Locations Map</h3>
    <p style="margin: 5px 0; font-size: 12px; text-align: center;">Total Plots: ''' + str(len(plot_coords)) + '''</p>
</div>
'''
m.get_root().html.add_child(folium.Element(title_html))

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
output_file = "field_locations_map.html"
m.save(output_file)

print(f"\n✅ Map created successfully!")
print(f"Saved: {output_file}")
print(f"Total plots mapped: {len(plot_coords)}")
print(f"\nOpen '{output_file}' in your web browser to view the map")
