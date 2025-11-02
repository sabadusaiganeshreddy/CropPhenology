# Research Summary: Crop Phenology Classification Using Multi-Temporal Satellite Data

## Overview
This research developed an automated methodology for classifying crop phenology stages using multi-temporal satellite-derived vegetation indices. The study analyzed 53 agricultural plots over a complete crop cycle from December 2024 to April 2025.

---

## 1. DATA AND STUDY AREA

### 1.1 Input Data
- **Dataset**: Multi-temporal satellite imagery (28 observation dates)
- **Study Period**: December 27, 2024 to April 11, 2025 (106 days)
- **Number of Plots**: 53 agricultural fields (24 plots used for detailed spatial analysis)
- **Geographic Location**: Bihar region, India (Lat: 25.57-25.58°N, Lon: 84.82-84.83°E)
- **Input File**: `classified_data_input.csv` (3,074 observations)

### 1.2 Vegetation Indices Used
Three key vegetation indices were extracted from satellite imagery:

1. **NDVI (Normalized Difference Vegetation Index)**
   - Range: -1 to +1
   - Measures vegetation greenness and health
   - Formula: (NIR - Red) / (NIR + Red)

2. **SAVI (Soil-Adjusted Vegetation Index)**
   - Reduces soil background effects
   - More accurate in sparse vegetation conditions
   - Formula: ((NIR - Red) / (NIR + Red + L)) × (1 + L), where L = 0.5

3. **NDWI (Normalized Difference Water Index)**
   - Measures vegetation water content
   - Indicator of plant moisture stress
   - Formula: (NIR - SWIR) / (NIR + SWIR)

### 1.3 Spatial Data
- **Coordinate Data**: `figures/new-coordinates.xlsx` (24 plots with 4 corner coordinates each)
- **Coordinate Format**: Latitude, Longitude pairs for field boundaries
- **Centroid Calculation**: Field centers computed as average of 4 corner coordinates

---

## 2. METHODOLOGY

### 2.1 Data Preprocessing
1. **Data Loading and Validation**
   - Automatic detection of input CSV file with required columns
   - Quality checks for data completeness and validity

2. **Data Cleaning**
   - Removal of rows with missing values
   - Conversion of dates to datetime format
   - Sorting by plot_id and date for temporal analysis

3. **Outlier Detection and Filtering**
   - Statistical outlier detection using Z-score method (threshold: ±3 standard deviations)
   - Applied independently to NDVI, SAVI, and NDWI

### 2.2 Temporal Slope Calculation

**Method: 16-Day Moving Window with Median Slope**

For each observation date and each vegetation index:

1. **Temporal Window**: ±8 days around the target date (16-day total window)
2. **Pairwise Slope Calculation**: 
   - For all observation pairs (i, j) within the window:
   - Slope = (Value_j - Value_i) / (Date_j - Date_i)
   - Time difference in days
3. **Robust Estimation**: Median of all pairwise slopes used (highly robust to noise)
4. **Output**: Daily rate of change (Δ Index / day)

**Calculated Slopes:**
- `NDVI_slope`: Rate of change in NDVI
- `SAVI_slope`: Rate of change in SAVI
- `NDWI_slope`: Rate of change in NDWI

**Advantages of This Method:**
- Very smooth and stable slope estimates
- Robust to missing data and noise
- Captures gradual phenological transitions
- Avoids overfitting to individual observations

### 2.3 Composite Growth Index (G)

**Formula**: G = 0.6 × NDVI + 0.4 × SAVI

**Rationale**:
- Combines strengths of both NDVI and SAVI
- NDVI weighted higher (60%) for vegetation vigor
- SAVI (40%) accounts for soil background effects
- Provides more stable phenology indicator

**Slope of Composite Index**:
- sG = 0.5 × (NDVI_slope + SAVI_slope)
- Represents overall vegetation growth rate

### 2.4 Temporal Smoothing

