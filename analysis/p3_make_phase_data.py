"""
Build on existing orders and conversation data, as well as logs, to make detailed data by power and phase concerning state and actions.

'phase', (S1901M, etc)
'power', (country name)
'model', (model name)
'centers', (list of supply centers currently owned)
'influence', (list of territories under influence)
'units', (list of units in [A|F] [province] format)
'orders', (list of orders given)
'relationship_to_austria' (as rated Friendly/Neutral/Enemy etc)
'relationship_to_england' (as rated Friendly/Neutral/Enemy etc)
'relationship_to_france' (as rated Friendly/Neutral/Enemy etc)
'relationship_to_germany' (as rated Friendly/Neutral/Enemy etc)
'relationship_to_italy' (as rated Friendly/Neutral/Enemy etc)
'relationship_to_russia' (as rated Friendly/Neutral/Enemy etc)
'relationship_to_turkey' (as rated Friendly/Neutral/Enemy etc)
'centers_count', (number of supply centers currently owned)
'units_count', (number of units currently owned)
'armies_count', (number of armies currently owned)
'fleet_count', (number of fleets currently owned)
'influence_count', (number of territories under influence)
'phase_year', (1901, etc)
'season', (M, S, etc)
'phase_section', (last character of phase name, M, F, etc)
'centers_change', (number of supply centers gained/lost since last M phase)
'units_change', (number of units gained/lost since last M phase)
'armies_change', (number of armies gained/lost since last M phase)
'fleet_change', (number of fleets gained/lost since last M phase)
'influence_change', (number of territories under influence gained/lost since last M phase)
'conversation_england', (transcript of conversation with England if any)
'conversation_france', (transcript of conversation with France if any)
'conversation_germany', (transcript of conversation with Germany if any)
'conversation_italy', (transcript of conversation with Italy if any)
'conversation_russia', (transcript of conversation with Russia if any)
'conversation_turkey', (transcript of conversation with Turkey if any)
'conversation_austria', (transcript of conversation with Austria if any)
'count_build_commands', (number of build commands given)
'count_convoy_commands', (number of convoy commands given)
'count_disband_commands', (number of disband commands given)
'count_hold_commands', (number of hold commands given)
'count_move_commands', (number of move commands given)
'count_retreat_commands', (number of retreat commands given)
'count_support hold_commands', (number of support hold commands given)
'count_support move_commands', (number of support move commands given)
'count_got_bounce', (number of bounce results)
'count_got_bounce/dislodged', (number of bounce/dislodged results)
'count_got_cut', (number of cut results)
'count_got_cut/dislodged', (number of cut/dislodged results)
'count_got_disband', (number of disband results)
'count_got_dislodged', (number of dislodged results)
'count_got_pass', (number of pass results)
'count_got_void', (number of void results)
'count_got_void/disband', (number of void/disband results)
'count_got_void/dislodged', (number of void/dislodged results)
etc (a lot of possible combinations here)
'count_moves_into_own_territory', (number of moves into own territory)
'count_moves_into_another_territory', (number of moves into another territory)
'count_territories_gained', (number of territories gained)
'list_took_territory_from', (list of countries territory was taken from, "UNOWNED" if was neutral)
'count_supply_centers_gained', (number of supply centers gained)
'list_took_supply_centers_from', (list of countries supply centers were taken from)
'list_countries_supported', (list of countries supported)
'list_countries_attacked', (list of countries attacked)
'count_supported_self', (number of times supported self)
'count_supported_other', (number of times supported another power)
'count_was_supported_by_other', (number of times got supported by another power)
'list_was_supported_by', (list of countries that supported this power)
'raw_order_generation_response', (raw output from order query)
'automated_order_extraction_status', (success/error message for order extraction)
'order_reasoning', (free-text reasoning extracted from response)
'unformatted_order_response', (raw orders partially extracted from response)
'order_reasoning_length', (length of reasoning in generating orders)
'invalid_order_count', (number of invalid orders given)
'no_moves_extracted_flag', (flag for if no moves were extracted)
'valid_order_count', (number of valid orders, calculated as unit_count - invalid_order_count, unless no valid orders were extracted )
'goals', (list of goals for the phase separated by \n\n)
'diary', (diary entry for the phase)
"""

import pandas as pd
import numpy as np

import json 
import copy
import re 
import argparse
from pathlib import Path
from analysis.analysis_helpers import process_standard_game_inputs, get_country_to_model_mapping
from analysis.schemas import COUNTRIES
from tqdm import tqdm
import traceback 

