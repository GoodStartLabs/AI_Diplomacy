#!/usr/bin/env python3
"""
Orchestration script to run all three analysis scripts in sequence:
1. 1_make_longform_orders_data.py 
2. 2_make_convo_data.py
3. 3_make_phase_data.py

This script passes the same CLI arguments to each script.

eg

# Basic usage with all parameters
python analysis/make_all_analysis_data.py --selected_game game1 game2 --game_data_folder "/path/to/Game Data" --output_folder "/path/to/Game Data - Analysis" --analysis_folder "/path/to/analysis"

# Using output_folder as analysis_folder
python analysis/make_all_analysis_data.py --selected_game game1 --game_data_folder "/path/to/Game Data" --output_folder "/path/to/Game Data - Analysis"

# or leave out to process all games in the data folder
python analysis/make_all_analysis_data.py --game_data_folder "/path/to/Game Data" --output_folder "/path/to/Game Data - Analysis"
"""
import argparse

from pathlib import Path
import pandas as pd
from tqdm import tqdm

from analysis.p1_make_longform_orders_data import make_longform_order_data
from analysis.p2_make_convo_data import make_conversation_data   
from analysis.p3_make_phase_data import make_phase_data
from analysis.analysis_helpers import get_country_to_model_mapping, process_standard_game_inputs, process_game_inputs_in_zip
from analysis.schemas import COUNTRIES

from typing import Dict



def process_game_data_from_folders(game_path : Path) -> Dict[str, pd.DataFrame]:
    """Reads log data from folder and makes analytic data sets"""
    
    game_data : dict[str, pd.DataFrame] = process_standard_game_inputs(path_to_folder=game_path)
    
    country_to_model = get_country_to_model_mapping(game_data["overview"], game_data["all_responses"])
    
    orders_data : pd.DataFrame = make_longform_order_data(country_to_model=country_to_model, 
                                   lmvs_data=game_data["lmvs_data"],
                                   all_responses=game_data["all_responses"])
    
    conversations_data : pd.DataFrame = make_conversation_data(country_to_model=country_to_model, lmvs_data=game_data["lmvs_data"])

    phase_data : pd.DataFrame = make_phase_data(country_to_model=country_to_model, 
                           lmvs_data=game_data["lmvs_data"], 
                           conversations_data=conversations_data, 
                           orders_data=orders_data)
    
    return {"orders_data": orders_data, 
            "conversations_data": conversations_data, 
            "phase_data": phase_data}

def process_game_data_from_zip(zip_path: Path, game_name: str) -> Dict[str, pd.DataFrame]:
    """Reads log data from zip and makes analytic data sets"""

    game_data: dict[str, pd.DataFrame] = process_game_inputs_in_zip(zip_path=zip_path, selected_game=game_name)

    country_to_model = get_country_to_model_mapping(game_data["overview"], game_data["all_responses"])

    orders_data: pd.DataFrame = make_longform_order_data(
        country_to_model=country_to_model,
        lmvs_data=game_data["lmvs_data"],
        all_responses=game_data["all_responses"],
    )

    conversations_data: pd.DataFrame = make_conversation_data(
        country_to_model=country_to_model, lmvs_data=game_data["lmvs_data"]
    )

    phase_data: pd.DataFrame = make_phase_data(
        country_to_model=country_to_model,
        lmvs_data=game_data["lmvs_data"],
        conversations_data=conversations_data,
        orders_data=orders_data,
    )

    return {
        "orders_data": orders_data,
        "conversations_data": conversations_data,
        "phase_data": phase_data,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run all three analysis scripts in sequence with the same arguments.")
    parser.add_argument(
        "--selected_game", 
        type=str, 
        nargs='*', 
        help="One or more specific games to process. If not provided, all games in the data folder will be processed."
    )
    parser.add_argument(
        "--game_data_folder", 
        type=str, 
        required=True,
        help="The folder where game data is stored."
    )
    parser.add_argument(
        "--analysis_folder", 
        type=str, 
        required=True,
        help="The folder to save the new analysis folders and files"
    )

    args = parser.parse_args()
    
    # Convert namespace to dictionary
    args_dict = vars(args)
    args_dict["analysis_folder"] = Path(args_dict["analysis_folder"])
    args_dict["game_data_folder"] = Path(args_dict["game_data_folder"])
    
    games_to_process = args.selected_game
    if not games_to_process:
        games_to_process = [p.name for p in args_dict["game_data_folder"].iterdir() if p.is_dir()]
    for game in tqdm(games_to_process, desc="Processing games"):
        game_path = args_dict["game_data_folder"] / game
        if not game_path.is_dir():
            continue
        
        try:
            results = process_game_data_from_folders(game_path=game_path)
            for data_set, df in results.items():
                output_dir = args_dict["analysis_folder"] / data_set
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"{game}_{data_set}.csv"
                df.to_csv(output_path, index=False)
        except Exception as e:
            print(f"Error processing game {game}: {e}")