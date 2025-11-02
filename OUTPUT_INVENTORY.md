# Complete Output Inventory

## 📊 Data Files (3 files)

### Primary Outputs
1. **`plot_data_with_slopes.csv`** ⭐ MAIN OUTPUT
   - 3,074 rows × 13+ columns
   - 53 plots × 28 dates
   - Columns: plot_id, date, NDVI, SAVI, NDWI, NDVI_slope, SAVI_slope, NDWI_slope, G, G_sm, sG, stage4_code, stage_4
   - Date range: 2024-12-27 to 2025-04-11

2. **`phenology_stage4_transitions.csv`**
   - Transition dates only (when stage changes)
   - Format: plot_id, date, from_stage, to_stage, stage_name
   - Useful for identifying key phenological events

3. **`classified_data_input.csv`** (INPUT)
   - Original satellite data
   - 3,074 observations

---

## 📈 Static Visualizations (14 PNG files)

### Individual Plot Analysis - Plot 1 (Green Field)

4. **`figures/plot_1_phenology_classification.png`**
   - 3-panel time series
   - Panel 1: NDVI, SAVI, NDWI profiles
   - Panel 2: Composite growth index (G and G_smoothed)
   - Panel 3: Phenology stage classification over time

5. **`figures/plot_1_ndvi_slope.png`**
   - NDVI rate of change (Δ NDVI/day)
   - X-axis: 10-day interval ticks
   - Shows growth vs. senescence periods

6. **`figures/plot_1_savi_slope.png`**
   - SAVI rate of change (Δ SAVI/day)
   - 10-day interval x-axis

7. **`figures/plot_1_ndwi_slope.png`**
   - NDWI rate of change (Δ NDWI/day)
   - 10-day interval x-axis

### Individual Plot Analysis - Plot 2 (Blue Field)

8. **`figures/plot_2_phenology_classification.png`**
   - Same format as Plot 1
   - 3-panel phenology analysis

9. **`figures/plot_2_ndvi_slope.png`**
   - NDVI slope for Plot 2

10. **`figures/plot_2_savi_slope.png`**
    - SAVI slope for Plot 2

11. **`figures/plot_2_ndwi_slope.png`**
    - NDWI slope for Plot 2

### Comparative Analysis (Plots 1 & 2)

12. **`figures/comparison_plots_1_2.png`**
    - Side-by-side comparison
    - Multiple panels showing NDVI, SAVI, NDWI for both plots

13. **`figures/timeline_comparison_1_2.png`**
    - Overlay comparison
    - All three indices on same timeline for both plots

14. **`figures/classification_comparison_1_2.png`**
    - Phenology stage progression comparison
    - Shows timing differences between the two plots

### Legacy Map Output

15. **`figures/classification_map_20250126.png`**
    - Static snapshot of map on January 26, 2025
    - 53 plots with color-coded phenology

16. **`figures/classification_map_20250126.html`**
    - Interactive version of above map

---

## 🗺️ Interactive Web Maps (28 HTML files)

### Temporal Map Series
Located in: **`phenology_maps/`** directory

17-44. **28 Interactive HTML Maps** (one per observation date):

**December 2024:**
- `map_2024_12_27.html` - Initial bare soil stage

**January 2025:**
- `map_2025_01_11.html` - Seedling emergence
- `map_2025_01_19.html` - Early tillering
- `map_2025_01_26.html` - Tillering/Growth transition
- `map_2025_01_29.html`
- `map_2025_01_31.html`

**February 2025:**
- `map_2025_02_03.html` - Active growth
- `map_2025_02_08.html`
- `map_2025_02_10.html`
- `map_2025_02_13.html`
- `map_2025_02_15.html` - Peak growth, ripening begins
- `map_2025_02_18.html`
- `map_2025_02_23.html`

**March 2025:**
- `map_2025_03_02.html` - Growth/Ripening mix
- `map_2025_03_05.html`
- `map_2025_03_07.html`
- `map_2025_03_10.html`
- `map_2025_03_12.html`
- `map_2025_03_15.html`
- `map_2025_03_22.html` - All plots ripening (100%)
- `map_2025_03_25.html`
- `map_2025_03_27.html`
- `map_2025_03_29.html`
- `map_2025_03_30.html`

**April 2025:**
- `map_2025_04_01.html` - Late season ripening
- `map_2025_04_06.html`
- `map_2025_04_09.html`
- `map_2025_04_11.html` - Final observation

**Map Features:**
- ✅ Satellite imagery base layer (Esri World Imagery)
- ✅ OpenStreetMap alternative layer
- ✅ Color-coded circle markers by phenology stage
- ✅ Interactive popups with plot details (NDVI, SAVI, NDWI, coordinates)
- ✅ Plot number labels
- ✅ Dynamic legend with stage colors and statistics
- ✅ Fullscreen mode
- ✅ Distance measurement tool
- ✅ Layer switcher control

---

## 📂 Coordinate Data Files

45. **`figures/new-coordinates.xlsx`** (INPUT)
    - 24 plots × 4 corner coordinates
    - Format: "lat, lon" strings
    - Used for map generation

46. **`figures/plots - Sheet1.csv`** (INPUT)
    - Alternative coordinate format
    - 53 plots

---

## 💻 Code Files (3 Python scripts)