**Savitzky-Golay Filter Applied to G**:
- Window length: 7 observations
- Polynomial order: 2
- Purpose: Remove high-frequency noise while preserving phenological trends
- Output: `G_sm` (smoothed composite growth index)

### 2.5 Phenology Classification Algorithm

**Five-Stage Classification System:**

| Stage Code | Stage Name | Description |
|------------|-----------|-------------|
| 0 | Bare | Bare soil or minimal vegetation |
| 1 | Seedling | Early germination and emergence |
| 2 | Tillering | Vegetative growth, canopy development |
| 3 | Growth | Active vegetative growth, peak biomass |
| 4 | Ripening | Senescence, grain filling, maturation |

**Classification Logic (Rule-Based Decision Tree):**

```
For each observation (plot, date):

1. Calculate: delta_G = G_smoothed - previous_G_smoothed

2. Apply Classification Rules:
   
   IF NDVI < 0.15:
       → Stage 0 (Bare)
   
   ELSE IF NDVI < 0.35 AND sG > 0:
       → Stage 1 (Seedling)
   
   ELSE IF NDVI >= 0.35:
       IF sG > 0.001 OR delta_G > 0.002:
           → Stage 3 (Growth)
       
       ELSE IF sG < -0.001 OR delta_G < -0.002:
           → Stage 4 (Ripening)
       
       ELSE IF previous_stage == 1:
           → Stage 2 (Tillering)
       
       ELSE:
           → Maintain previous stage
   
   ELSE:
       → Stage 2 (Tillering) as default

3. Apply Temporal Consistency Constraints:
   - Prevent rapid stage reversals
   - Allow logical transitions only
   - Smooth stage progressions
```

**Key Thresholds:**
- NDVI < 0.15: Bare soil threshold
- NDVI < 0.35: Early vegetation threshold
- sG > 0.001: Active growth threshold
- sG < -0.001: Senescence threshold
- delta_G thresholds: Detect rapid changes in vegetation

### 2.6 Phenology Transition Detection

**Method**: Identify dates where phenology stage changes from one observation to the next

**Output**: `phenology_stage4_transitions.csv`
- Contains only transition dates for each plot
- Format: plot_id, date, from_stage, to_stage, stage_name
- Used for tracking key phenological events

---

## 3. RESULTS AND OUTPUTS

### 3.1 Processed Data Files

**Primary Output:**
- **`plot_data_with_slopes.csv`** (3,074 rows × multiple columns)
  - All original data plus calculated features
  - Columns: plot_id, date, NDVI, SAVI, NDWI, NDVI_slope, SAVI_slope, NDWI_slope, G, G_sm, sG, stage4_code, stage_4
  - Date range: 2024-12-27 to 2025-04-11
  - 53 plots × 28 dates (average)

**Transition Data:**
- **`phenology_stage4_transitions.csv`**
  - Summary of phenological stage changes
  - Key dates for each plot's development

### 3.2 Visualization Outputs

#### 3.2.1 Individual Plot Analysis (Plots 1 & 2)

**A. Phenology Classification Time Series**
- Files: `figures/plot_1_phenology_classification.png`, `figures/plot_2_phenology_classification.png`
- **Content**: 3-panel visualization:
  1. **Panel 1**: NDVI, SAVI, NDWI temporal profiles
  2. **Panel 2**: Composite growth index (G) and smoothed G
  3. **Panel 3**: Classified phenology stages over time
- **X-axis**: Dates marked at phenology transition points
- **Color-coded stages**: Visual differentiation of 5 phenology stages

**B. Slope Analysis Plots (6 plots total)**
- Files: 
  - `figures/plot_1_ndvi_slope.png`, `figures/plot_1_savi_slope.png`, `figures/plot_1_ndwi_slope.png`
  - `figures/plot_2_ndvi_slope.png`, `figures/plot_2_savi_slope.png`, `figures/plot_2_ndwi_slope.png`
