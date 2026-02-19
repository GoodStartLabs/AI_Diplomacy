from dotenv import load_dotenv
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import re

logger = logging.getLogger("utils")
# Level inherited from root (set in lm_game.py); use --debug for DEBUG globally.

load_dotenv()


@dataclass
class Message:
    sender: str
    recipient: str
    content: str


@dataclass
class Phase:
    name: str  # e.g. "SPRING 1901"
    plans: Dict[str, str] = field(default_factory=dict)
    messages: List[Message] = field(default_factory=list)
    submitted_orders_by_power: Dict[str, List[str]] = field(default_factory=dict)
    orders_by_power: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    results_by_power: Dict[str, List[List[str]]] = field(default_factory=lambda: defaultdict(list))
    # NEW: Store phase-end summaries provided by each power
    phase_summaries: Dict[str, str] = field(default_factory=dict)
    # NEW: Store experience/journal updates from each power for this phase
    experience_updates: Dict[str, str] = field(default_factory=dict)

    def add_plan(self, power_name: str, plan: str):
        self.plans[power_name] = plan

    def add_message(self, sender: str, recipient: str, content: str):
        self.messages.append(Message(sender=sender, recipient=recipient, content=content))

    def add_orders(self, power: str, orders: List[str], results: List[List[str]]):
        self.orders_by_power[power].extend(orders)
        # Make sure results has the same length as orders, if not, pad with empty lists
        if len(results) < len(orders):
            results.extend([[] for _ in range(len(orders) - len(results))])
        self.results_by_power[power].extend(results)

    def get_private_messages(self, power: str) -> Dict[str, str]:
        conversations = defaultdict(str)
        for msg in self.messages:
            if msg.sender == power:
                conversations[msg.recipient] += f"  {power}: {msg.content}\n"
            elif msg.recipient == power:
                conversations[msg.sender] += f"  {msg.sender}: {msg.content}\n"
        return conversations

    def get_all_orders_formatted(self) -> str:
        if not self.orders_by_power:
            return ""

        result = f"\nOrders for {self.name}:\n"
        for power, orders in self.orders_by_power.items():
            result += f"{power}:\n"
            results = self.results_by_power.get(power, [])
            for i, order in enumerate(orders):
                if i < len(results) and results[i]:
                    # Join multiple results with commas
                    result_str = f" ({', '.join(results[i])})"
                else:
                    result_str = " (success)"
                result += f"  {order}{result_str}\n"
            result += "\n"
        return result


