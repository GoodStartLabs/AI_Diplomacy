"""Utility functions and constants for loading Diplomacy analysis data.

This module provides helpers to read game data stored either as a folder on disk
or inside a zip archive, plus a few constant lists and regex patterns that are
used across the analysis scripts.

"""

from pathlib import Path
from typing import Dict, Union
import json
import zipfile

import pandas as pd
from analysis.schemas import COUNTRIES
from analysis.validation import LMVSGame

__all__: list[str] = [
    "process_standard_game_inputs",
    "process_game_inputs_in_zip",
    "get_country_to_model_mapping",
]
    
def process_standard_game_inputs(path_to_folder: Path) -> Dict[str, Union[pd.DataFrame, dict]]:
    """
    Read in a game folder and return the overview, lmvs_data, and all_responses
    
    Args:
        path_to_folder: Path to the game folder. Must contain overview.jsonl, lmvsgame.json, and llm_responses.csv files.
    
    Returns:
        Dictionary containing overview, lmvs_data, and all_responses
    """
    # ----- check files exist -----
    overview_path = path_to_folder / "overview.jsonl"
    lmvsgame_path = path_to_folder / "lmvsgame.json"
    llm_resp_path = path_to_folder / "llm_responses.csv"

    if not overview_path.exists():
        raise FileNotFoundError(str(overview_path))
    if overview_path.stat().st_size == 0:
        raise FileNotFoundError(f"{overview_path} is empty")

    if not lmvsgame_path.exists():
        raise FileNotFoundError(str(lmvsgame_path))
    if lmvsgame_path.stat().st_size == 0:
        raise FileNotFoundError(f"{lmvsgame_path} is empty")
    if not llm_resp_path.exists():
        raise FileNotFoundError(str(llm_resp_path))
    if llm_resp_path.stat().st_size == 0:
        raise FileNotFoundError(f"{llm_resp_path} is empty")

    # ----- load data -----
    overview = pd.read_json(overview_path, lines=True)

    with open(lmvsgame_path, "r") as f:
        lmvs_data = json.load(f)
    # validate the LMVS data format
    LMVSGame.model_validate(
        lmvs_data,
    )

    all_responses = pd.read_csv(llm_resp_path)
    expected_columns = ['model', 'power', 'phase', 'response_type', 'raw_input', 'raw_response',
       'success']
    missing_columns = [col for col in expected_columns if col not in all_responses.columns]
    assert len(missing_columns) == 0, f"Missing required columns in CSV: {missing_columns}"
    return {"overview":overview, "lmvs_data":lmvs_data, "all_responses":all_responses}

def get_country_to_model_mapping(overview_df : pd.DataFrame, llm_responses_df : pd.DataFrame) -> pd.Series:
    """ Get a country:model map of which country was played by which model, different in different versions of data"""
    country_to_model = overview_df.loc[1].reindex(COUNTRIES)
    if pd.isnull(country_to_model).any(): 
        if llm_responses_df is not None:
            country_to_model = llm_responses_df.set_index("power")["model"].reindex(COUNTRIES)
    return country_to_model

def process_game_inputs_in_zip(zip_path: Path, selected_game: str) -> Dict[str, Union[pd.DataFrame, dict]]:
    """
    Read in a game folder and return the overview, lmvs_data, and all_responses
    
    Args:
        zip_path: Path to the zip file
        selected_game: Name of the game to extract
    
    Returns:
        Dictionary containing overview, lmvs_data, and all_responses
    """
    zip_name = zip_path.stem  # Gets filename without extension
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        overview = pd.read_json(zip_ref.open(f"{zip_name}/{selected_game}/overview.jsonl"), lines=True)
        lmvs_data = json.load(zip_ref.open(f"{zip_name}/{selected_game}/lmvsgame.json"))
        all_responses = pd.read_csv(zip_ref.open(f"{zip_name}/{selected_game}/llm_responses.csv"))
    return {"overview": overview, "lmvs_data": lmvs_data, "all_responses": all_responses}
