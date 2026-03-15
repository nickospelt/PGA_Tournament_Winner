import os
import pandas as pd
from typing import List
from pydantic import BaseModel

def save_to_parquet(data: List[BaseModel], dataset_name: str, partition_cols: List[str] = None):
    """
    Saves a list of Pydantic models to Parquet files with Hive-style partitioning.

    Args:
        data (List[BaseModel]): List of Pydantic model instances.
        dataset_name (str): Name of the dataset (e.g., 'player_tournament_stats').
        partition_cols (List[str]): List of columns to partition by (e.g., ['season', 'tournament_id']).
    """
    if not data:
        print(f"No data to save for {dataset_name}")
        return
    
    # Convert Pydantic models to DataFrame
    records = [d.model_dump() for d in data]
    df = pd.DataFrame(records)
    
    # Base directory for the dataset
    base_path = f"data/pga/raw/{dataset_name}"
    
    if partition_cols:
        # Group by partition columns to handle multiple partitions in one batch
        # This ensures we write correct Hive-style paths
        grouped = df.groupby(partition_cols)
        
        for keys, group in grouped:
            # keys is a tuple of values corresponding to partition_cols
            if not isinstance(keys, tuple):
                keys = (keys,)
            
            # Construct path: base/col1=val1/col2=val2/...
            path_parts = [base_path]
            for col, val in zip(partition_cols, keys):
                path_parts.append(f"{col}={val}")
            
            partition_dir = os.path.join(*path_parts)
            os.makedirs(partition_dir, exist_ok=True)
            
            # Write file. We use a fixed name 'data.parquet' for now as per architecture
            # implying one write per partition per run. 
            file_path = os.path.join(partition_dir, "data.parquet")
            
            # Drop partition columns from the file content as they are in the path
            # (Standard Hive partitioning usually keeps them out, but pandas read_parquet can handle both)
            # We'll keep them in the file for safety unless strictly hive-compliant readers need them out.
            # Usually it's better to keep them out to save space if partitioned.
            group_to_write = group.drop(columns=partition_cols)
            
            group_to_write.to_parquet(file_path, index=False)
            print(f"Saved {len(group)} records to {file_path}")
    else:
        # No partition, just write to base path
        os.makedirs(base_path, exist_ok=True)
        file_path = os.path.join(base_path, "data.parquet")
        df.to_parquet(file_path, index=False)
        print(f"Saved {len(df)} records to {file_path}")
