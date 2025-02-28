import logging
import re
import os
import time
from typing import Dict, List, Optional, Tuple, Any

# Establish logger
logger = logging.getLogger(__name__)

# Import model client for summarization
from ai_diplomacy.model_loader import load_model_client

# Token counting 
try:
    import tiktoken
    ENCODER = tiktoken.get_encoding("cl100k_base")  # OpenAI's encoding for models like GPT-4/3.5
    
    def count_tokens(text: str) -> int:
        """
        Accurately counts tokens for text using tiktoken.
        Falls back to approximation if tiktoken fails.
        """
        try:
            return len(ENCODER.encode(text))
        except Exception as e:
            # Fallback to approximation
            logger.warning(f"CONTEXT | TOKEN COUNT | Error using tiktoken ({str(e)}), falling back to approximation")
            return len(text) // 4  # Simple approximation
except ImportError:
    # Fallback for environments without tiktoken
    logger.warning("CONTEXT | TOKEN COUNT | tiktoken not available, using approximate token counting")
    
    def count_tokens(text: str) -> int:
        """
        Approximates token count for text. This is a rough estimate.
        OpenAI tokens are ~4 chars per token on average.
        """
        return len(text) // 4  # Simple approximation


class ContextManager:
    """
    Manages context size for Diplomacy game history and messages.
    Provides power-specific recursive summarization functionality 
    when context exceeds thresholds.
    """
    def __init__(
        self, 
        phase_token_threshold: int = 15000,
        message_token_threshold: int = 15000,
        summary_model: str = "o3-mini"
    ):
        self.phase_token_threshold = phase_token_threshold
        self.message_token_threshold = message_token_threshold
        self.summary_model = summary_model
        
        # Per-power tracking of summary states
        self.power_summary_states = {}  # Indexed by power_name
        
        # Shared phase summary state (phases are globally visible)
        self.phase_summary_state = {
            'last_summary': None,      # The most recent summary of older phases
            'summarized_phases': [],   # List of phase names that have been summarized
            'last_summary_time': 0,    # When we last summarized
        }
        
        # Cooldown period (seconds) - don't summarize more frequently than this
        # For a game, 30 seconds is more appropriate than 5 minutes
        self.summary_cooldown = 30  # 30 seconds
        
        logger.debug(f"CONTEXT | Initialized manager with thresholds: phase={phase_token_threshold}, message={message_token_threshold} tokens")
        logger.debug(f"CONTEXT | Summary cooldown set to {self.summary_cooldown} seconds")
    
    def get_power_state(self, power_name):
        """
        Gets or initializes the summary state for a specific power.
        """
        if power_name not in self.power_summary_states:
            self.power_summary_states[power_name] = {
                'last_message_summary': None,  # The most recent message summary
                'summarized_messages': set(),  # Set of message IDs that have been summarized
                'last_summary_time': 0,        # When we last summarized messages for this power
            }
        return self.power_summary_states[power_name]
    
    def load_summarization_prompts(self) -> Tuple[str, str, str]:
        """
        Load prompts for phase, message, and recursive summarization.
        Returns tuple of (phase_prompt, message_prompt, recursive_prompt)
        """
        try:
            # Try to load from files
            with open("./ai_diplomacy/prompts/phase_summary_prompt.txt", "r") as f:
                phase_prompt = f.read().strip()
            
            with open("./ai_diplomacy/prompts/message_summary_prompt.txt", "r") as f:
                message_prompt = f.read().strip()
                
            with open("./ai_diplomacy/prompts/recursive_summary_prompt.txt", "r") as f:
                recursive_prompt = f.read().strip()
                
            logger.debug("CONTEXT | Loaded summarization prompts from files")
            return phase_prompt, message_prompt, recursive_prompt
        except FileNotFoundError:
            # Return default prompts if files not found
            logger.warning("CONTEXT | Summarization prompt files not found, using default templates")
            
            phase_prompt = """You are summarizing the history of a Diplomacy game. 
Create a concise summary that preserves all strategically relevant information about:
1. Supply center changes
2. Unit movements and their results 
3. Key battles and their outcomes
4. Territory control shifts

Focus on what actually happened, not explanations or justifications.
Maintain the chronological structure but condense verbose descriptions.
Use clear, factual language with specific location names.

ORIGINAL PHASE HISTORY:
{phase_history}

SUMMARY:"""

            message_prompt = """You are summarizing diplomatic messages in a Diplomacy game.
Create a concise summary of the conversations between powers that preserves:
1. Agreements and alliances formed
2. Betrayals and broken promises
3. Strategic intentions revealed 
4. Explicit threats or support offered
5. Key relationships between each power

Organize by relationships (e.g., FRANCE-GERMANY, ENGLAND-RUSSIA), prioritizing the most 
significant interactions. Include specific territory names mentioned.

The summary must reflect the actual diplomatic landscape accurately so players can make informed decisions.

ORIGINAL MESSAGE HISTORY:
{message_history}

SUMMARY:"""

            recursive_prompt = """You are creating a recursive summary of a Diplomacy game's history.
You have a previous summary of earlier events/messages and new content to incorporate.

Your task is to create a unified, seamless summary that:
1. Preserves key strategic information from both sources
2. Maintains chronological flow and logical structure
3. Presents the most relevant information for decision-making
4. Emphasizes developments in alliances, betrayals, and territorial control

PREVIOUS SUMMARY:
{previous_summary}

NEW CONTENT:
{new_content}

Create a unified summary that reads as a single coherent narrative while preserving critical strategic information:"""
            
            return phase_prompt, message_prompt, recursive_prompt
    
    def generate_recursive_summary(self, previous_summary, new_content, prompt_type="recursive", power_name=None):
        """
        Generates a recursive summary by combining previous summary with new content.
        
        Args:
            previous_summary: Previous summary text
            new_content: New content to be incorporated
            prompt_type: Type of prompt to use (recursive, phase, or message)
            power_name: Name of the power for context
            
        Returns:
            A new summary incorporating both previous and new content
        """
        # Load appropriate prompt
        phase_prompt, message_prompt, recursive_prompt = self.load_summarization_prompts()
        
        # Calculate token counts for logging
        new_content_tokens = count_tokens(new_content)
        prev_summary_tokens = count_tokens(previous_summary or "")
        
        if prompt_type == "phase" and not previous_summary:
            # Initial phase summary
            prompt = phase_prompt.replace("{phase_history}", new_content)
            logger.debug(f"CONTEXT | SUMMARY | Creating initial phase summary with {new_content_tokens} tokens")
            logger.info(f"CONTEXT | SUMMARY | Initializing phase summary for {len(new_content.split())} words / {new_content_tokens} tokens of game history")
        elif prompt_type == "message" and not previous_summary:
            # Initial message summary
            prompt = message_prompt.replace("{message_history}", new_content)
            logger.debug(f"CONTEXT | SUMMARY | Creating initial message summary for {power_name} with {new_content_tokens} tokens")
            logger.info(f"CONTEXT | SUMMARY | Initializing message summary for {power_name} ({new_content_tokens} tokens)")
        else:
            # Recursive summary (or phase/message with previous summary)
            prompt = recursive_prompt
            prompt = prompt.replace("{previous_summary}", previous_summary or "(No previous summary)")
            prompt = prompt.replace("{new_content}", new_content)
            
            logger.debug(f"CONTEXT | SUMMARY | Creating recursive {prompt_type} summary for {power_name or 'game'}")
            logger.debug(f"CONTEXT | SUMMARY | Previous summary: {prev_summary_tokens} tokens, New content: {new_content_tokens} tokens")
            logger.info(f"CONTEXT | SUMMARY | Recursive summarization: combining {prev_summary_tokens} tokens of previous summary with {new_content_tokens} tokens of new content")
        
        # Get the summary using the LLM
        summarization_client = load_model_client(self.summary_model, power_name=power_name, emptysystem=True)
        summary = summarization_client.generate_response(prompt)
        
        summary_tokens = count_tokens(summary)
        logger.debug(f"CONTEXT | Generated {prompt_type} recursive summary ({summary_tokens} tokens)")
        
        # Log the compression ratio
        if new_content_tokens > 0:
            if previous_summary:
                total_input_tokens = prev_summary_tokens + new_content_tokens
                compression_ratio = summary_tokens / total_input_tokens
                logger.info(f"CONTEXT | SUMMARY | Compression: {total_input_tokens} → {summary_tokens} tokens ({compression_ratio:.2f}x)")
            else:
                compression_ratio = summary_tokens / new_content_tokens
                logger.info(f"CONTEXT | SUMMARY | Compression: {new_content_tokens} → {summary_tokens} tokens ({compression_ratio:.2f}x)")
        
        return summary
    
    def should_summarize_phases(self, phase_summaries: Dict[str, str]) -> bool:
        """
        Determine if phase summaries need to be condensed based on token count,
        cooldown period, and new content since last summarization.
        """
        # Check if we're in cooldown period
        current_time = time.time()
        time_since_last = current_time - self.phase_summary_state['last_summary_time']
        
        if time_since_last < self.summary_cooldown:
            logger.debug(f"CONTEXT | Phase summarization skipped (in cooldown period, {time_since_last:.0f}s < {self.summary_cooldown}s)")
            return False
            
        # Get unsummarized phase content - exclude existing summary entries
        unsummarized_phase_names = [p for p in phase_summaries.keys() 
                                  if p not in self.phase_summary_state['summarized_phases']
                                  and not p.startswith("SUMMARY_UNTIL_")]
        
        if not unsummarized_phase_names:
            logger.debug("CONTEXT | No new phases to summarize")
            return False
        
        # If we have a previous summary, count its tokens
        base_token_count = 0
        if self.phase_summary_state['last_summary']:
            base_token_count = count_tokens(self.phase_summary_state['last_summary'])
        
        # Count tokens in unsummarized phases
        unsummarized_text = "\n\n".join([phase_summaries[phase] for phase in unsummarized_phase_names])
        unsummarized_token_count = count_tokens(unsummarized_text)
        
        # Check if total exceeds threshold
        total_token_count = base_token_count + unsummarized_token_count
        should_summarize = total_token_count > self.phase_token_threshold
        
        # Log decision details
        if should_summarize:
            logger.debug(f"CONTEXT | Phase token count ({total_token_count} tokens) exceeds threshold ({self.phase_token_threshold} tokens), will summarize")
            logger.debug(f"CONTEXT | Phase breakdown: {base_token_count} tokens from previous summary + {unsummarized_token_count} tokens from {len(unsummarized_phase_names)} new phases")
            logger.info(f"CONTEXT | THRESHOLD EXCEEDED | Phase summaries need summarization ({total_token_count} > {self.phase_token_threshold} tokens)")
        else:
            logger.debug(f"CONTEXT | Phase token count ({total_token_count} tokens) below threshold ({self.phase_token_threshold} tokens), no summarization needed")
        
        return should_summarize
    
    def should_summarize_messages(self, message_history: str, power_name: str) -> bool:
        """
        Determine if message history for a specific power needs to be condensed
        based on token count and cooldown period.
        """
        # Get power-specific state
        power_state = self.get_power_state(power_name)
        
        # Check if we're in cooldown period
        current_time = time.time()
        time_since_last = current_time - power_state['last_summary_time']
        
        if time_since_last < self.summary_cooldown:
            logger.debug(f"CONTEXT | Message summarization for {power_name} skipped (in cooldown period, {time_since_last:.0f}s < {self.summary_cooldown}s)")
            return False
            
        # Don't summarize empty history
        if not message_history or message_history == "(No history yet)" or message_history.strip() == "":
            logger.debug(f"CONTEXT | Message summarization for {power_name} skipped (empty history)")
            return False
            
        # If we have a previous summary, count its tokens
        base_token_count = 0
        if power_state['last_message_summary']:
            base_token_count = count_tokens(power_state['last_message_summary'])
        
        # Count tokens in the new content
        new_token_count = count_tokens(message_history)
        
        # Skip if this is just a template with no actual content
        if "COMMUNICATION HISTORY:" in message_history and new_token_count < 200:
            # Check if it's just headers with no actual content
            content_lines = [line for line in message_history.split("\n") 
                            if line.strip() and not line.strip().endswith(":") 
                            and "has not engaged" not in line]
            if len(content_lines) <= 2:
                logger.debug(f"CONTEXT | Message summarization for {power_name} skipped (template with no significant content)")
                return False
        
        # Check if total exceeds threshold 
        total_token_count = base_token_count + new_token_count
        should_summarize = total_token_count > self.message_token_threshold
        
        # Log decision details
        if should_summarize:
            logger.debug(f"CONTEXT | Message token count for {power_name} ({total_token_count} tokens) exceeds threshold ({self.message_token_threshold} tokens), will summarize")
            logger.debug(f"CONTEXT | Message breakdown for {power_name}: {base_token_count} tokens from previous summary + {new_token_count} tokens from new messages")
            logger.info(f"CONTEXT | THRESHOLD EXCEEDED | Messages for {power_name} need summarization ({total_token_count} > {self.message_token_threshold} tokens)")
        else:
            logger.debug(f"CONTEXT | Message token count for {power_name} ({total_token_count} tokens) below threshold ({self.message_token_threshold} tokens), no summarization needed")
            
        return should_summarize
    
    def summarize_phase_history(self, phase_summaries: Dict[str, str], power_name: Optional[str] = None) -> Dict[str, str]:
        """
        Create a recursively updated summary of phase history.
        Keeps recent phases intact and summarizes older ones.
        Always preserves the most recent phase for better context.
        
        Returns a new dictionary with condensed history.
        """
        if not self.should_summarize_phases(phase_summaries):
            return phase_summaries
            
        # Mark summarization time
        self.phase_summary_state['last_summary_time'] = time.time()
        
        # Sort phases chronologically 
        sorted_phases = sorted(phase_summaries.keys())
        
        # Get unsummarized phase names, excluding existing summary entries
        unsummarized_phase_names = [p for p in sorted_phases 
                                  if p not in self.phase_summary_state['summarized_phases']
                                  and not p.startswith("SUMMARY_UNTIL_")]
        
        # Always keep the most recent phase intact regardless of any other logic
        # Then add enough additional recent phases to have at least 2 intact phases
        most_recent_phase = max(unsummarized_phase_names) if unsummarized_phase_names else None
        
        # If we have more than 2 phases, keep the most recent plus another 1-2 for context
        if len(unsummarized_phase_names) > 2:
            recent_phases = unsummarized_phase_names[-3:] 
            logger.debug(f"CONTEXT | PHASE SUMMARIZATION | Keeping {len(recent_phases)} recent phases intact, including most recent: {most_recent_phase}")
        else:
            # If we have 2 or fewer phases, keep them all intact
            recent_phases = unsummarized_phase_names
            logger.debug(f"CONTEXT | PHASE SUMMARIZATION | Keeping all {len(recent_phases)} phases intact")
            
        phases_to_summarize = [p for p in unsummarized_phase_names if p not in recent_phases]
        
        if not phases_to_summarize:
            logger.debug("CONTEXT | PHASE SUMMARIZATION | No new phases to summarize")
            return phase_summaries  # Nothing to summarize
        
        # Log which phases we're summarizing vs keeping intact
        logger.debug(f"CONTEXT | PHASE SUMMARIZATION | Phases to summarize: {phases_to_summarize}")
        logger.debug(f"CONTEXT | PHASE SUMMARIZATION | Recent phases to keep intact: {recent_phases}")
        
        # Text to summarize: previous summary + new phases to summarize
        previous_summary = self.phase_summary_state['last_summary'] or ""
        
        # Generate content only from phases being summarized (not already in a summary)
        new_content = ""
        for phase in phases_to_summarize:
            new_content += f"PHASE {phase}:\n{phase_summaries[phase]}\n\n"
        
        # Log before summarization - include token counts for clarity
        new_content_tokens = count_tokens(new_content)
        prev_summary_tokens = count_tokens(previous_summary) if previous_summary else 0
        
        logger.info(f"CONTEXT | PHASE SUMMARIZATION | Starting recursive summarization for {len(phases_to_summarize)} phases")
        logger.info(f"CONTEXT | PHASE SUMMARIZATION | Phases being summarized: {', '.join(phases_to_summarize)}")
        logger.info(f"CONTEXT | PHASE SUMMARIZATION | Content size: {new_content_tokens} tokens from new phases + {prev_summary_tokens} tokens from previous summary")
        
        # Generate recursive summary
        if previous_summary:
            # We have a previous summary, do recursive summarization
            logger.debug(f"CONTEXT | PHASE SUMMARIZATION | Performing recursive summarization with previous summary ({prev_summary_tokens} tokens)")
            summary = self.generate_recursive_summary(
                previous_summary, 
                new_content,
                prompt_type="recursive", 
                power_name=power_name
            )
        else:
            # No previous summary, do initial summarization
            logger.debug(f"CONTEXT | PHASE SUMMARIZATION | Performing initial phase summarization ({new_content_tokens} tokens)")
            summary = self.generate_recursive_summary(
                None,
                new_content,
                prompt_type="phase",
                power_name=power_name
            )
        
        # Update phase summary state
        self.phase_summary_state['last_summary'] = summary
        # Track which phases have been summarized
        for phase in phases_to_summarize:
            if phase not in self.phase_summary_state['summarized_phases']:
                self.phase_summary_state['summarized_phases'].append(phase)
        
        # Log the current summarization state
        logger.debug(f"CONTEXT | PHASE SUMMARIZATION | Updated summarized_phases list: now contains {len(self.phase_summary_state['summarized_phases'])} phases")
        
        # Create new dictionary with summarized older phases and intact recent phases
        result = {}
        
        # Include any existing summaries that were in the input but aren't being updated
        for key in phase_summaries:
            if key.startswith("SUMMARY_UNTIL_") and key not in result:
                # Only keep summaries that don't overlap with our new summary
                if not any(phase in key for phase in phases_to_summarize):
                    result[key] = phase_summaries[key]
                    logger.debug(f"CONTEXT | PHASE SUMMARIZATION | Preserved existing summary: {key}")
        
        # Add the new summary as a special entry
        if phases_to_summarize:
            last_summarized = max(phases_to_summarize)
            summary_key = f"SUMMARY_UNTIL_{last_summarized}"
            result[summary_key] = summary
            summary_tokens = count_tokens(summary)
            logger.info(f"CONTEXT | PHASE SUMMARIZATION | Created summary key '{summary_key}' ({summary_tokens} tokens)")
        
        # Add the recent phases as-is
        for phase in recent_phases:
            result[phase] = phase_summaries[phase]
            logger.debug(f"CONTEXT | PHASE SUMMARIZATION | Preserved recent phase: {phase}")
        
        # Add any regular phases that weren't summarized and weren't in recent_phases
        for phase in phase_summaries:
            if (not phase.startswith("SUMMARY_UNTIL_") and 
                phase not in phases_to_summarize and 
                phase not in recent_phases and
                phase not in result):
                result[phase] = phase_summaries[phase]
                logger.debug(f"CONTEXT | PHASE SUMMARIZATION | Preserved other phase: {phase}")
        
        # Log summarization metrics
        orig_phases = len([p for p in phase_summaries if not p.startswith("SUMMARY_UNTIL_")])
        new_phases = len([p for p in result if not p.startswith("SUMMARY_UNTIL_")])
        orig_summaries = len([p for p in phase_summaries if p.startswith("SUMMARY_UNTIL_")])
        new_summaries = len([p for p in result if p.startswith("SUMMARY_UNTIL_")])
        
        logger.info(f"CONTEXT | PHASE SUMMARIZATION | Original: {orig_phases} phases + {orig_summaries} summaries → New: {new_phases} phases + {new_summaries} summaries")
        logger.debug(f"CONTEXT | PHASE SUMMARIZATION | Result contains {new_summaries} summaries + {len(recent_phases)} intact recent phases + {new_phases - len(recent_phases)} other preserved phases")
        
        # Verify the most recent phase is preserved
        if most_recent_phase and most_recent_phase not in result:
            logger.warning(f"CONTEXT | PHASE SUMMARIZATION | Most recent phase {most_recent_phase} not in result! Adding it back.")
            result[most_recent_phase] = phase_summaries[most_recent_phase]
        
        # Log token sizes for before and after
        orig_tokens = sum(count_tokens(v) for v in phase_summaries.values())
        new_tokens = sum(count_tokens(v) for v in result.values())
        token_reduction = (orig_tokens - new_tokens) / orig_tokens * 100 if orig_tokens > 0 else 0
        
        logger.info(f"CONTEXT | PHASE SUMMARIZATION | Token reduction: {orig_tokens} → {new_tokens} tokens ({token_reduction:.1f}% reduction)")
        
        return result
    
    def summarize_message_history(
        self, 
        message_history: str, 
        power_name: str,
        organized_by_relationship: bool = True
    ) -> str:
        """
        Create a recursively updated summary of message history for a specific power.
        Preserves raw messages from the most recent turn while summarizing older content.
        
        Args:
            message_history: Current unsummarized message history
            power_name: The power whose history is being summarized
            organized_by_relationship: If True, assumes messages are organized by relationship
            
        Returns:
            Updated message history with recursive summarization applied
        """
        # Get power-specific state
        power_state = self.get_power_state(power_name)
        
        # Check if we need to summarize
        if not self.should_summarize_messages(message_history, power_name):
            # If we have a previous summary but are below threshold, we can still use the previous summary
            if power_state['last_message_summary'] and message_history:
                prev_summary = power_state['last_message_summary']
                prev_summary_tokens = count_tokens(prev_summary)
                message_tokens = count_tokens(message_history)
                
                # Only use previous summary if it's significantly smaller than the raw history
                if prev_summary_tokens < (message_tokens * 0.7):  # 30% reduction threshold
                    logger.info(f"CONTEXT | MESSAGE SUMMARIZATION | {power_name} | Using existing summary ({prev_summary_tokens} tokens) instead of raw history ({message_tokens} tokens)")
                    return prev_summary
            
            logger.debug(f"CONTEXT | MESSAGE SUMMARIZATION | No summarization needed for {power_name}, using original history")
            return message_history
        
        # Defensive check for empty content
        if not message_history or message_history.strip() == "":
            logger.warning(f"CONTEXT | MESSAGE SUMMARIZATION | Empty message history for {power_name}")
            return "(No message history available)"
            
        # Mark summarization time
        power_state['last_summary_time'] = time.time()
        
        # Log before summarization with token counts
        message_tokens = count_tokens(message_history)
        logger.info(f"CONTEXT | MESSAGE SUMMARIZATION | Starting message summarization for {power_name}")
        logger.info(f"CONTEXT | MESSAGE SUMMARIZATION | Current message history size: {message_tokens} tokens")
        
        # Extract and preserve the most recent turn's messages
        recent_turn_messages = ""
        remaining_history = message_history
        
        # Try to identify and extract the most recent turn's messages
        if organized_by_relationship:
            # For relationship-organized history, try to extract the latest communication sections
            # Look for power relationship headers like "FRANCE-GERMANY:" or timestamp markers
            
            # First, look for a timestamp pattern to identify the most recent turn
            time_pattern = r"\[([0-9]{2}:[0-9]{2}:[0-9]{2})\]|\(([0-9]{2}:[0-9]{2}:[0-9]{2})\)"
            timestamps = re.findall(time_pattern, message_history)
            
            if timestamps:
                # If we found timestamps, try to identify the latest message blocks
                # Convert the flat string into lines for easier processing
                lines = message_history.split('\n')
                section_starts = []
                
                # Find all section start indices
                for i, line in enumerate(lines):
                    if re.match(r"^[A-Z]+-[A-Z]+:$", line.strip()) or "COMMUNICATION HISTORY:" in line:
                        section_starts.append(i)
                
                # Add a sentinel index for the end of the file
                section_starts.append(len(lines))
                
                # Identify sections with the most recent timestamp
                recent_sections = []
                for i in range(len(section_starts) - 1):
                    section_content = '\n'.join(lines[section_starts[i]:section_starts[i+1]])
                    if timestamps[-1][0] in section_content or timestamps[-1][1] in section_content:
                        recent_sections.append((section_starts[i], section_starts[i+1]))
                
                # Extract recent sections
                if recent_sections:
                    logger.debug(f"CONTEXT | MESSAGE SUMMARIZATION | {power_name} | Identified {len(recent_sections)} recent message sections")
                    
                    # Rebuild the message history with recent sections preserved
                    all_lines = []
                    recent_lines = []
                    sections_to_summarize = []
                    
                    # Mark sections for preservation or summarization
                    current_pos = 0
                    for start, end in recent_sections:
                        # Add section before this recent section to summarization
                        if current_pos < start:
                            sections_to_summarize.append('\n'.join(lines[current_pos:start]))
                        
                        # Add this recent section to preservation
                        recent_lines.extend(lines[start:end])
                        current_pos = end
                    
                    # Add any remaining content after the last recent section
                    if current_pos < len(lines):
                        sections_to_summarize.append('\n'.join(lines[current_pos:]))
                    
                    # Set the recent and remaining content
                    recent_turn_messages = '\n'.join(recent_lines)
                    remaining_history = '\n'.join(sections_to_summarize)
                    
                    # Log what we're preserving vs summarizing
                    recent_tokens = count_tokens(recent_turn_messages)
                    remaining_tokens = count_tokens(remaining_history)
                    logger.info(f"CONTEXT | MESSAGE SUMMARIZATION | {power_name} | Preserving {recent_tokens} tokens from most recent turn, summarizing {remaining_tokens} tokens")
            
            # If we couldn't extract by timestamp, try to preserve a reasonable portion
            if not recent_turn_messages:
                # Fallback approach: preserve approximately the last 25% of the content
                message_lines = message_history.split('\n')
                split_point = max(1, int(len(message_lines) * 0.75))  # Preserve last 25%
                
                remaining_history = '\n'.join(message_lines[:split_point])
                recent_turn_messages = '\n'.join(message_lines[split_point:])
                
                recent_tokens = count_tokens(recent_turn_messages)
                remaining_tokens = count_tokens(remaining_history)
                logger.info(f"CONTEXT | MESSAGE SUMMARIZATION | {power_name} | Fallback: preserving last {recent_tokens} tokens (~25%), summarizing {remaining_tokens} tokens")
        
        # Use default approach if we couldn't extract the recent turn
        if not recent_turn_messages:
            # Preserve approximately the last 25% of content
            split_point = max(1, int(len(message_history) * 0.75))  # Keep last 25%
            remaining_history = message_history[:split_point]
            recent_turn_messages = message_history[split_point:]
            
            recent_tokens = count_tokens(recent_turn_messages)
            remaining_tokens = count_tokens(remaining_history)
            logger.info(f"CONTEXT | MESSAGE SUMMARIZATION | {power_name} | Default: preserving last {recent_tokens} tokens (~25%), summarizing {remaining_tokens} tokens")
        
        # Create a meaningful ID for this message batch for tracking
        current_time = int(time.time())
        message_batch_id = f"{power_name}_msg_{current_time}"
        if message_batch_id not in power_state['summarized_messages']:
            power_state['summarized_messages'].add(message_batch_id)
        
        # Generate recursive summary using previous summary and remaining history
        previous_summary = power_state['last_message_summary']
        has_previous_summary = previous_summary is not None
        
        # Log summarization approach
        if has_previous_summary and remaining_history:
            prev_summary_tokens = count_tokens(previous_summary)
            remaining_tokens = count_tokens(remaining_history)
            logger.info(f"CONTEXT | MESSAGE SUMMARIZATION | {power_name} | Recursive approach: combining {prev_summary_tokens} token summary with {remaining_tokens} tokens of older messages")
            
            summary = self.generate_recursive_summary(
                previous_summary,
                remaining_history,
                prompt_type="recursive",
                power_name=power_name
            )
        elif remaining_history:
            # No previous summary, do initial summarization of older content
            remaining_tokens = count_tokens(remaining_history)
            logger.info(f"CONTEXT | MESSAGE SUMMARIZATION | {power_name} | Initial summarization: {remaining_tokens} tokens of older messages")
            
            summary = self.generate_recursive_summary(
                None,
                remaining_history,
                prompt_type="message",
                power_name=power_name
            )
        else:
            # Nothing to summarize, use previous summary if available or empty summary
            summary = previous_summary or "(No earlier message history to summarize)"
            logger.info(f"CONTEXT | MESSAGE SUMMARIZATION | {power_name} | Using previous summary only, no older content to summarize")
        
        # Update power state with the summary of older content
        power_state['last_message_summary'] = summary
        
        # Protect against empty summaries
        if not summary or summary.strip() == "":
            logger.warning(f"CONTEXT | MESSAGE SUMMARIZATION | Empty summary generated for {power_name}, using fallback")
            summary = f"(Summary for {power_name}: No significant diplomatic interactions in earlier phases)"
            power_state['last_message_summary'] = summary
        
        # Track metrics for logging
        summary_tokens = count_tokens(summary)
        recent_tokens = count_tokens(recent_turn_messages)
        combined_tokens = summary_tokens + recent_tokens
        reduction = 100 - (combined_tokens * 100 / message_tokens) if message_tokens > 0 else 0
        
        logger.info(f"CONTEXT | MESSAGE SUMMARIZATION | Completed for {power_name}: {message_tokens} → {combined_tokens} tokens ({reduction:.1f}% reduction)")
        logger.info(f"CONTEXT | MESSAGE SUMMARIZATION | {power_name} | Final breakdown: {summary_tokens} tokens summary + {recent_tokens} tokens recent messages")
        
        # Combine the summary with the preserved recent messages
        header = f"--- SUMMARIZED DIPLOMATIC HISTORY FOR {power_name} ---\n"
        if has_previous_summary:
            header += f"(Includes recursive summary of previous communications)\n\n"
        else:
            header += f"(Initial summary of communications)\n\n"
        
        # Add a clear separator between summary and recent messages
        recent_header = "\n\n--- MOST RECENT COMMUNICATIONS (PRESERVED) ---\n\n"
            
        return header + summary + recent_header + recent_turn_messages
    
    def get_optimized_phase_summaries(
        self, 
        game, 
        power_name: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Main access point for getting optimized phase summaries.
        If summaries are below threshold, returns original.
        Otherwise, returns recursively condensed version.
        """
        if not hasattr(game, "phase_summaries") or not game.phase_summaries:
            logger.debug("CONTEXT | No phase summaries available")
            return {}
            
        # Count original phases for logging
        original_phase_count = len(game.phase_summaries)
        logger.debug(f"CONTEXT | Checking phase optimization for {power_name or 'game'} with {original_phase_count} phases")
        
        # Start with a working copy of the original phase summaries
        working_phase_summaries = dict(game.phase_summaries)
        
        # Add any existing summaries from previous runs
        if self.phase_summary_state['last_summary']:
            # Find the last phase we summarized
            if self.phase_summary_state['summarized_phases']:
                last_summarized = max(self.phase_summary_state['summarized_phases'])
                summary_key = f"SUMMARY_UNTIL_{last_summarized}"
                working_phase_summaries[summary_key] = self.phase_summary_state['last_summary']
                logger.debug(f"CONTEXT | Added existing phase summary '{summary_key}' from previous run")
        
        # Check if we need to create a new summary
        if self.should_summarize_phases(working_phase_summaries):
            # Create condensed version using recursive summarization
            logger.debug(f"CONTEXT | Creating optimized phase summaries for {power_name or 'game'}")
            result = self.summarize_phase_history(working_phase_summaries, power_name)
            
            # Add a log showing which phases are included in the optimized version
            phase_keys = list(result.keys())
            summary_keys = [k for k in phase_keys if k.startswith("SUMMARY_UNTIL_")]
            regular_phases = [k for k in phase_keys if not k.startswith("SUMMARY_UNTIL_")]
            
            logger.info(f"CONTEXT | PHASE OPTIMIZATION | Returning {len(summary_keys)} summary entries and {len(regular_phases)} regular phases")
            if summary_keys:
                logger.debug(f"CONTEXT | PHASE OPTIMIZATION | Summary entries: {', '.join(summary_keys)}")
            if regular_phases:
                logger.debug(f"CONTEXT | PHASE OPTIMIZATION | Regular phases: {', '.join(regular_phases)}")
                
            return result
        else:
            # Return the working copy which includes any previous summaries
            summary_keys = [k for k in working_phase_summaries.keys() if k.startswith("SUMMARY_UNTIL_")]
            logger.debug(f"CONTEXT | Using original phase summaries plus {len(summary_keys)} previous summaries (below threshold)")
            return working_phase_summaries
    
    def get_optimized_message_history(
        self, 
        game_history, 
        power_name: Optional[str] = None,
        organized_history: Optional[str] = None
    ) -> str:
        """
        Main access point for getting optimized message history.
        Ensures that the most recent messages are always preserved intact.
        
        Args:
            game_history: The GameHistory object
            power_name: The power requesting the history
            organized_history: Optional pre-organized history text
            
        Returns:
            Optimized message history as string
        """
        if not power_name:
            logger.warning("CONTEXT | No power_name provided for message history optimization, using raw history")
            return organized_history or (game_history.get_game_history() if hasattr(game_history, "get_game_history") else str(game_history))
        
        # Get the raw message history for this power
        if organized_history is not None:
            message_history = organized_history
        elif hasattr(game_history, "get_game_history"):
            message_history = game_history.get_game_history(power_name) or "(No history yet)"
        else:
            message_history = str(game_history) if game_history else "(No history yet)"
        
        # Log what we received from the game history object
        message_chars = len(message_history)
        message_tokens = count_tokens(message_history)
        
        logger.debug(f"CONTEXT | RAW MESSAGE HISTORY | {power_name} | Length: {message_chars} chars ({message_tokens} tokens)")
        if message_chars < 100:  # If it's very short, log the entire content
            logger.debug(f"CONTEXT | RAW MESSAGE HISTORY | {power_name} | Content: {message_history}")
        
        # Enhanced check for empty or minimal history
        if message_history in ["(No history yet)", "", None] or message_history.strip() == "":
            fallback_message = f"(No communication history available for {power_name})"
            logger.warning(f"CONTEXT | Empty message history for {power_name}, using fallback: '{fallback_message}'")
            return fallback_message
        
        # Check for very sparse history (just headings)
        if "COMMUNICATION HISTORY:" in message_history and message_chars < 200:
            if all(line.strip() == "" or line.strip().endswith(":") or "has not engaged" in line 
                  for line in message_history.split("\n") if line.strip()):
                logger.warning(f"CONTEXT | Found sparse message history template for {power_name}, using fallback")
                return f"COMMUNICATION HISTORY:\n\n{power_name} has no significant diplomatic exchanges recorded in this phase."
        
        # Get power-specific state 
        power_state = self.get_power_state(power_name)
        
        logger.debug(f"CONTEXT | Checking message optimization for {power_name} with {message_tokens} tokens")
        
        # Check if we already have a summary with recent messages preserved
        if "--- MOST RECENT COMMUNICATIONS (PRESERVED) ---" in message_history:
            # The history already contains our preserved recent messages format
            # We should extract the recent messages, check for new content, and handle appropriately
            logger.info(f"CONTEXT | MESSAGE OPTIMIZATION | {power_name} | Detected existing summary with preserved recent messages")
            
            # Split history into sections
            parts = message_history.split("--- MOST RECENT COMMUNICATIONS (PRESERVED) ---")
            if len(parts) >= 2:
                # Extract summary and preserved parts
                previous_summary_part = parts[0].strip()
                preserved_recent_part = parts[1].strip()
                
                # Check if we have new content to add to this history
                new_content = ""
                # If organized_history is different from what we previously processed,
                # it may contain new messages that we haven't seen before
                if organized_history and "--- MOST RECENT COMMUNICATIONS (PRESERVED) ---" not in organized_history:
                    # This is likely new content that should be treated as the most recent
                    new_content = organized_history
                    logger.info(f"CONTEXT | Detected new content to add to existing summary structure: {count_tokens(new_content)} tokens")
                
                if new_content:
                    # Combine the existing summary with the preserved content plus new content
                    # The preserved content becomes part of what needs to be summarized
                    content_to_summarize = preserved_recent_part
                    
                    # Extract the actual summary part without headers
                    summary_text = previous_summary_part
                    if "--- SUMMARIZED DIPLOMATIC HISTORY FOR" in summary_text:
                        summary_lines = summary_text.split("\n")
                        # Skip the header lines (usually 3)
                        summary_text = "\n".join(summary_lines[3:])
                    
                    # Generate a new summary with the preserved content now included
                    updated_summary = self.generate_recursive_summary(
                        summary_text,
                        content_to_summarize,
                        prompt_type="recursive",
                        power_name=power_name
                    )
                    
                    # Update the power state
                    power_state['last_message_summary'] = updated_summary
                    
                    # Create the new structure
                    header = f"--- SUMMARIZED DIPLOMATIC HISTORY FOR {power_name} ---\n"
                    header += f"(Includes recursive summary of previous communications)\n\n"
                    recent_header = "\n\n--- MOST RECENT COMMUNICATIONS (PRESERVED) ---\n\n"
                    
                    # Return the new summary + recent content
                    result = header + updated_summary + recent_header + new_content
                    
                    # Log the update
                    logger.info(f"CONTEXT | MESSAGE OPTIMIZATION | {power_name} | Updated existing summary structure with {count_tokens(new_content)} tokens of new content")
                    return result
            
        # Standard path: Check if we need to create a new summary
        if self.should_summarize_messages(message_history, power_name):
            # Create recursively condensed version
            logger.debug(f"CONTEXT | Creating optimized message history for {power_name}")
            
            # Determine if this is an initial summarization or recursive summarization
            has_previous_summary = power_state['last_message_summary'] is not None
            
            # If this appears to be a message history that already contains our summary header,
            # we should extract the actual messages and combine with the previous summary
            if has_previous_summary and "--- SUMMARIZED DIPLOMATIC HISTORY FOR" in message_history:
                logger.info(f"CONTEXT | MESSAGE OPTIMIZATION | {power_name} | Detected summarized content in message history")
                
                # Split the history to extract only the new content
                parts = message_history.split("--- SUMMARIZED DIPLOMATIC HISTORY FOR")
                if len(parts) > 1:
                    # Extract only the new content (the part before the summary header)
                    new_content = parts[0].strip()
                    if new_content:
                        logger.debug(f"CONTEXT | Extracted {count_tokens(new_content)} tokens of new content from message history")
                        
                        # Use the previous summary plus the extracted new content
                        result = self.summarize_message_history(new_content, power_name)
                    else:
                        # If no new content, just use the previous summary
                        logger.warning(f"CONTEXT | No new content found before summary marker for {power_name}")
                        result = power_state['last_message_summary']
                else:
                    # Fallback to normal summarization if parsing fails
                    logger.warning(f"CONTEXT | Failed to parse summary structure for {power_name}, using normal summarization")
                    result = self.summarize_message_history(message_history, power_name)
            else:
                # Normal summarization path
                result = self.summarize_message_history(message_history, power_name)
            
            # Log the optimization stats
            result_tokens = count_tokens(result)
            logger.info(f"CONTEXT | MESSAGE OPTIMIZATION | {power_name} | Original size: {message_tokens} tokens, Optimized size: {result_tokens} tokens")
            logger.info(f"CONTEXT | MESSAGE OPTIMIZATION | {power_name} | Using {'recursive' if has_previous_summary else 'initial'} message summary with preserved recent content")
            
            # Safety check for empty result
            if not result or result.strip() == "":
                logger.error(f"CONTEXT | MESSAGE OPTIMIZATION | {power_name} | Empty result after summarization, using original history")
                return message_history
                
            return result
        else:
            # If we have a previous summary, use it instead of raw history when appropriate
            if power_state['last_message_summary'] and message_tokens > (self.message_token_threshold // 2):
                # We're approaching the threshold, but not over it yet
                # Use the existing summary instead of raw history if it's significantly smaller
                summary = power_state['last_message_summary']
                summary_tokens = count_tokens(summary)
                
                # Only use previous summary if it's significantly smaller
                if summary_tokens < (message_tokens * 0.7):  # At least 30% reduction
                    logger.info(f"CONTEXT | MESSAGE OPTIMIZATION | {power_name} | Using existing summary ({summary_tokens} tokens) instead of raw history ({message_tokens} tokens)")
                    
                    # Safety check for empty summary
                    if not summary or summary.strip() == "":
                        logger.error(f"CONTEXT | MESSAGE OPTIMIZATION | {power_name} | Empty summary found, using original history")
                        return message_history
                        
                    return summary
                else:
                    logger.debug(f"CONTEXT | MESSAGE OPTIMIZATION | {power_name} | Summary not significantly smaller ({summary_tokens} vs {message_tokens} tokens), using original")
            
            # Final safety check before returning original
            if message_history.strip() == "":
                logger.warning(f"CONTEXT | Empty original message history for {power_name}, using minimal fallback")
                return f"COMMUNICATION HISTORY:\n\n{power_name} has no diplomatic history yet."
            
            # Return original when well below threshold
            logger.debug(f"CONTEXT | Using original message history for {power_name} (below threshold)")
            return message_history


# Global context manager instance
# This can be configured at startup
context_manager = ContextManager()

def configure_context_manager(
    phase_threshold: int = 15000,
    message_threshold: int = 15000,
    summary_model: str = "o3-mini"
) -> None:
    """
    Configure the global context manager.
    Should be called early in the application lifecycle.
    
    Args:
        phase_threshold: Token threshold for phase summarization
        message_threshold: Token threshold for message summarization
        summary_model: Model to use for summarization
    """
    global context_manager
    logger.info(f"CONTEXT | Configuring manager with thresholds: phase={phase_threshold}, message={message_threshold} tokens, model={summary_model}")
    context_manager = ContextManager(
        phase_token_threshold=phase_threshold,
        message_token_threshold=message_threshold,
        summary_model=summary_model
    )

def get_optimized_context(
    game,
    game_history,
    power_name: Optional[str] = None,
    organized_history: Optional[str] = None
) -> Tuple[Dict[str, str], str]:
    """
    Convenience function to get both optimized phase summaries and message history.
    
    Args:
        game: The Diplomacy game object
        game_history: The GameHistory object
        power_name: The power requesting the history (optional)
        organized_history: Optional pre-organized history text
    
    Returns:
        Tuple of (optimized_phase_summaries, optimized_message_history)
    """
    logger.debug(f"CONTEXT | Getting optimized context for {power_name or 'game'}")
    
    # Track original sizes for comparison
    orig_phase_count = len(game.phase_summaries) if hasattr(game, "phase_summaries") and game.phase_summaries else 0
    orig_phase_tokens = sum(count_tokens(content) for content in game.phase_summaries.values()) if hasattr(game, "phase_summaries") and game.phase_summaries else 0
    
    raw_message_history = ""
    if organized_history is not None:
        raw_message_history = organized_history
    elif hasattr(game_history, "get_game_history") and power_name:
        raw_message_history = game_history.get_game_history(power_name) or "(No history yet)"
    
    orig_message_tokens = count_tokens(raw_message_history) if raw_message_history else 0
    
    # Get optimized context - phases first as they impact game state
    start_time = time.time()
    optimized_phases = context_manager.get_optimized_phase_summaries(game, power_name)
    phase_opt_time = time.time() - start_time
    
    # Then get optimized messages
    start_time = time.time()
    optimized_messages = context_manager.get_optimized_message_history(
        game_history, power_name, organized_history
    )
    message_opt_time = time.time() - start_time
    
    # Track token counts for the optimized content
    phase_count = len(optimized_phases) if optimized_phases else 0
    summary_count = len([k for k in optimized_phases.keys() if k.startswith("SUMMARY_UNTIL_")]) if optimized_phases else 0
    message_tokens = count_tokens(optimized_messages) if optimized_messages else 0
    phase_tokens = sum(count_tokens(content) for content in optimized_phases.values()) if optimized_phases else 0
    
    # Calculate optimization metrics
    phase_reduction = (orig_phase_tokens - phase_tokens) / orig_phase_tokens * 100 if orig_phase_tokens > 0 else 0
    message_reduction = (orig_message_tokens - message_tokens) / orig_message_tokens * 100 if orig_message_tokens > 0 else 0
    
    # Enhanced logging
    logger.info(f"CONTEXT | OPTIMIZATION RESULT | {power_name or 'game'} | Phases: {orig_phase_count} → {phase_count} ({phase_reduction:.1f}% token reduction)")
    logger.info(f"CONTEXT | OPTIMIZATION RESULT | {power_name or 'game'} | Messages: {orig_message_tokens} → {message_tokens} tokens ({message_reduction:.1f}% reduction)")
    logger.debug(f"CONTEXT | OPTIMIZATION RESULT | {power_name or 'game'} | Performance: {phase_opt_time:.2f}s for phases, {message_opt_time:.2f}s for messages")
    logger.debug(f"CONTEXT | OPTIMIZATION RESULT | {power_name or 'game'} | Returning {phase_count} phases ({summary_count} summaries, {phase_tokens} tokens) and {message_tokens} tokens of messages")
    
    return optimized_phases, optimized_messages