# Crop Phenology Classification Project

## Overview
This project extracts satellite data and classifies crop phenology stages for agricultural plots using Sentinel-2 imagery and vegetation indices.

## Workspace Structure

### Core Scripts
- **laddu.py** - Main classification pipeline
  - Loads data, calculates slopes, classifies phenology stages
  - Generates visualizations with colored stage backgrounds
  - Auto-detects input CSV files

- **extract_satellite_data_optimized.py** - Satellite data extraction
  - Downloads Sentinel-2 imagery from Google Earth Engine
  - Calculates NDVI, SAVI, and NDWI (McFeeters formula)
  - Processes 50 plots with progress saving and retry logic

- **authenticate_gee.py** - Google Earth Engine authentication helper

### Data Files

#### Input Data
- **figures/plots - Sheet1.csv** - Plot coordinates (50 plots with 4 corner coordinates each)

#### Output Data
- **satellite_data_corrected_ndwi.csv** - Extracted satellite data (4,400 records)
  - Date range: 2024-12-02 to 2025-04-26
  - Columns: plot_id, date, NDVI, SAVI, NDWI
  - NDWI calculated with corrected McFeeters formula: (Green - NIR) / (Green + NIR)

- **plot_data_with_slopes.csv** - Classified data with slopes
  - All 50 plots with phenology classifications
  - Slopes calculated for NDVI, SAVI, NDWI

- **phenology_stage4_transitions.csv** - Stage transition dates
  - First occurrence of each phenology stage per plot

#### Legacy Data (for reference)
- **filter_results - Sheet1.csv** - Original data with incorrect NDWI formula

### Visualizations (figures/)
- *Slope plots*: NDVI, NDWI, SAVI slopes for plots 2, 6, 31
- *Phenology classification plots*: 3-panel visualizations with colored stage backgrounds

## Phenology Classification

### 5-Stage System
0. *Bare* - No crop activity (pre-planting/post-harvest)
1. *Seedling* - Early emergence (G ≤ 0.30, rising slope)
2. *Tillering* - Vegetative growth (0.30 < G ≤ 0.50, rising slope)
3. *Growth* - Active growth (G > 0.50, rising slope)
4. *Ripening* - Maturity (high G, falling slope)

### Key Thresholds (Data-Driven)
- G_seed_max = 0.30 (25th percentile)
- G_high = 0.50 (median)
- Greenness index: G = 0.6*NDVI + 0.4*SAVI
- Requires rising slope for Seedling/Tillering to avoid misclassifying bare fields

## Vegetation Indices

- *NDVI* = (NIR - Red) / (NIR + Red)
- *SAVI* = ((NIR - Red) / (NIR + Red + 0.5)) × 1.5
- *NDWI* (McFeeters) = (Green - NIR) / (Green + NIR) ✅ CORRECTED

## Dataset Statistics

- *Total plots*: 50
- *Total records*: 4,400 (88 images per plot on average)
- *Date range*: December 1, 2024 → April 30, 2025
- *Cloud threshold*: <20%
- *Resolution*: 10m (Sentinel-2)

### Index Ranges
| Index | Mean  | Min    | Max   |
|-------|-------|--------|-------|
| NDVI  | 0.43  | 0.12   | 0.93  |
| SAVI  | 0.65  | 0.18   | 1.39  |
| NDWI  | -0.47 | -0.83  | -0.17 |

## Usage

### 1. Extract New Satellite Data (Optional)
bash
python authenticate_gee.py  # First time only
python extract_satellite_data_optimized.py


### 2. Run Classification
bash
python laddu.py


This will:
- Auto-detect the input CSV
- Calculate slopes
- Classify phenology stages
- Generate visualizations for plots 2, 6, 31
- Save results to plot_data_with_slopes.csv and phenology_stage4_transitions.csv

## Requirements

- Python 3.11+
- pandas
- numpy
- matplotlib
- earthengine-api (for satellite extraction)
- Google Earth Engine account

## Notes

- Classification uses data-driven thresholds derived from actual field statistics
- Bare stage is default when greenness is low and no rising trend detected
- All visualizations include colored backgrounds representing phenology stages
- Progress is automatically saved during satellite extraction (every 10 plots)
