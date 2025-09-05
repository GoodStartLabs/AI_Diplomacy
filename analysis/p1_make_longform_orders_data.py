"""

Set-up & constants
    imports pandas, numpy, json, copy, re, os
    hard-codes lists for the seven Diplomacy powers, every supply-center (SC) province, and the coastal SC variants

Top-level function make_longform_order_data(game_data_folder, selected_game)
Runs end-to-end for one game folder and returns a single long-form DataFrame (all_orders_ever).

expected game data files:
    overview.jsonl → maps each country to the LLM model that played it
    lmvsgame.json → full turn-by-turn log in the LM vs Game Engine format
    llm_responses.csv → every prompt/response the agent produced

Build a “turn_actions” super-table
    state snapshots (units, centers, influence) per phase → status_over_time
    order strings plus their official adjudication results → orders_over_time
    concatenate the two; index is COUNTRY_[units|centers|influence|orders], columns are phase names.

Explode into one-row-per-order (all_orders_ever)
    melt orders_over_time, dropping nulls, so each record has:
    country, phase, order (raw text, e.g. "A PAR - BUR (MOVE)")
    classify order with regexes → command ∈ {Move, Hold, Support Move, …}.
    extract unit_location, destination, boolean SC flags, and the adjudication result.

Annotate ownership & influence
    Helper lambdas walk back into the phase state to tag:
    which power currently controls unit_location or destination
    whether the unit is trespassing or attempting to trespass
    who owns any piece occupying the square the unit is moving into.

Support logic
    finds which orders support a given unit and records the supporting powers
    adds convenience flags (was_supported, supported_by_self, supported_by_other, etc.).

Merge relationship matrices (5 possible states: Enemy, Unfriendly, Neutral, Friendly, Ally)
    current country's view of all others (relationship_england, …)
    how all others rate this country (englands_relationship_rating, …).

Add strategic context columns
    supporting_self, supporting_an_ally
    weight column unit_order_weight (inverse of the country's total number of unit-orders for averaging).

Fuse LLM reasoning
    pulls the order-generation rows out of llm_responses.csv
    extracts free-text “reasoning”, unformatted order blob, length, and success flag (if can be done)

Return / save
    The function returns the enriched DataFrame
    Run from CLI to process all games: python make_longform_orders_data.py 
    
"""

import pandas as pd
import numpy as np

import copy
import re 
import argparse
import warnings
from pathlib import Path
from analysis.analysis_helpers import process_standard_game_inputs, get_country_to_model_mapping
from analysis.schemas import COUNTRIES, ALL_SUPPLY_CENTERS, COASTAL_SCs, PLACE_IDENTIFIER, UNIT_IDENTIFIER, UNIT_MOVE, POSSIBLE_COMMANDS
from tqdm import tqdm
import traceback
from typing import List, Optional, Dict 
# Suppress pandas warnings
warnings.filterwarnings('ignore', category=UserWarning, module='pandas.core.strings')
warnings.filterwarnings('ignore', category=pd.errors.SettingWithCopyWarning)