- **Content**: Temporal rate of change (Δ Index / day)
- **X-axis**: 10-day interval ticks for consistent temporal reference
- **Zero-line**: Horizontal reference line to identify growth vs. senescence periods
- **Interpretation**: 
  - Positive slopes: Vegetation increase (Growth stage)
  - Negative slopes: Vegetation decrease (Ripening/Senescence)
  - Near-zero slopes: Stable periods (Bare, Tillering)

#### 3.2.2 Comparative Analysis (Plots 1 & 2)

**A. Side-by-Side Comparison**
- File: `figures/comparison_plots_1_2.png`
- **Content**: Multi-panel comparison of both plots
- **Panels**: NDVI, SAVI, NDWI time series for each plot
- **Purpose**: Visual comparison of phenological patterns between plots

**B. Timeline Comparison**
- File: `figures/timeline_comparison_1_2.png`
- **Content**: Overlay of all three indices for both plots
- **Purpose**: Identify synchrony or differences in phenological development

**C. Classification Comparison**
- File: `figures/classification_comparison_1_2.png`
- **Content**: Phenology stage progressions for both plots side-by-side
- **Purpose**: Compare crop development timing between fields

#### 3.2.3 Spatial Visualization

**A. Interactive Web Maps (28 maps total)**

**Static Map (Legacy):**
- File: `figures/classification_map_20250126.html` and `.png`
- Single date snapshot (January 26, 2025)
- 53 plots with phenology classifications

**Temporal Map Series:**
- Directory: `phenology_maps/`
- Files: `map_2024_12_27.html` through `map_2025_04_11.html` (28 files)
- **Technology**: Folium library with Leaflet.js
- **Base Layers**:
  - Esri World Imagery (satellite view)
  - OpenStreetMap (street map view)
  - Layer switcher control

