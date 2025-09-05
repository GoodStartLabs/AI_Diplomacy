"""
Make conversation data from diplomacy game logs, for convenience in analyzing conversationd data alone.

Resulting columns: 
['phase',
 'party_1', (country name)
 'party_1_model', (model name)
 'party_1_opinion', (opinion of party 2, "Ally", "Enemy", "Neutral" etc)
 'party_2', (country name)
 'party_2_model', (model name)
 'party_2_opinion', (opinion of party 1)
 'party_1_messages_count', (number of messages from party 1)
 'party_1_messages_streak', (number of consecutive messages from party 1)
 'party_2_messages_count', (number of messages from party 2)
 'party_2_messages_streak', (number of consecutive messages from party 2)
 'party_1_messages_text', (text of messages from party 1 alone)
 'party_2_messages_text', (text of messages from party 2)
 'transcript' # formatted transcript of conversation
 ]
"""
import pandas as pd
import itertools 
import argparse

from tqdm import tqdm
from pathlib import Path
from analysis.analysis_helpers import COUNTRIES, process_standard_game_inputs, get_country_to_model_mapping
import traceback

def make_conversation_data(country_to_model : pd.Series, lmvs_data : pd.DataFrame) -> pd.DataFrame:
    """
    Make conversation data from diplomacy game logs.
    
    Args:
        country_to_model: A Series mapping country names to model names
        lmvs_data: A DataFrame containing the game data
    
    Returns:
        A DataFrame containing the conversation data (a row for every conversation between 2 powers, at every phase)
    """
    COUNTRY_COMBINATIONS = list(itertools.combinations(COUNTRIES, r=2))
    
    # relationship data
    agent_relationship_matrix_over_time = {}
    for phase in lmvs_data["phases"]:
        agent_relationship_matrix_over_time[phase["name"]] = pd.DataFrame(phase.get("agent_relationships", {}))

    longform_relationships = pd.concat(agent_relationship_matrix_over_time).reset_index(names=["phase", "agent"])

    all_conversations = {}
    for phase in lmvs_data["phases"]:
        current_phase = phase["name"]
        phase_conversation_data = []
        for sender, recipient in COUNTRY_COMBINATIONS:
            # Make conversation data 
            messages_dataframe = pd.DataFrame(phase["messages"])
            if messages_dataframe.empty:
                continue
            exchange_condition = ((messages_dataframe["sender"]==sender) & (messages_dataframe["recipient"]==recipient)) | ((messages_dataframe["sender"]==recipient) & (messages_dataframe["recipient"]==sender))

            messages_exchanged = messages_dataframe[exchange_condition].copy()

            messages_exchanged["message"] = messages_exchanged["message"].str.replace(r"\s+", " ", regex=True).copy()
            messages_exchanged["new_sender"] = messages_exchanged["sender"] != messages_exchanged["sender"].shift(1).copy()
            messages_exchanged["message_group"] = messages_exchanged["new_sender"].cumsum().copy()

            # Count messages in each group
            consecutive_counts = messages_exchanged.groupby(['message_group', 'sender']).size().reset_index(name='consecutive_count')

            # Get maximum consecutive messages for each sender
            max_consecutive = consecutive_counts.groupby('sender')['consecutive_count'].max()

            formatted_str = "" 
            for i, row in messages_exchanged.iterrows():
                formatted_str += f"{row['sender']}: {row['message']}\n\n"
                
            messages_from_sender = (messages_exchanged['sender']==sender).sum()
            sender_streak = max_consecutive[sender] if sender in max_consecutive.index else 0
            messages_from_recipient = (messages_exchanged['sender'] == recipient).sum()
            recipient_streak = max_consecutive.get(recipient, 0)
            party_1_opinion_series = longform_relationships[(longform_relationships["phase"] == current_phase) & (longform_relationships["agent"] == sender)].reindex(columns=[recipient])
            party_1_opinion = party_1_opinion_series.iloc[0,0] if not party_1_opinion_series.empty else ""
            party_2_opinion_series = longform_relationships[(longform_relationships["phase"] == current_phase) & (longform_relationships["agent"] == recipient)].reindex(columns=[sender])
            party_2_opinion = party_2_opinion_series.iloc[0,0] if not party_2_opinion_series.empty else ""

            conversation_data = {
                "party_1": sender,
                "party_1_model": country_to_model[sender],
                "party_1_opinion": party_1_opinion,
                "party_2": recipient,
                "party_2_model": country_to_model[recipient],
                "party_2_opinion": party_2_opinion,
                "party_1_messages_count": messages_from_sender,
                "party_1_messages_streak": sender_streak,
                "party_2_messages_count": messages_from_recipient,
                "party_2_messages_streak": recipient_streak,
                "party_1_messages_text": "\n\n".join(messages_exchanged[messages_exchanged['sender']==sender]['message'].to_list()),
                "party_2_messages_text": "\n\n".join(messages_exchanged[messages_exchanged['sender']==recipient]['message'].to_list()),
                "transcript": formatted_str
            }
            phase_conversation_data.append(conversation_data)
        all_conversations[current_phase] = pd.DataFrame(phase_conversation_data)

    all_conversations = pd.concat(all_conversations).reset_index().rename(columns={"level_0":"phase"}).drop(
        columns="level_1"
    )
    return all_conversations

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create longform conversation data from diplomacy game logs.")
    
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
        help="The folder to save the output CSV files."
    )

    args = parser.parse_args()

    current_game_data_folder = Path(args.game_data_folder)
    analysis_folder = Path(args.analysis_folder) / "conversations_data"

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
            game_data = process_standard_game_inputs(game_path)
            overview_df = game_data["overview"]
            country_to_model = get_country_to_model_mapping(overview_df, game_data["all_responses"])
            data = make_conversation_data(country_to_model=country_to_model,
                                          lmvs_data=game_data["lmvs_data"])
            output_path = analysis_folder / f"{game_name}_conversations_data.csv"
            data.to_csv(output_path, index=False)
        except FileNotFoundError as e:
            print(f"Could not process {game_name}. Missing file: {e.filename}")
        except Exception as e:
            print(f"An unexpected error occurred while processing {game_name}: {e}")
            print(f"Skipping {game_name}.")
            traceback.print_exc()