def make_longform_order_data(country_to_model : pd.Series, lmvs_data : pd.DataFrame, all_responses : pd.DataFrame) -> pd.DataFrame:
    """
    Makes a dataframe with a row for each order given by every power, in every phase (see module docstring for more details).
    
    Args:
        country_to_model: A Series mapping country names to model names
        lmvs_data: A DataFrame containing the game data
        all_responses: A DataFrame containing the responses from the LLM responses csv
    
    Returns:
        A DataFrame with a row for each order given by every power, in every phase
    """
    ################## PART 1 ##################
    # build `turn_actions` dataframe

    # Get units at each turn
    status_over_time = []
    for phase in lmvs_data["phases"]:
        phase_list = []
        for var in ["units", "centers", "influence"]:
            phase_list.append(pd.Series(phase["state"][var]).rename(phase["name"]).add_suffix(f"_{var}"))
        status_over_time.append(pd.concat(phase_list))
        
    status_over_time = pd.concat(status_over_time, axis=1)

    # Get orders + outcome 
    orders_over_time = []
    for phase in lmvs_data["phases"]:
        phase_orders = copy.deepcopy(phase["orders"])
        result_of_orders = phase["results"]
        
        for country, order_list in phase_orders.items():
            if order_list:
                for i, order in enumerate(order_list):
                    identifier = order[:5]
                    if result_of_orders.get(identifier, None):
                        results = '/'.join(result_of_orders[identifier]).upper()
                        if results:
                            order_list[i] = order_list[i] + f" ({results})"
                    
        orders_over_time.append(pd.Series(phase_orders).rename(phase["name"]).add_suffix("_orders"))
    orders_over_time = pd.concat(orders_over_time, axis=1)


    # index for COUNTRY_[turn_status], columns for PHASE, each value a list
    turn_actions = pd.concat([orders_over_time, status_over_time])


    ################## PART 2 ##################
    # Data by orders

    # Snippet to pull out and classifier all orders

    # build the data frame
    all_orders_ever = turn_actions.loc[turn_actions.index.str.contains("orders")].reset_index(names="country").melt(id_vars="country", 
                                                                                                    var_name="phase", 
                                                                                                    value_name="order").dropna().explode("order")
    all_orders_ever = all_orders_ever.dropna(subset="order").reset_index(drop=True)

    # categorize each order based on regex
    # note that this will overwrite if multiple regexes match, which is why we've split support into 2 commands
    for possible_command, regex in POSSIBLE_COMMANDS.items():
        all_orders_ever.loc[all_orders_ever.order.str.contains(regex, regex=True), "command"] = possible_command
        
    all_orders_ever["unit_location"] = all_orders_ever["order"].str.extract(rf"({PLACE_IDENTIFIER})")
    all_orders_ever["location_was_sc"] = all_orders_ever["unit_location"].isin(ALL_SUPPLY_CENTERS) | all_orders_ever["unit_location"].isin(COASTAL_SCs)

    # only MOVE has a destination
    all_orders_ever["destination"] = np.where(
        all_orders_ever["command"]=="Move",
        all_orders_ever["order"].str.extract(rf"{UNIT_IDENTIFIER} . ({PLACE_IDENTIFIER})", expand=False),
        np.nan
    )
    all_orders_ever["destination_was_sc"] = all_orders_ever["destination"].isin(ALL_SUPPLY_CENTERS) | all_orders_ever["destination"].isin(COASTAL_SCs)

    # Retreat also has a destination
    all_orders_ever.loc[all_orders_ever["command"]=="Retreat", "destination"] = all_orders_ever.loc[all_orders_ever["command"]=="Retreat", "order"].str.extract(rf"{UNIT_IDENTIFIER} R ({PLACE_IDENTIFIER})", expand=False)

    all_orders_ever["immediate_result"] = all_orders_ever["order"].str.extract(r"\(([^)]+)\)")
    all_orders_ever["immediate_result"] = all_orders_ever["immediate_result"].fillna("PASS")

    all_orders_ever["country"] = all_orders_ever["country"].str.replace("_orders", "")
        
    all_orders_ever["model"] = all_orders_ever["country"].map(country_to_model)
    all_orders_ever["model_short_name"] = all_orders_ever["model"].str.split("/").str[-1]
    all_orders_ever["country_model"] = all_orders_ever["country"] + " (" + all_orders_ever["model_short_name"] + ")"

    def check_location_influence(phase_id : str, location : str) -> str:
        """
        Helper - checks who owns a location at a given phase. Uses the `turn_actions` dataframe from overall context.
        
        Args:
            phase_id: The phase to check
            location: The location to check
        
        Returns:
            The country that owns the location, or "Unowned" if no country owns it
        """
        # checking who owns a location at `phase_id`
        if pd.isnull(location):
            return np.nan
        current_influence = turn_actions.loc[turn_actions.index.str.contains("influence"), phase_id]
        current_influence.index = current_influence.index.str.replace("_influence", "")
        for country, influence in current_influence.items():
            if location in influence:
                return country
        return "Unowned"

    all_orders_ever["unit_location_affiliation"] = all_orders_ever.apply(lambda row: check_location_influence(row["phase"],
                                                                                                            row["unit_location"]), axis=1)
    all_orders_ever["destination_affiliation"] = all_orders_ever.apply(lambda row: check_location_influence(row["phase"],
                                                                                                            row["destination"]), axis=1)

    def find_supporting_country(unit_command, command_type, phase) -> Optional[str]:
        """
        Helper - finds which orders support a given unit and records the supporting powers. Operating on the `all_orders_ever` dataframe.
        
        Args:
            unit_command: The unit command to find supporting orders for
            command_type: The type of command ("Move" or "Hold")
            phase: The phase to check
        
        Returns:
            A string containing a comma-separated list of countries that issued an order to support that unit, or None if no such orders exist
        """
        if command_type == "Move" or command_type == "Hold":  # commands that can be supported
            potential_supports = all_orders_ever[(all_orders_ever["phase"] == phase) & 
                                                (all_orders_ever["command"].isin(["Support Move", "Support Hold"]))]
            potential_supports = potential_supports[potential_supports["order"].str.contains(unit_command, regex=False)]
            if potential_supports.empty:
                return None
            else:
                return ",".join(potential_supports["country"].tolist())
        return None

    all_orders_ever["supported_by"] = all_orders_ever.apply(lambda row: find_supporting_country(row["order"], row["command"], row["phase"]), axis=1)
    all_orders_ever["in_anothers_territory"] =( all_orders_ever["country"] != all_orders_ever["unit_location_affiliation"]) & (all_orders_ever["unit_location_affiliation"] != "Unowned")
    all_orders_ever["moving_into_anothers_territory"] = ((all_orders_ever["country"] != all_orders_ever["destination_affiliation"]) & 
                                                         (all_orders_ever["destination_affiliation"].notnull()) & 
                                                         (all_orders_ever["destination_affiliation"] != "Unowned"))

    def find_owner_of_unit(unit_location : str, phase : str) -> Optional[str]:
        """
        Helper - finds the owner of a unit at a given phase. Operating on the `turn_actions` dataframe from overall context.
        
        Args:
            unit_location: The location of the unit to find the owner of
            phase: The phase to check
        
        Returns:
            The country that owns the unit, or None if no country owns it
        """
        if pd.notnull(unit_location):
            unit_status = turn_actions.loc[turn_actions.index.str.contains("_units"), phase]
            unit_status.index = unit_status.index.str.replace("_units", "")
            for country, units in unit_status.items():
                for unit in units:
                    if re.match(f"[AF] {unit_location}", unit):
                        return country

    def find_destination_info(destination, phase) -> Optional[Dict[str, Optional[str]]]:
        """
        Helper - finds information about the destination of a unit at a given phase. 
        Operating on the `all_orders_ever` dataframe from overall context.
        
        Args:
            destination: The location of the unit to find the owner of
            phase: The phase to check
        
        Returns:
            A dictionary containing information about the destination unit, or None if no such unit exists
        """
        if pd.notnull(destination):
            country = find_owner_of_unit(destination, phase)
            # there should only ever be one unit at a given location during a phase
            destination_unit_orders = all_orders_ever[(all_orders_ever["country"] == country) & 
                                                                (all_orders_ever["phase"] == phase) & 
                                                                (all_orders_ever["unit_location"] == destination)]
            if not destination_unit_orders.empty:
                destination_unit_orders = destination_unit_orders.iloc[0] # safe conversion to a series
                return {"destination_unit_owner": country, 
                                "destination_unit_order": destination_unit_orders["command"],
                                "destination_unit_outcome":destination_unit_orders["immediate_result"],
                                "destination_unit_supported_by": destination_unit_orders["supported_by"]}

    destination_unit_info = all_orders_ever.apply(lambda row: find_destination_info(row["destination"], row["phase"]), axis=1).apply(pd.Series)
    destination_unit_info["destination_was_occupied"] = destination_unit_info["destination_unit_owner"].notnull()

    all_orders_ever = pd.concat([all_orders_ever, destination_unit_info], axis=1)

    # if a Support action: who were they supporting? what was their support doing?
    def find_support_recipient_info(unit_order, command, phase) -> Optional[Dict[str, Optional[str]]]:
        """
        Helper - finds information about the recipient of a support action at a given phase. 
        Operating on the `all_orders_ever` dataframe from overall context.
        
        Args:
            unit_order: The order of the unit to find the recipient of support for
            command: The type of command ("Support Move" or "Support Hold")
            phase: The phase to check
        
        Returns:
            A dictionary containing information about the recipient of support, or None if no such recipient exists
        """
        if "Support" in command:
            recipient_location = re.match(rf"{UNIT_IDENTIFIER} S [AF] ({PLACE_IDENTIFIER})", unit_order).group(1)
            recipient_country = find_owner_of_unit(recipient_location, phase)
            # there should only ever be one unit at a given location during a phase
            recipient_order_info = all_orders_ever[(all_orders_ever["country"] == recipient_country) & 
                                                (all_orders_ever["phase"] == phase) & 
                                                (all_orders_ever["unit_location"] == recipient_location)].iloc[0]
            return {"recipient_unit_owner": recipient_country, "recipient_unit_outcome": recipient_order_info["immediate_result"],
                    "recipient_unit_in_anothers_territory": recipient_order_info["in_anothers_territory"],
                    "recipient_unit_moving_into_anothers_territory": recipient_order_info["moving_into_anothers_territory"],
                    "recipient_unit_destination_occupied": recipient_order_info["destination_was_occupied"]}

    support_recipient_info = all_orders_ever.apply(lambda row: find_support_recipient_info(row["order"], 
                                                                                           row["command"], 
                                                                                           row["phase"]), axis=1).apply(pd.Series)
    # add support recipient info to all_orders_ever as additional columns
    all_orders_ever = pd.concat([all_orders_ever, support_recipient_info], axis=1)

    # add relationships with other countries
    # if original v1
    agent_relationship_matrix_over_time = {}
    for phase in lmvs_data["phases"]:
        agent_relationship_matrix_over_time[phase["name"]] = pd.DataFrame(phase.get("agent_relationships", {}))
    longform_relationships = pd.concat(agent_relationship_matrix_over_time).reset_index(names=["phase", "agent"])
    
    if longform_relationships.empty:
        # Then we have v2 of the data log where relationships are stored under state_agents and need a different approach
        agent_relationship_matrix_over_time = {}
        for phase in lmvs_data["phases"]:
            agent_state = phase.get("state_agents", {}) 
            country_relationships = {}
            for c in COUNTRIES:
                country_relationships[c] = agent_state.get(c, {}).get("relationships", {})
            agent_relationship_matrix_over_time[phase["name"]] = pd.DataFrame(country_relationships)
        longform_relationships = pd.concat(agent_relationship_matrix_over_time).reset_index(names=["phase", "agent"])
   
   
    longform_relationships.columns = longform_relationships.columns.str.lower()
    longform_relationships[['austria', 'england', 'france', 'germany', 'italy',
        'russia', 'turkey']] = longform_relationships[['austria', 'england', 'france', 'germany', 'italy',
        'russia', 'turkey']].fillna("Self") 
    longform_relationships = longform_relationships.add_prefix("relationship_")
    all_orders_ever = pd.merge(all_orders_ever, longform_relationships, 
            left_on=["phase", "country"], right_on=["relationship_phase", "relationship_agent"]).drop(columns=["relationship_phase", "relationship_agent"])
    
    alternate_relationship_view = pd.concat(agent_relationship_matrix_over_time)
    alternate_relationship_view.index.names = ["phase", "agent"]
    alternate_relationship_view = alternate_relationship_view.stack().reset_index().rename(columns={"level_2":"recipient",
            0:"status"}).set_index(["phase", "recipient", 
            "agent"])["status"].unstack("agent").fillna("Self").add_suffix("s_relationship_rating").reset_index()
    all_orders_ever = pd.merge(all_orders_ever, alternate_relationship_view, 
            left_on=["phase", "country"], right_on=["phase", "recipient"]).drop(columns=["recipient"])

    # if action was supporting, add flags
    all_orders_ever["supporting_self"] = all_orders_ever["country"]==all_orders_ever["recipient_unit_owner"]
    all_orders_ever["supporting_an_ally"] = (all_orders_ever["country"] !=all_orders_ever["recipient_unit_owner"]) & (all_orders_ever["recipient_unit_owner"].notnull())

    def countries_aside_from(a_country : str) -> List[str]:
        return [country for country in all_orders_ever["country"].unique() if country != a_country]

    def check_country(supporters : List[str], country : str) -> bool:
        """
        Helper - checks if a given country is in a list of supporters
        
        Args:
            supporters: The list of supporters to check
            country: The country to check
        
        Returns:
            True if the country is in the list of supporters, False otherwise
        """
        if pd.isnull(supporters):
            return False
        for other_countries in countries_aside_from(country):
            if other_countries in supporters:
                return True
        return False

    # helpers
    all_orders_ever["was_supported"] = all_orders_ever["supported_by"].notnull()
    all_orders_ever["supported_by_self"] = all_orders_ever.apply(lambda x: x["country"] in x["supported_by"] if pd.notnull(x["supported_by"]) else False, axis=1)
    all_orders_ever["supported_by_other"] = all_orders_ever.apply(lambda x: check_country(x["supported_by"], x["country"]), axis=1)

    all_orders_ever["destination_unit_was_supported"] = all_orders_ever["destination_unit_supported_by"].notnull()

    # add number of unit orders ever made during this game
    unit_order_weight = 1 / all_orders_ever.groupby("country").size()
    all_orders_ever["unit_order_weight"] = all_orders_ever["country"].map(unit_order_weight)

    # Get llm order planning
    order_generations = all_responses[all_responses["response_type"] == "order_generation"].copy()
    order_reasoning_details = order_generations[["power", "phase", "raw_response", "success"]].copy()
    
    extracted_order_reasoning = order_reasoning_details["raw_response"].fillna("").apply(lambda x: pd.Series(re.split("parsable output", x, flags=re.IGNORECASE)))

    order_reasoning_details.loc[:, "reasoning"] = extracted_order_reasoning.loc[:, 0]
    if len(extracted_order_reasoning.columns) > 1:
        order_reasoning_details.loc[:, "unformatted_orders"] = extracted_order_reasoning.loc[:, 1:].fillna("").apply(lambda x: "\n".join(x), axis=1)
    else:
        order_reasoning_details.loc[:, "unformatted_orders"] = ""
    order_reasoning_details["reasoning_length"] = order_reasoning_details["reasoning"].str.split(" ").apply(len)

    all_orders_ever = pd.merge(all_orders_ever,
                            order_reasoning_details.rename(columns={"success":"automated_order_extraction_status"}), 
                            left_on=["country", "phase"], right_on=["power", "phase"], how="left").drop(columns=["power"])
    return all_orders_ever

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create longform order data from diplomacy game logs.")
    
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
        help="Game data analysis folder to make the orders_data folder and save the output CSV files."
    )

    args = parser.parse_args()
    

    current_game_data_folder = Path(args.game_data_folder)
    analysis_folder = Path(args.analysis_folder) / "orders_data" 

    if not analysis_folder.exists():
        print(f"Output folder {analysis_folder} not found, creating it.")
        analysis_folder.mkdir(parents=True, exist_ok=True)

    games_to_process = args.selected_game
    if not games_to_process:
        games_to_process = [p.name for p in current_game_data_folder.iterdir() if p.is_dir()]

    for game_name in tqdm(games_to_process, desc="Processing games"):
        game_path = current_game_data_folder / game_name
        if not game_path.is_dir():
            continue

        try:
            game_source_data = process_standard_game_inputs(game_path)
            overview_df = game_source_data["overview"]
            country_to_model = get_country_to_model_mapping(overview_df, game_source_data["all_responses"])
            data = make_longform_order_data(country_to_model=country_to_model,
                                            lmvs_data=game_source_data["lmvs_data"],
                                            all_responses=game_source_data["all_responses"])
            output_path = analysis_folder / f"{game_name}_orders_data.csv"
            data.to_csv(output_path, index=False)
        except FileNotFoundError as e:
            print(f"Could not process {game_name}. Missing file: {e.filename}")
        except Exception as e:
            print(f"An unexpected error occurred while processing {game_name}: {e}")
            traceback.print_exc()