**Map Features:**
- **Circle Markers**: Color-coded by phenology stage
  - Bare: Light gray (#D3D3D3)
  - Seedling: Light green (#90EE90)
  - Tillering: Gold (#FFD700)
  - Growth: Forest green (#228B22)
  - Ripening: Dark orange (#FF8C00)

- **Interactive Popups**: Click markers to view:
  - Plot ID
  - Date
  - Phenology stage
  - NDVI, SAVI, NDWI values
  - GPS coordinates

- **Plot Labels**: Numerical labels overlaid on each field

- **Dynamic Legend**:
  - Stage color key
  - Date display
  - Plot count statistics

- **Tools**:
  - Fullscreen mode
  - Distance measurement tool
  - Zoom/pan controls

**Coordinate Coverage:**
- 24 plots with precise GPS coordinates
- Field centroids calculated from 4-corner boundaries
- Coordinate range: Lat 25.57-25.58°N, Lon 84.82-84.83°E

**Temporal Coverage:**
Available dates (28 maps):
```
2024-12-27          2025-02-15          2025-03-12
2025-01-11          2025-02-18          2025-03-15
2025-01-19          2025-02-23          2025-03-22
2025-01-26          2025-03-02          2025-03-25
2025-01-29          2025-03-05          2025-03-27
2025-01-31          2025-03-07          2025-03-29
2025-02-03          2025-03-10          2025-03-30
2025-02-08                              2025-04-01
2025-02-10                              2025-04-06
2025-02-13                              2025-04-09
                                        2025-04-11
```

---

## 4. KEY FINDINGS

### 4.1 Phenological Progression Patterns

**Typical Crop Cycle Observed:**
1. **Bare Stage** (Late December): 18/24 plots (~75%)
2. **Seedling Stage** (Early-Mid January): Emergence phase
3. **Tillering Stage** (Mid-Late January): Vegetative development
4. **Growth Stage** (February-Early March): Peak biomass accumulation
5. **Ripening Stage** (Mid March onwards): 100% of plots by March 22

**Temporal Variability:**
- Some plots showed more rapid development (early transition to Growth)
- A few plots exhibited delayed germination (extended Bare period)
- Majority of plots followed synchronized phenological progression

### 4.2 Vegetation Index Dynamics

**NDVI Patterns:**
- Bare stage: NDVI < 0.15
- Active growth: NDVI peaked at 0.6-0.8
- Ripening: Gradual NDVI decline

**SAVI Patterns:**
- More stable than NDVI during early stages
- Reduced soil background effects visible

**NDWI Patterns:**
- Tracked plant water status
- Decline during ripening indicated moisture stress

### 4.3 Slope Analysis Insights

**Growth Phase (Positive Slopes):**
- Strongest slopes during Seedling → Tillering → Growth transitions
- Peak growth rates: +0.01 to +0.02 NDVI units/day

**Senescence Phase (Negative Slopes):**
- Gradual negative slopes during Growth → Ripening
- Senescence rates: -0.005 to -0.015 NDVI units/day

**Stable Phases (Near-Zero Slopes):**
- Bare stage: Minimal vegetation change
- Late ripening: Stable senesced vegetation

---

## 5. TECHNICAL SPECIFICATIONS

### 5.1 Software and Libraries

**Programming Language:** Python 3.x

**Core Libraries:**
- `pandas`: Data manipulation and analysis
- `numpy`: Numerical computations
- `matplotlib`: Static visualizations
- `scipy`: Signal processing (Savitzky-Golay filter)
- `folium`: Interactive web mapping
- `openpyxl`: Excel file handling

### 5.2 Processing Pipeline

```
Input Data (CSV)
    ↓
Data Cleaning & Validation
    ↓
Outlier Detection & Removal
    ↓
Temporal Slope Calculation (16-day window)
    ↓
Composite Index Calculation (G)
    ↓
Temporal Smoothing (Savitzky-Golay)
    ↓
Phenology Classification (Rule-based)
    ↓
Transition Detection
    ↓
Outputs: Data Files + Visualizations + Maps
```

### 5.3 Key Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Slope window | 16 days (±8 days) | Temporal smoothing for slope |
| Savitzky-Golay window | 7 observations | Noise reduction |
| Savitzky-Golay polynomial | 2nd order | Preserve trends |
| NDVI bare threshold | 0.15 | Bare soil detection |
| NDVI vegetation threshold | 0.35 | Established vegetation |
| Growth slope threshold | +0.001 /day | Active growth detection |
| Senescence slope threshold | -0.001 /day | Ripening detection |
| Map update frequency | 28 dates | ~3-4 day intervals |
| Spatial resolution | Plot-level | Field-scale analysis |

---

## 6. ADVANTAGES OF THIS METHODOLOGY

### 6.1 Robustness
- **Median-based slope calculation**: Resistant to outliers and missing data
- **Multi-index approach**: Reduces dependence on single indicator
- **Temporal smoothing**: Eliminates sensor noise and atmospheric effects
- **Rule-based classification**: Transparent and interpretable decisions

### 6.2 Automation
- **Fully automated pipeline**: Minimal manual intervention required
- **Scalable**: Can process any number of plots and dates
- **Reproducible**: Consistent results with same input data

### 6.3 Visualization
- **Multi-scale outputs**: From individual plots to entire study area
- **Interactive maps**: User-friendly exploration of spatio-temporal patterns
- **Publication-ready figures**: High-resolution static images for reports/papers

### 6.4 Temporal Resolution
- **28 observation dates**: High temporal density captures phenological transitions
- **~3-4 day intervals**: Sufficient to detect rapid changes
- **Complete crop cycle coverage**: From bare soil to harvest

---

## 7. POTENTIAL APPLICATIONS

1. **Precision Agriculture**
   - Field-specific management decisions
   - Optimization of irrigation and fertilization timing
   - Early detection of crop stress or anomalies

2. **Crop Monitoring**
   - Regional phenology assessment
   - Yield prediction models
   - Crop insurance verification

3. **Climate Impact Studies**
   - Phenological shift detection due to climate change
   - Inter-annual variability analysis
   - Growing season length trends

4. **Agricultural Research**
   - Cultivar comparison studies
   - Management practice evaluation
   - Phenological model validation

---

## 8. LIMITATIONS AND FUTURE WORK

### 8.1 Current Limitations
- **Cloud cover**: Potential data gaps in cloudy conditions (not evident in this dataset)
- **Plot-level resolution**: Cannot detect within-field variability
- **Rule-based classification**: May not capture all phenological nuances
- **Single crop season**: Findings specific to this growing season

### 8.2 Recommended Future Enhancements
1. **Machine Learning Integration**
   - Train supervised classifiers (Random Forest, SVM) for phenology
   - Use labeled field observations for validation

2. **Additional Indices**
   - Include EVI (Enhanced Vegetation Index)
   - Red-edge based indices for early senescence detection

3. **Multi-Year Analysis**
   - Establish baseline phenological calendars
   - Quantify inter-annual variability

4. **Higher Spatial Resolution**
   - Sub-field variability assessment
   - Pixel-level phenology mapping

5. **Integration with Ground Data**
   - Field observations for validation
   - Crop yield correlation analysis

6. **Real-Time Processing**
   - Automated alerts for phenological events
   - Integration with farm management systems

---

## 9. CONCLUSIONS

This research successfully developed and implemented an automated methodology for crop phenology classification using multi-temporal satellite-derived vegetation indices. The approach combines:

- **Robust temporal analysis** through 16-day moving window slope calculations
- **Multi-index integration** (NDVI, SAVI, NDWI) for comprehensive vegetation monitoring
- **Rule-based classification** providing interpretable phenology stages
- **Interactive visualization** enabling spatio-temporal pattern exploration

The methodology was applied to 53 agricultural plots over a complete crop cycle, generating:
- **Quantitative outputs**: Slope-enriched time series data with phenology classifications
- **Static visualizations**: Publication-ready figures showing temporal dynamics
- **Interactive maps**: 28 web-based maps for spatial phenology exploration

Results demonstrate clear phenological progression patterns, with most plots transitioning from bare soil (December) through seedling, tillering, and growth stages (January-February) to complete ripening by late March. The automated pipeline provides a scalable, reproducible framework for operational crop phenology monitoring.

---

## 10. DATA AND CODE AVAILABILITY

### 10.1 Input Data
- `classified_data_input.csv`: Original satellite-derived vegetation indices
- `figures/new-coordinates.xlsx`: Plot boundary coordinates

### 10.2 Processed Data
- `plot_data_with_slopes.csv`: Complete dataset with slopes and classifications
- `phenology_stage4_transitions.csv`: Phenology transition events

### 10.3 Visualizations
- `figures/`: Individual plot and comparative analysis figures (PNG)
- `phenology_maps/`: Interactive HTML maps for all observation dates

### 10.4 Code
- `laddu.py`: Main processing pipeline
  - Data preprocessing
  - Slope calculation
  - Phenology classification
  - Visualization generation
- `map_new_coordinates.py`: Interactive map generation script

### 10.5 Summary Documents
- `RESEARCH_SUMMARY.md`: This comprehensive methodology document
- `README.md`: Project overview and quick start guide

---

## CITATION SUGGESTION

If you use this methodology or code in your research, please consider the following citation format:

```
[Your Name et al.] (2025). Automated Crop Phenology Classification Using 
Multi-Temporal Satellite-Derived Vegetation Indices: A Rule-Based Approach 
with Temporal Slope Analysis. [Journal/Conference Name], [Volume], [Pages].

Dataset: Multi-temporal satellite observations of 53 agricultural plots,
Bihar region, India (December 2024 - April 2025).

Methodology: 16-day moving window slope calculation with median aggregation,
composite growth index (G = 0.6*NDVI + 0.4*SAVI), Savitzky-Golay smoothing,
and rule-based five-stage phenology classification.

Code and data available at: [Repository URL]
```

---

## ACKNOWLEDGMENTS

**Data Processing**: Python-based automated pipeline
**Visualization**: Matplotlib (static) and Folium (interactive web maps)
**Analysis Period**: December 2024 - April 2025
**Study Area**: Agricultural region in Bihar, India

---

**Document Version**: 1.0  
**Date**: October 23, 2025  
**Status**: Complete methodology and results summary