47. **`laddu.py`** ⭐ MAIN PROCESSING PIPELINE
    - 1,012 lines of code
    - Functions:
      - Data loading and cleaning
      - Outlier detection
      - Slope calculation (16-day window)
      - Composite index calculation
      - Savitzky-Golay smoothing
      - Phenology classification (rule-based)
      - Transition detection
      - Visualization generation
      - Map creation

48. **`map_new_coordinates.py`**
    - 302 lines of code
    - Generates 28 interactive HTML maps
    - Uses Folium library
    - Processes Excel coordinate file
    - Loops through all observation dates

49. **`create_classification_map.py`** (Legacy)
    - 226 lines
    - Single-date map generation
    - 53 plots from CSV coordinates

50. **`create_simple_map.py`** (Legacy)
    - 155 lines
    - Basic field location map
    - No phenology classifications

---

## 📄 Documentation Files

51. **`RESEARCH_SUMMARY.md`** ⭐ THIS DOCUMENT
    - Complete methodology description
    - Results summary
    - Technical specifications
    - Ready for research paper inclusion

52. **`OUTPUT_INVENTORY.md`**
    - Complete file listing (this file)
    - Quick reference guide

53. **`README.md`** (if exists)
    - Project overview
    - Quick start guide

---

## 📊 SUMMARY STATISTICS

### Data Coverage
- **Plots**: 53 total (24 with precise GPS coordinates)
- **Observation Dates**: 28 (Dec 27, 2024 - Apr 11, 2025)
- **Total Observations**: 3,074 data points
- **Average Observations per Plot**: ~58 (all dates included)
- **Study Duration**: 106 days

### Output Counts
- **CSV Data Files**: 3 (1 input, 2 outputs)
- **Static Images (PNG)**: 14 publication-ready figures
- **Interactive Maps (HTML)**: 28 temporal maps + 2 legacy maps = 30 total
- **Python Scripts**: 4 (2 main, 2 legacy)
- **Documentation Files**: 2 comprehensive documents
- **Coordinate Files**: 2 (Excel + CSV)

### Total Files Generated: **50+ files**

---

## 🎯 KEY FILES FOR RESEARCH PAPER

### Essential Data
1. **`plot_data_with_slopes.csv`** - Main dataset for analysis
2. **`phenology_stage4_transitions.csv`** - Key phenological events

### Essential Figures (for paper)
3. **`figures/plot_1_phenology_classification.png`** - Example phenology time series
4. **`figures/plot_2_phenology_classification.png`** - Second example for comparison
5. **`figures/plot_1_ndvi_slope.png`** - Slope analysis example
6. **`figures/comparison_plots_1_2.png`** - Multi-plot comparison
7. **`figures/classification_comparison_1_2.png`** - Phenology progression comparison

### Supporting Materials
8. **Interactive maps** - Select 3-5 key dates for supplementary material:
   - `map_2024_12_27.html` - Initial stage
   - `map_2025_02_15.html` - Transition period
   - `map_2025_03_22.html` - Peak ripening
   - (Convert to PNG if needed for print publication)

### Methodology
9. **`RESEARCH_SUMMARY.md`** - Complete methodology section
10. **`laddu.py`** - Code availability (cite in paper, provide as supplement)

---

## 📐 FILE SIZES (Approximate)

- CSV files: ~500 KB each (1.5 MB total)
- PNG images: ~200-500 KB each (~5 MB total)
- HTML maps: ~1-1.5 MB each (~40 MB total)
- Python scripts: ~50-100 KB each
- **Total Project Size**: ~50-60 MB

---

## 🔄 WORKFLOW SUMMARY

```
Input Data (CSV + Coordinates)
         ↓
    [laddu.py]
         ↓
    ├─→ plot_data_with_slopes.csv
    ├─→ phenology_stage4_transitions.csv
    ├─→ 14 PNG figures
    └─→ 2 legacy HTML maps
         ↓
[map_new_coordinates.py]
         ↓
    28 interactive HTML maps
```

---

## ✅ CHECKLIST FOR RESEARCH PAPER

### Methods Section
- [ ] Describe 16-day moving window slope calculation
- [ ] Explain composite growth index (G = 0.6*NDVI + 0.4*SAVI)
- [ ] Document Savitzky-Golay smoothing parameters
- [ ] Present phenology classification rules (5 stages)
- [ ] Include threshold values table

### Results Section
- [ ] Include Plot 1 & 2 phenology classification figures
- [ ] Show slope analysis (NDVI slope plot)
- [ ] Present comparison plots
- [ ] Add statistics table (stage distribution by date)
- [ ] Describe temporal progression patterns

### Figures (Suggested)
- **Figure 1**: Methodology flowchart
- **Figure 2**: Plot 1 phenology time series (3-panel)
- **Figure 3**: NDVI slope analysis for Plot 1
- **Figure 4**: Comparison of Plots 1 & 2 phenology
- **Figure 5**: Spatial map showing phenology distribution (select 3 key dates)
- **Figure 6**: Transition timeline for all plots

### Tables (Suggested)
- **Table 1**: Phenology classification rules and thresholds
- **Table 2**: Stage distribution statistics by date
- **Table 3**: Transition dates for example plots (1 & 2)

### Supplementary Material
- [ ] All 28 interactive HTML maps
- [ ] Complete dataset (plot_data_with_slopes.csv)
- [ ] Python code (laddu.py, map_new_coordinates.py)
- [ ] Coordinate data files

---

**Document Created**: October 23, 2025  
**Project**: Automated Crop Phenology Classification  
**Total Outputs**: 50+ files across data, visualizations, maps, and code
