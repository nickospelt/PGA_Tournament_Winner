# Sports Analytics Data Architecture Plan

## Overview

This document outlines the data architecture plan for a sports analytics
pipeline that ingests PGA Tour data from ESPN, stores it in Parquet
files, and queries it using DuckDB. The goal is to support feature
engineering, machine learning models, and an AI betting agent.

------------------------------------------------------------------------

# 1. Schema Updates

The original schema stores most statistics at the **tournament level**.
However, scoring is naturally **round-level data**. To improve
flexibility for modeling and analytics, the schema should separate
tournament statistics from round scores.

## Player Tournament Stats

One row per **player per tournament**.

Columns:

-   player_name (FK → players)
-   tournament_id (FK → tournaments)
-   drive_dist
-   drive_acc
-   gir_acc
-   putts_per_gir
-   eagles
-   birdies
-   pars
-   bogeys
-   double_bogeys
-   earnings
-   fedex_pts
-   total_score

## Player Round Scores

One row per **player per round**.

Columns:

-   player_name
-   tournament_id
-   round
-   score

Example rows:

  player        tournament     round   score
  ------------- -------------- ------- -------
  Tiger Woods   Masters 2025   1       69
  Tiger Woods   Masters 2025   2       71

Benefits:

-   easier time-series analysis
-   cleaner SQL
-   easier rolling window features
-   avoids wide schemas with r1/r2/r3/r4 columns

------------------------------------------------------------------------

# 2. Local Raw Data Structure

Raw tables should be stored in **Parquet files** organized like a small
data lake.

Directory layout:

    data/
        pga/
            raw/

                players/
                    players.parquet

                courses/
                    courses.parquet

                tournaments/
                    tournaments.parquet

                holes/
                    course=<course_name>/
                        holes.parquet

                player_tournament_stats/
                    season=<year>/
                        tournament_id=<id>/
                            stats.parquet

                player_round_scores/
                    season=<year>/
                        tournament_id=<id>/
                            rounds.parquet

                weather_records/
                    location=<location>/
                        year=<year>.parquet

Guidelines:

-   Never overwrite historical files.
-   Append new partitions when new tournaments are scraped.
-   Use tournament boundaries as natural partitions.

Typical file sizes will be small because sports datasets are small, but
this structure scales well when moved to cloud storage.

------------------------------------------------------------------------

# 3. Data Validation Layer (Pydantic)

Because this pipeline relies on **scraped ESPN data**, all records must be
validated before they are written to Parquet. Scraped HTML structures
can change unexpectedly and may produce malformed or incomplete rows.

To protect the dataset from corruption, **Pydantic models serve as the
schema enforcement layer for the ingestion pipeline.**

Validation occurs between scraping and storage.

Pipeline flow:

Scraper → Parsed Dict → Pydantic Validation → DataFrame → Parquet

------------------------------------------------------------------------

## Validation Responsibilities

Pydantic models enforce:

- required fields
- correct data types
- logical value ranges
- consistent schema across all Parquet files

Each entity in the system has a corresponding validation model.

Examples:

- Player
- Tournament
- Course
- Hole
- WeatherRecord
- PlayerTournamentStats
- PlayerRoundScore

These models define the **source-of-truth schema** for raw data.

------------------------------------------------------------------------

## Example Validation Step

Scraped rows are first parsed into dictionaries.

Example scraped record:

```python
from models.player_record import PlayerRecord
from pydantic import ValidationError

raw_record = {
    "player_name": "Scottie Scheffler",
    "tournament_id": 401465512,
    "driving_distance": "318.2",
    "driving_accuracy": "64.3"
}

try:
    record = PlayerRecord(**raw_record)
except ValidationError as e:
    logger.warning(f"Invalid record skipped: {e}")
```

## Value Constaints

The pydantic models can be updated to ensure that only acceptable values are added to the datasets

Example pydnatic model:

```python
from pydantic import BaseModel, Field

class PlayerTournamentStats(BaseModel):

    player_name: str
    tournament_id: int

    drive_dist: float = Field(ge=200, le=400)
    drive_acc: float = Field(ge=0, le=100)
    gir_acc: float = Field(ge=0, le=100)
    putts_per_gir: float = Field(ge=0, le=3)
```

## Writing Valid Records

```python
import pandas as pd

records = [r.model_dump() for r in validated_records]

df = pd.DataFrame(records)

df.to_parquet("data/raw/player_tournament_stats/season=2025/tournament_id=401465512/stats.parquet")
```


------------------------------------------------------------------------

# 4. Feature Tables

Feature tables are **precomputed datasets used by machine learning
models**.

They are derived from raw tables using SQL queries in DuckDB.

Feature tables should be stored separately.

Directory:

    data/pga/features/

Example feature tables:

    player_form_features.parquet
    player_course_history_features.parquet
    tournament_features.parquet

## Example Features

Player form:

-   avg_score_last_20_rounds
-   avg_score_last_5_tournaments
-   driving_accuracy_last_10_events

Course fit:

-   avg_score_at_course
-   driving_accuracy_vs_course_average

Weather sensitivity:

-   avg_score_windy_conditions
-   avg_score_low_temperature

------------------------------------------------------------------------

# 5. When Features Are Computed

Features are computed **after new raw data arrives**.

Pipeline schedule example for PGA:

1.  Scrape ESPN after each round
2.  Write raw parquet partitions
3.  Recompute feature tables
4.  Save updated feature datasets

This means features update approximately:

-   4 times per PGA tournament
-   daily for NBA/NFL if expanded

Feature generation should be done in **batch pipelines**, not
dynamically during model execution.

Example DuckDB query:

``` sql
CREATE OR REPLACE TABLE player_form_features AS
SELECT
    player_name,
    tournament_id,
    AVG(score) OVER (
        PARTITION BY player_name
        ORDER BY tournament_date
        ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
    ) AS avg_score_last_20_rounds
FROM player_round_scores;
```

Then export to Parquet.

------------------------------------------------------------------------

# 6. Using the Data

## Training Models

Feature tables are used to train models.

Example dataset:

  ----------------------------------------------------------------------------------------------
  player         tournament     avg_score_last_20_rounds   course_history_score   target_win
  -------------- -------------- -------------------------- ---------------------- --------------

  ----------------------------------------------------------------------------------------------

Models such as XGBoost can train directly on these tables.

## Running Predictions

When the AI agent needs predictions:

1.  Query feature tables
2.  Load model
3.  Generate predictions
4.  Compare predictions to sportsbook odds

Example DuckDB query:

``` python
duckdb.sql("""
SELECT *
FROM player_tournament_features
WHERE tournament_id = 401465512
""")
```

The agent should **never recompute features dynamically**.

------------------------------------------------------------------------

# 7. Transition to Cloud

When moving to production, the same structure can be used with object
storage such as S3.

Example:

    s3://sports-data-lake/
        raw/
        features/

DuckDB can query these files directly without changing schema or
queries.

------------------------------------------------------------------------

# 8. Summary

Key principles:

-   Preserve the natural granularity of source data.
-   Separate raw data, curated tables, and feature tables.
-   Use tournament-based partitioning.
-   Precompute feature tables in batch pipelines.
-   Keep models and agents consuming feature datasets, not raw tables.

This architecture scales from local experimentation to production
analytics systems.