@dataclass
class GameHistory:
    phases: List[Phase] = field(default_factory=list)

    def add_phase(self, phase_name: str):
        # Avoid adding duplicate phases
        if not self.phases or self.phases[-1].name != phase_name:
            self.phases.append(Phase(name=phase_name))
            logger.debug(f"Added new phase: {phase_name}")
        else:
            logger.warning(f"Phase {phase_name} already exists. Not adding again.")

    def _get_phase(self, phase_name: str) -> Optional[Phase]:
        for phase in reversed(self.phases):
            if phase.name == phase_name:
                return phase
        logger.error(f"Phase {phase_name} not found in history.")
        return None

    def add_plan(self, phase_name: str, power_name: str, plan: str):
        phase = self._get_phase(phase_name)
        if phase:
            phase.plans[power_name] = plan
            logger.debug(f"Added plan for {power_name} in {phase_name}")

    def add_message(self, phase_name: str, sender: str, recipient: str, message_content: str):
        phase = self._get_phase(phase_name)
        if phase:
            message = Message(sender=sender, recipient=recipient, content=message_content)
            phase.messages.append(message)
            logger.debug(f"Added message from {sender} to {recipient} in {phase_name}")

    def add_orders(self, phase_name: str, power_name: str, orders: List[str]):
        phase = self._get_phase(phase_name)
        if phase:
            phase.orders_by_power[power_name].extend(orders)
            logger.debug(f"Added orders for {power_name} in {phase_name}: {orders}")

    def add_results(self, phase_name: str, power_name: str, results: List[List[str]]):
        phase = self._get_phase(phase_name)
        if phase:
            phase.results_by_power[power_name].extend(results)
            logger.debug(f"Added results for {power_name} in {phase_name}: {results}")

    # NEW: Method to add phase summary for a power
    def add_phase_summary(self, phase_name: str, power_name: str, summary: str):
        phase = self._get_phase(phase_name)
        if phase:
            phase.phase_summaries[power_name] = summary
            logger.debug(f"Added phase summary for {power_name} in {phase_name}")

    # NEW: Method to add experience update for a power
    def add_experience_update(self, phase_name: str, power_name: str, update: str):
        phase = self._get_phase(phase_name)
        if phase:
            phase.experience_updates[power_name] = update
            logger.debug(f"Added experience update for {power_name} in {phase_name}")

    def get_strategic_directives(self):
        # returns for last phase only if exists
        if not self.phases:
            return {}
        return self.phases[-1].plans

    def get_order_history_for_prompt(
        self,
        game: "Game",
        power_name: str,
        current_phase_name: str,
        num_movement_phases_to_show: int = 1,
    ) -> str:
        # ── guard clauses ──────────────────────────────────────────
        if not self.phases or num_movement_phases_to_show <= 0:
            return "\n(No order history to show)\n"

        prev = [p for p in self.phases if p.name != current_phase_name]
        if not prev:
            return "\n(No previous phases in history)\n"

        start, seen = 0, 0
        for i in range(len(prev) - 1, -1, -1):
            if prev[i].name.endswith("M"):
                seen += 1
                if seen >= num_movement_phases_to_show:
                    start = i
                    break
        phases_to_report = prev[start:]
        if not phases_to_report:
            return "\n(No relevant order history in look-back window)\n"

        # ── helpers ───────────────────────────────────────────────
        def _scalar(res):
            """Flatten lists/dicts to a single outcome token (string)."""
            tag = res
            while isinstance(tag, list):
                tag = tag[0] if tag else ""
            if isinstance(tag, dict):
                tag = tag.get("outcome") or tag.get("result") or ""
            return str(tag).strip().lower()

        engine_phases = {ph.name: ph for ph in getattr(game, "get_phase_history", lambda: [])()}
        eng2code = {"AUSTRIA": "AUT", "ENGLAND": "ENG", "FRANCE": "FRA", "GERMANY": "GER", "ITALY": "ITA", "RUSSIA": "RUS", "TURKEY": "TUR"}
        norm = game.map.norm

        out_lines = []

        for ph in phases_to_report:
            if not (ph.orders_by_power or ph.submitted_orders_by_power):
                continue
            out_lines.append(f"\n--- Orders from Phase: {ph.name} ---")

            for pwr in sorted(set(ph.orders_by_power) | set(ph.submitted_orders_by_power)):
                submitted = ph.submitted_orders_by_power.get(pwr, [])
                accepted = ph.orders_by_power.get(pwr, [])

                if isinstance(submitted, str):
                    submitted = [submitted]
                if isinstance(accepted, str):
                    accepted = [accepted]

                def _norm_keep(o):  # keep WAIVE readable
                    return o if o.upper() == "WAIVE" else norm(o)

                sub_norm = {_norm_keep(o): o for o in submitted}
                acc_norm = {_norm_keep(o): o for o in accepted}
                if not submitted and not accepted:
                    continue

                out_lines.append(f"  {pwr}:")

                # outcome source
                raw_res = ph.results_by_power.get(pwr) or ph.results_by_power or {}
                if not raw_res:
                    eng = engine_phases.get(ph.name)
                    if eng and hasattr(eng, "order_results"):
                        key = next((k for k, v in eng2code.items() if v == pwr), None)
                        raw_res = (eng.order_results or {}).get(key, {})

                seen_ok = set()

                # 1️⃣ accepted orders
                for idx, order in enumerate(accepted):
                    if isinstance(raw_res, dict):
                        res_raw = raw_res.get(order) or raw_res.get(" ".join(order.split()[:2]))
                    elif isinstance(raw_res, list) and idx < len(raw_res):
                        res_raw = raw_res[idx]
                    else:
                        res_raw = ""

                    tag = _scalar(res_raw)
                    if not tag or tag == "ok":
                        tag = "success"
                    elif "bounce" in tag:
                        tag = "bounce"
                    elif "void" == tag:
                        tag = "void: no effect"
                    
                    # don't show (success) tag for hold moves, it might be causing convergence on
                    # always-hold behaviour
                    is_hold = re.search(r"\sH\s*$", order) or re.search(r"\sHOLD\s*$", order)
                    if tag == "success" and is_hold:
                        out_lines.append(f"    {order}")
                    else:
                        out_lines.append(f"    {order} ({tag})")
                    seen_ok.add(_norm_keep(order))

                # 2️⃣ invalid submissions
                for k in sorted(set(sub_norm) - seen_ok):
                    out_lines.append(f"    {sub_norm[k]} (Rejected by engine: invalid)")

        if len(out_lines) == 1:
            return "\n(No orders were issued in recent history)\n"
        return "\n".join(out_lines)

    def get_orders_history_for_phase(
            self,
            game: "Game",
            phase_name: str,                      # ← the single phase we want
        ) -> Dict[str, Dict[str, List[Dict[str, str]]]]:
        """
        Return the orders for `phase_name` as:

            {
                "<POWER>": {
                    "<order_type>": [
                        {"order": "<order str>", "result": "<result str>"},
                        ...
                    ],
                    ...
                },
                ...
            }

        Order types: move, hold, support, convoy, build, disband, waive, other.
        """

        # ── locate the requested phase ──────────────────────────────
        target_phase = next((p for p in self.phases if p.name == phase_name), None)
        if not target_phase or not (target_phase.orders_by_power or target_phase.submitted_orders_by_power):
            return {}

        # ── helpers ───────────────────────────────────────────────
        def _scalar(res):
            """Flatten lists/dicts to a single outcome token."""
            tag = res
            while isinstance(tag, list):
                tag = tag[0] if tag else ""
            if isinstance(tag, dict):
                tag = tag.get("outcome") or tag.get("result") or ""
            return str(tag).strip().lower()

        def _order_type(order: str) -> str:
            o = order.upper()

            if o.strip() == "WAIVE":
                return "waive"

            # hold: ends with “ H” or “ HOLD”            
            if re.search(r"\sH\s*$", o) or re.search(r"\sHOLD\s*$", o):
                return "hold"

            if " S " in o:
                return "support"
            if " C " in o:
                return "convoy"
            if " R " in o:
                return "retreat"
            if " - " in o:
                return "move"
            if re.search(r"\sBUILD\s*$", o) or o.endswith(" B") or " B " in o:
                return "build"
            if re.search(r"\sDISBAND\s*$", o) or o.endswith(" D") or " D " in o:
                return "disband"
            return "other"


        # engine fallback
        engine_phases = {ph.name: ph for ph in getattr(game, "get_phase_history", lambda: [])()}
        eng2code = {
            "AUSTRIA": "AUT", "ENGLAND": "ENG", "FRANCE": "FRA",
            "GERMANY": "GER", "ITALY": "ITA", "RUSSIA": "RUS", "TURKEY": "TUR",
        }
        norm = game.map.norm

        orders_by_power = defaultdict(lambda: defaultdict(list))

        # iterate powers present in this phase
        for pwr in sorted(set(target_phase.orders_by_power) | set(target_phase.submitted_orders_by_power)):
            submitted = target_phase.submitted_orders_by_power.get(pwr, [])
            accepted  = target_phase.orders_by_power.get(pwr, [])

            if isinstance(submitted, str):
                submitted = [submitted]
            if isinstance(accepted, str):
                accepted = [accepted]

            def _norm_keep(o):
                return o if o.upper() == "WAIVE" else norm(o)

            sub_norm = {_norm_keep(o): o for o in submitted}
            acc_norm = {_norm_keep(o): o for o in accepted}

            # outcome source
            raw_res = target_phase.results_by_power.get(pwr) or target_phase.results_by_power or {}
            if not raw_res:
                eng = engine_phases.get(target_phase.name)
                if eng and hasattr(eng, "order_results"):
                    key = next((k for k, v in eng2code.items() if v == pwr), None)
                    raw_res = (eng.order_results or {}).get(key, {})

            seen_ok = set()

            # accepted orders
            for idx, order in enumerate(accepted):
                if isinstance(raw_res, dict):
                    res_raw = raw_res.get(order) or raw_res.get(" ".join(order.split()[:2]))
                elif isinstance(raw_res, list) and idx < len(raw_res):
                    res_raw = raw_res[idx]
                else:
                    res_raw = ""

                tag = _scalar(res_raw)
                if not tag or tag == "ok":
                    tag = "success"
                elif "bounce" in tag:
                    tag = "bounce"
                elif "void" == tag:
                    tag = "void: no effect"

                result_field = tag

                orders_by_power[pwr][_order_type(order)].append(
                    {"order": order, "result": result_field}
                )
                seen_ok.add(_norm_keep(order))

            # invalid submissions
            for k in sorted(set(sub_norm) - seen_ok):
                order_str = sub_norm[k]
                orders_by_power[pwr][_order_type(order_str)].append(
                    {"order": order_str, "result": "invalid"}
                )

        # convert nested defaultdicts to regular dicts
        return {
            pwr: {otype: lst for otype, lst in type_map.items()}
            for pwr, type_map in orders_by_power.items()
        }




    def get_messages_this_round(self, power_name: str, current_phase_name: str) -> str:
        current_phase: Optional[Phase] = None
        for phase_obj in self.phases:
            if phase_obj.name == current_phase_name:
                current_phase = phase_obj
                break

        if not current_phase:
            return f"\n(No messages found for current phase: {current_phase_name})\n"

        private_msgs_dict = current_phase.get_private_messages(power_name)
        if not private_msgs_dict:
            return f"\n(No messages recorded for current phase: {current_phase_name})\n"

        messages_str = "**MESSAGES TO/FROM YOU THIS ROUND:**\n"
        for other_power, conversation_content in private_msgs_dict.items():
            messages_str += f" Conversation with {other_power}:\n"
            messages_str += conversation_content
            messages_str += "\n"
        return messages_str.strip()

    # New method to get recent messages TO a specific power
    def get_recent_messages_to_power(self, power_name: str, limit: int = 3) -> List[Dict[str, str]]:
        """
        Gets the most recent messages sent TO this power, useful for tracking messages that need replies.
        Returns a list of dictionaries with 'sender', 'content', and 'phase' keys.
        """
        if not self.phases:
            return []

        # Get the most recent 2 phases including current phase
        recent_phases = self.phases[-2:] if len(self.phases) >= 2 else self.phases[-1:]

        # Collect all messages sent TO this power
        messages_to_power = []
        for phase in recent_phases:
            for msg in phase.messages:
                if msg.recipient == power_name and msg.sender != power_name:
                    messages_to_power.append({"sender": msg.sender, "content": msg.content, "phase": phase.name})

        # Add debug logging
        logger.info(f"Found {len(messages_to_power)} messages to {power_name} across {len(recent_phases)} phases")
        if not messages_to_power:
            logger.info(f"No messages found for {power_name} to respond to")

        # Take the most recent 'limit' messages
        return messages_to_power[-limit:] if messages_to_power else []

    def get_ignored_messages_by_power(self, sender_name: str, num_phases: int = 3) -> Dict[str, List[Dict[str, str]]]:
        """
        Identifies which powers are not responding to messages from sender_name.
        Returns a dict mapping power names to their ignored messages.

        A message is considered ignored if:
        1. It was sent from sender_name to another power (private)
        2. No response from that power was received in the same or next phase
        """
        ignored_by_power = {}

        # Get recent phases
        recent_phases = self.phases[-num_phases:] if self.phases else []
        if not recent_phases:
            return ignored_by_power

        for i, phase in enumerate(recent_phases):
            # Get messages sent by sender to other powers (targeted only)
            sender_messages = []
            for msg in phase.messages:
                if isinstance(msg, Message):
                    if msg.sender == sender_name and msg.recipient != sender_name:
                        sender_messages.append(msg)
                else:
                    if msg["sender"] == sender_name and msg["recipient"] != sender_name:
                        sender_messages.append(msg)

            # Check for responses in this and next phases
            for msg in sender_messages:
                # Handle both Message objects and dict objects
                if isinstance(msg, Message):
                    recipient = msg.recipient
                    msg_content = msg.content
                else:
                    recipient = msg["recipient"]
                    msg_content = msg["content"]

                # Look for responses in current phase and next phases
                found_response = False

                # Check remaining phases starting from current
                for check_phase in recent_phases[i : min(i + 2, len(recent_phases))]:
                    # Look for direct response: FROM the recipient TO the sender
                    response_msgs = []
                    for m in check_phase.messages:
                        if isinstance(m, Message):
                            if m.sender == recipient and m.recipient == sender_name:
                                response_msgs.append(m)
                        else:
                            if m["sender"] == recipient and m["recipient"] == sender_name:
                                response_msgs.append(m)

                    if response_msgs:
                        found_response = True
                        break

                if not found_response:
                    if recipient not in ignored_by_power:
                        ignored_by_power[recipient] = []
                    ignored_by_power[recipient].append({"phase": phase.name, "content": msg_content})

        return ignored_by_power