def make_phase_data(country_to_model : pd.Series, 
                    lmvs_data : pd.DataFrame, 
                    conversations_data : pd.DataFrame, 
                    orders_data : pd.DataFrame) -> pd.DataFrame:
    """
    takes country-to-model mapping, game state (lmvs_data), conversations, and orders, and returns a dataframe with one row per (power, phase). 
    
    Args:
        country_to_model: mapping of country to model
        lmvs_data: raw lmvs_data dataframe
        conversations_data: dataframe of conversations
        orders_data: dataframe of orders
        
    Returns:
        dataframe with one row per (power, phase) containing phase-level features, convos, relationships, and orders info. 
    """

    longform_conversations_complete = []
    for c in COUNTRIES: 
        subset_party_1 = conversations_data[(conversations_data["party_1"]==c)][["party_1", "party_2", 
                                            "phase", "transcript"]].rename(columns={"party_1": "agent", "party_2": "other_country"})
        subset_party_2 = conversations_data[(conversations_data["party_2"]==c)][["party_2", "party_1", 
                                            "phase", "transcript"]].rename(columns={"party_2": "agent", "party_1": "other_country"})
        my_convos = pd.concat([subset_party_1, subset_party_2]).set_index(["agent", "phase", "other_country"])["transcript"].unstack().add_prefix("conversation_")
        
        longform_conversations_complete.append(my_convos)

    longform_conversations_complete = pd.concat(longform_conversations_complete).reset_index().rename(
            columns={"agent":"power"})
    longform_conversations_complete.index.name = ""

    ############ Relationships #############
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

    ########### ORDERS DATA ###########
    # adding results to lmvs

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
        orders_over_time.append(pd.Series(phase_orders).rename(phase["name"]))
    orders_over_time = pd.concat(orders_over_time, axis=1).T



    # some additional features for summary
    orders_data["move_was_successful"] = (orders_data["command"]=="Move") & (orders_data["immediate_result"] == "PASS")
    orders_data["took_location"] = orders_data["move_was_successful"] & orders_data["moving_into_anothers_territory"]
    orders_data["move_took_location_from"] = np.where(orders_data["took_location"], orders_data["destination_affiliation"], np.nan)
    orders_data["move_took_sc"] = orders_data["took_location"] & orders_data["destination_was_sc"]
    orders_data["move_took_sc_from"] = np.where(orders_data["move_took_sc"], orders_data["destination_affiliation"], np.nan)

    orders_data["defendant_country"] = np.where(orders_data["destination_affiliation"] != orders_data["country"], 
                                                orders_data["destination_affiliation"], np.nan)

    
    # orders reasoning 
    order_reasoning_by_phase = orders_data[['phase', 'country', 'raw_response',
       'automated_order_extraction_status', 'reasoning', 'unformatted_orders',
       'reasoning_length']].drop_duplicates().rename(columns={
           "country": "power",
           "raw_response": "raw_order_generation_response",
           "reasoning": "order_reasoning",
           "unformatted_orders": "unformatted_order_response",
           "reasoning_length": "order_reasoning_length",
       })
    order_reasoning_by_phase["invalid_order_count"] = pd.to_numeric(order_reasoning_by_phase["automated_order_extraction_status"].str.extract(r"Failure: Invalid LLM Moves (\d+)", 
                                                                                                                                              expand=False), errors="coerce").fillna(0)
    order_reasoning_by_phase["no_moves_extracted_flag"] = order_reasoning_by_phase["automated_order_extraction_status"].str.contains("No moves extracted")
    
    
    
    # phase level summaries for orders
    commands_given = orders_data.groupby(["country", "phase"])["command"].value_counts()
    immediate_outcomes = orders_data.groupby(["country", "phase"])["immediate_result"].value_counts()
    # units in own territory
    orders_data["moving_in_own_territory"] = orders_data["destination_affiliation"]==orders_data["country"]
    orders_data["moving_into_anothers_territory"] = orders_data["destination_affiliation"]!=orders_data["country"]

    moves_in_own_territory = orders_data.groupby(["country", "phase"])["moving_in_own_territory"].sum()
    moves_into_other_territory = orders_data.groupby(["country", "phase"])["moving_into_anothers_territory"].sum()

    gained_territory = orders_data.groupby(["country", "phase"])["took_location"].sum()
    took_territory_from = orders_data.groupby(["country", "phase"])["move_took_location_from"].apply(lambda x: x.dropna().tolist())

    count_lost_territory = orders_data.groupby(["move_took_location_from", "phase"]).size()
    lost_territory_to = orders_data.groupby(["move_took_location_from", "phase"])["country"].apply(lambda x: x.dropna().tolist())
    lost_territory_to.index.names = ["country", "phase"]

    supply_centers_gained = orders_data.groupby(["country", "phase"])["move_took_sc"].sum()
    supply_centers_taken_from = orders_data.groupby(["country", "phase"])["move_took_sc_from"].apply(lambda x: x.dropna().tolist())

    supply_centers_lost = orders_data.groupby(["move_took_sc_from", "phase"]).size()

    supply_centers_taken_by = orders_data.groupby(["move_took_sc_from", "phase"])["country"].apply(lambda x: x.dropna().tolist())
    supply_centers_taken_by.index.names = ["country", "phase"]

    supported_self = orders_data.groupby(["country", "phase"])["supporting_self"].sum()
    supported_other = orders_data.groupby(["country", "phase"])["supporting_an_ally"].sum()
    was_supported_by_self = orders_data.groupby(["country", "phase"])["supported_by_self"].sum()
    was_supported_by_other = orders_data.groupby(["country", "phase"])["supported_by_other"].sum()

    countries_supported = orders_data.groupby(["country", "phase"])["recipient_unit_owner"].apply(lambda x: x.dropna().tolist())
    got_supported_by = orders_data.groupby(["country", "phase"])["supported_by"].apply(lambda x: x.dropna().tolist())
    countries_attacked = orders_data.groupby(["country", "phase"])["defendant_country"].apply(lambda x: x.dropna().tolist())
    # lost a supply center


    # territories held, territories moved to

    orders_summary = pd.concat([commands_given.unstack().add_prefix("count_").add_suffix("_commands"), 
                                immediate_outcomes.unstack().add_prefix("count_got_"),
                                moves_in_own_territory.rename("count_moves_into_own_territory"), 
                                moves_into_other_territory.rename("count_moves_into_another_territory"), 
                                
                                gained_territory.rename("count_territories_gained"),
                                took_territory_from.rename("list_took_territory_from"),
                                count_lost_territory.rename("count_territories_lost"),
                                lost_territory_to.rename("list_lost_territory_to"),
                                
                                supply_centers_gained.rename("count_supply_centers_gained"), 
                                supply_centers_taken_from.rename("list_took_supply_centers_from"),
                                
                                supply_centers_lost.rename("count_supply_centers_lost"),
                                supply_centers_taken_by.rename("list_lost_supply_centers_to"),
                                
                                countries_supported.rename("list_countries_supported"),
                                countries_attacked.rename("list_countries_attacked"),
                                
                                supported_self.rename("count_supported_self"),
                                supported_other.rename("count_supported_other"),
                                got_supported_by.rename("list_was_supported_by"),
                                was_supported_by_other.rename("count_was_supported_by_other"),
                                was_supported_by_self.rename("count_was_supported_by_self"),
                                ], axis=1)

    orders_summary.columns = orders_summary.columns.str.lower() 
    orders_summary.loc[:, orders_summary.columns.str.contains("count")] = orders_summary.loc[:, orders_summary.columns.str.contains("count")].fillna(0)
    orders_summary.loc[:, orders_summary.columns.str.contains("list")] = orders_summary.loc[:, orders_summary.columns.str.contains("list")].map(lambda x: ", ".join(x) if isinstance(x, list) else "").replace("", np.nan)

    state_list = {}
    for phase in lmvs_data["phases"]:
        state_list[phase["name"]] = []
        for var in ["centers", "influence", "units"]:
            state_list[phase["name"]].append(pd.DataFrame(pd.Series(phase["state"][var])).rename(columns={0:var}))
        state_list[phase["name"]].append(orders_over_time.loc[phase["name"]].rename("orders"))
        state_list[phase["name"]] = pd.concat(state_list[phase["name"]], axis=1)
            
    # goals and diaries        
    goals_over_time = {}
    diary_over_time = {}
    for phase in lmvs_data["phases"]:
        agent_state = phase.get("state_agents", {}) 
        if agent_state: # Not all versions have this
            country_goals = {}
            country_diary = {}
            for c in COUNTRIES:
                country_goals[c] = "\n\n".join(agent_state.get(c, {}).get("goals", {}))
                country_diary[c] = "\n\n".join(agent_state.get(c, {}).get("full_private_diary", []))
            goals_over_time[phase["name"]] = pd.Series(country_goals)
            diary_over_time[phase["name"]] = pd.Series(country_diary)

    state_list = pd.concat(state_list, axis=0)
    state_list.index.names = ["phase", "agent"]
    if goals_over_time:
        goals_over_time = pd.DataFrame(goals_over_time).T.stack().reset_index().rename(columns={"level_0":"phase", "level_1":"agent", 0:"goal"}).set_index(["phase", "agent"])
        state_list = pd.concat([state_list, goals_over_time], axis=1)
    if diary_over_time:
        diary_over_time = pd.DataFrame(diary_over_time).T.stack().reset_index().rename(columns={"level_0":"phase", "level_1":"agent", 0:"diary"}).set_index(["phase", "agent"])
        state_list = pd.concat([state_list, diary_over_time], axis=1)
        
    longform_relationships = longform_relationships.set_index(["relationship_phase", "relationship_agent"])
    longform_relationships.index.names = ["phase", "agent"]
    full_phase_data = pd.merge(state_list, 
                            longform_relationships,
                            left_index=True, right_index=True).reset_index()
    full_phase_data["centers_count"] = full_phase_data["centers"].apply(lambda x: len(x))
    full_phase_data["units_count"] = full_phase_data["units"].apply(lambda x: len(x))
    full_phase_data["armies_count"] = full_phase_data["units"].apply(lambda x: sum(e[0]=="A" for e in x))
    full_phase_data["fleet_count"] = full_phase_data["units"].apply(lambda x: sum(e[0]=="F" for e in x))
    full_phase_data["influence_count"] = full_phase_data["influence"].apply(lambda x: len(x))

    full_phase_data["phase_year"] = full_phase_data["phase"].str[1:5]
    full_phase_data["season"] = full_phase_data["phase"].str[0]
    full_phase_data["phase_section"] = full_phase_data["phase"].str[-1]

    full_phase_data[["centers_change", "units_change", "armies_change", "fleet_change","influence_change"]] = full_phase_data[full_phase_data["phase_section"]=="M"].groupby("agent")[["centers_count",
                                                                            "units_count",
                                                                            "armies_count",
                                                                            "fleet_count",
                                                                            "influence_count"]].diff()

    full_phase_data = pd.merge(full_phase_data, longform_conversations_complete, 
                               left_on=["phase", "agent"], right_on=["phase", "power"])
    full_phase_data = pd.merge(full_phase_data, orders_summary, how="left", left_on=["power", "phase"],
                               right_index=True)
    full_phase_data["model"] = full_phase_data["power"].map(country_to_model)
    
    full_phase_data = pd.merge(full_phase_data, order_reasoning_by_phase, how="left", 
                               on=["phase", "power"])
    full_phase_data["valid_order_count"] = full_phase_data["units_count"] - full_phase_data["invalid_order_count"]
    full_phase_data["valid_order_count"] = np.where(full_phase_data["no_moves_extracted_flag"], 0, full_phase_data["valid_order_count"])
    
    # for column naming consistency
    full_phase_data.columns = full_phase_data.columns.str.replace(" ", "_").str.lower()
    return full_phase_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create longform phase data from diplomacy game logs.")
    
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
        help="The folder where analysis data is stored."
    )

    args = parser.parse_args()

    current_game_data_folder = Path(args.game_data_folder)
    analysis_folder = Path(args.analysis_folder)
    output_folder = analysis_folder / "phase_data"

    if not output_folder.exists():
        print(f"Output folder {output_folder} not found, creating it.")
        output_folder.mkdir(parents=True, exist_ok=True)

    games_to_process = args.selected_game
    if not games_to_process:
        games_to_process = [p.name for p in current_game_data_folder.iterdir() if p.is_dir()]

    for game_name in tqdm(games_to_process):
        if game_name == ".DS_Store":
            continue
        
        game_path = current_game_data_folder / game_name
        if not game_path.is_dir():
            continue
        
        try:
            game_data = process_standard_game_inputs(game_path)
            orders_data = pd.read_csv(analysis_folder / "orders_data" / f"{game_name}_orders_data.csv")
            conversations_data = pd.read_csv(analysis_folder / "conversations_data" / f"{game_name}_conversations_data.csv")
            country_to_model = get_country_to_model_mapping(game_data["overview"], game_data["all_responses"])
            data = make_phase_data(country_to_model=country_to_model, 
                                   lmvs_data=game_data["lmvs_data"], 
                                   conversations_data=conversations_data, 
                                   orders_data=orders_data)
            output_path = output_folder / f"{game_name}_phase_data.csv"
            data.to_csv(output_path, index=False)
        except FileNotFoundError as e:
            print(f"Could not process {game_name}. Missing file: {e.filename}")
        except Exception as e:
            print(f"An unexpected error occurred while processing {game_name}: {e}")
            print(f"Skipping {game_name}.")
            traceback.print_exc()