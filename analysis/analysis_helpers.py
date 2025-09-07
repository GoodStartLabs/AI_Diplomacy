# analysis_constants.py 
import os 
import json 
from pathlib import Path
import pandas as pd
import zipfile

def process_standard_game_inputs(game_data_folder : Path, selected_game : str) -> dict[str, pd.DataFrame]:
    path_to_folder = game_data_folder / selected_game

    assert os.path.exists(path_to_folder / "overview.jsonl"), f"Overview file not found in {path_to_folder}"
    overview = pd.read_json(path_to_folder / "overview.jsonl", lines=True)
    
    # get all turn actions from lmvs
    assert os.path.exists(path_to_folder / "lmvsgame.json"), f"LMVS file not found in {path_to_folder}"
    path_to_file = path_to_folder / "lmvsgame.json"

    # Use the standard `json` library to load the file into a Python object
    with open(path_to_file, 'r') as f:
        lmvs_data = json.load(f)
        
    assert os.path.exists(path_to_folder / "llm_responses.csv"), f"LLM responses file not found in {path_to_folder}"
    all_responses = pd.read_csv(path_to_folder / "llm_responses.csv")
    
    return {"overview":overview, "lmvs_data":lmvs_data, "all_responses":all_responses}

def process_game_in_zip(zip_path: Path, selected_game: str) -> dict[str, pd.DataFrame]:
    zip_name = zip_path.stem  # Gets filename without extension
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        overview = pd.read_json(zip_ref.open(f"{zip_name}/{selected_game}/overview.jsonl"), lines=True)
        lmvs_data = json.load(zip_ref.open(f"{zip_name}/{selected_game}/lmvsgame.json"))
        all_responses = pd.read_csv(zip_ref.open(f"{zip_name}/{selected_game}/llm_responses.csv"))
    return {"overview": overview, "lmvs_data": lmvs_data, "all_responses": all_responses}

supply_centers = [
    "ANK", "ARM", "BEL", "BER", "BUD", "BUL", "CON", "DEN", "EDI", "GRE",
    "HOL", "KIE", "LON", "LVP", "MAR", "MOS", "MUN", "NAP", "PAR", "POR",
    "ROM", "RUM", "SER", "SEV", "SMY", "SWE", "TRI", "TUN",
    "VEN", "VIE", "WAR", 
    "SPA", "STP", "BUL" # coastal provinces
]

coastal_scs = ["SPA/SC", "SPA/NC",
    "STP/SC", "STP/NC", 'BUL/EC',
       'BUL/SC',]

COUNTRIES = ['AUSTRIA', 'ENGLAND', 'FRANCE', 'GERMANY', 'ITALY', 'RUSSIA', 'TURKEY']

place_identifier = "[A-Z]{3}(?:/[A-Z]{2})?"
place_capturing_regex = r"([A-Z]{3})"
unit_identifier = rf"[AF] {place_identifier}"
unit_move = rf"{unit_identifier} . {place_identifier}"

possible_commands = {
    "Move": f"^"+unit_move, # distinguishing this from support
    "Support Move": f"{unit_identifier} S {unit_move}",
    "Support Hold": fr"{unit_identifier} S {unit_identifier}(?!\s+[.\-]\s+{place_identifier})",
    "Convoy": f"F {place_identifier} C {unit_move}", # No convoys in here? 
    "Hold": f"{unit_identifier} H",
    "Build": f"{unit_identifier} B",
    "Disband": f"{unit_identifier} D",
    "Retreat": f"{unit_identifier} R",
}
