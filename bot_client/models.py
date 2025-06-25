"""
Pydantic models for Diplomacy WebSocket protocol messages.

This module provides type-safe models for all WebSocket messages as documented
in WEBSOCKET.md, including requests (client -> server), responses (server -> client),
and notifications (server -> client).
"""

from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field
from abc import ABC


# =============================================================================
# Base Message Classes
# =============================================================================


class BaseMessage(BaseModel, ABC):
    """Base class for all WebSocket messages."""

    name: str

    class Config:
        extra = "forbid"


class BaseRequest(BaseMessage):
    """Base class for all client -> server requests."""

    request_id: str
    re_sent: bool = False


class BaseResponse(BaseMessage):
    """Base class for all server -> client responses."""

    request_id: str


class BaseNotification(BaseMessage):
    """Base class for all server -> client notifications (no request_id)."""

    pass


# =============================================================================
# Authentication & Connection Level Messages
# =============================================================================


class SignInRequest(BaseRequest):
    """Client authentication request."""

    name: Literal["sign_in"] = "sign_in"
    username: str
    password: str


class GetDaidePortRequest(BaseRequest):
    """Request DAIDE TCP port for a game."""

    name: Literal["get_daide_port"] = "get_daide_port"
    game_id: str


# =============================================================================
# Channel Level Messages (require authentication token)
# =============================================================================


class ChannelRequest(BaseRequest):
    """Base class for channel-level requests that require authentication."""

    token: str


class CreateGameRequest(ChannelRequest):
    """Create a new game."""

    name: Literal["create_game"] = "create_game"
    map_name: str = "standard"
    rules: List[str] = Field(default_factory=lambda: ["NO_PRESS", "IGNORE_ERRORS"])
    n_controls: int = 1
    deadline: Optional[int] = None
    registration_password: Optional[str] = None
    power_name: Optional[str] = None


class JoinGameRequest(ChannelRequest):
    """Join an existing game."""

    name: Literal["join_game"] = "join_game"
    game_id: str
    power_name: Optional[str] = None
    registration_password: Optional[str] = None


class JoinPowersRequest(ChannelRequest):
    """Join multiple powers in a game."""

    name: Literal["join_powers"] = "join_powers"
    game_id: str
    power_names: List[str]
    registration_password: Optional[str] = None


class ListGamesRequest(ChannelRequest):
    """List available games."""

    name: Literal["list_games"] = "list_games"
    game_id_filter: Optional[str] = None
    map_name: Optional[str] = None
    status: Optional[str] = None
    include_protected: bool = False


class GetPlayablePowersRequest(ChannelRequest):
    """Get uncontrolled powers in a game."""

    name: Literal["get_playable_powers"] = "get_playable_powers"
    game_id: str


class GetAvailableMapsRequest(ChannelRequest):
    """Get list of available maps."""

    name: Literal["get_available_maps"] = "get_available_maps"


class GetDummyWaitingPowersRequest(ChannelRequest):
    """Get AI-controllable powers (bot use)."""

    name: Literal["get_dummy_waiting_powers"] = "get_dummy_waiting_powers"
    game_id: str


class SetGradeRequest(ChannelRequest):
    """Modify user permissions."""

    name: Literal["set_grade"] = "set_grade"
    username: str
    grade: str


class DeleteAccountRequest(ChannelRequest):
    """Delete user account."""

    name: Literal["delete_account"] = "delete_account"


class LogoutRequest(ChannelRequest):
    """Disconnect from server."""

    name: Literal["logout"] = "logout"


# =============================================================================
# Game Level Messages (require authentication + game context)
# =============================================================================


class GameRequest(ChannelRequest):
    """Base class for game-level requests."""

    game_id: str
    game_role: str  # Power name like "ENGLAND"
    phase: Optional[str] = None


class SetOrdersRequest(GameRequest):
    """Submit orders for a power."""

    name: Literal["set_orders"] = "set_orders"
    orders: List[str]


class SetWaitFlagRequest(GameRequest):
    """Set wait flag for turn processing."""

    name: Literal["set_wait_flag"] = "set_wait_flag"
    wait: bool


class SendGameMessageRequest(GameRequest):
    """Send diplomatic message."""

    name: Literal["send_game_message"] = "send_game_message"
    recipient: str  # Power name or "GLOBAL"
    message: str
    message_type: str = "DIPLOMATIC"


class GetAllPossibleOrdersRequest(GameRequest):
    """Get legal orders for current phase."""

    name: Literal["get_all_possible_orders"] = "get_all_possible_orders"


class GetPhaseHistoryRequest(GameRequest):
    """Get historical game phases."""

    name: Literal["get_phase_history"] = "get_phase_history"
    from_phase: Optional[str] = None
    to_phase: Optional[str] = None


class ProcessGameRequest(GameRequest):
    """Force game processing (master only)."""

    name: Literal["process_game"] = "process_game"


class VoteRequest(GameRequest):
    """Vote for/against draw."""

    name: Literal["vote"] = "vote"
    vote: Literal["yes", "no"]


class SaveGameRequest(GameRequest):
    """Export game as JSON."""

    name: Literal["save_game"] = "save_game"


class SetGameStateRequest(GameRequest):
    """Modify game state (master only)."""

    name: Literal["set_game_state"] = "set_game_state"
    state: Dict[str, Any]


class SetGameStatusRequest(GameRequest):
    """Change game status (master only)."""

    name: Literal["set_game_status"] = "set_game_status"
    status: str


class SetDummyPowersRequest(GameRequest):
    """Make powers AI-controlled (master only)."""

    name: Literal["set_dummy_powers"] = "set_dummy_powers"
    power_names: List[str]


class DeleteGameRequest(GameRequest):
    """Delete game (master only)."""

    name: Literal["delete_game"] = "delete_game"


class LeaveGameRequest(GameRequest):
    """Leave game."""

    name: Literal["leave_game"] = "leave_game"


# =============================================================================
# Response Messages (Server -> Client)
# =============================================================================


class OkResponse(BaseResponse):
    """Generic success response."""

    name: Literal["ok"] = "ok"


class ErrorResponse(BaseResponse):
    """Error response with error type and message."""

    name: Literal["error"] = "error"
    error_type: str
    message: str


class DataTokenResponse(BaseResponse):
    """Contains authentication token."""

    name: Literal["data_token"] = "data_token"
    data: str  # The authentication token


class DataGameResponse(BaseResponse):
    """Contains full game object."""

    name: Literal["data_game"] = "data_game"
    data: Dict[str, Any]  # The complete game state


class DataGameInfoResponse(BaseResponse):
    """Contains game metadata."""

    name: Literal["data_game_info"] = "data_game_info"
    data: Dict[str, Any]


class DataGamesResponse(BaseResponse):
    """List of game information."""

    name: Literal["data_games"] = "data_games"
    data: List[Dict[str, Any]]


class DataMapsResponse(BaseResponse):
    """Available maps information."""

    name: Literal["data_maps"] = "data_maps"
    data: List[str]


class DataPowerNamesResponse(BaseResponse):
    """List of power names."""

    name: Literal["data_power_names"] = "data_power_names"
    data: List[str]


class DataPossibleOrdersResponse(BaseResponse):
    """Legal orders and locations."""

    name: Literal["data_possible_orders"] = "data_possible_orders"
    data: Dict[str, List[str]]  # Location -> list of possible orders


class DataGamePhasesResponse(BaseResponse):
    """Historical game phases."""

    name: Literal["data_game_phases"] = "data_game_phases"
    data: List[Dict[str, Any]]


class DataSavedGameResponse(BaseResponse):
    """Exported game JSON."""

    name: Literal["data_saved_game"] = "data_saved_game"
    data: Dict[str, Any]


class DataPortResponse(BaseResponse):
    """DAIDE port number."""

    name: Literal["data_port"] = "data_port"
    data: int


# =============================================================================
# Notification Messages (Server -> Client)
# =============================================================================


class GameProcessedNotification(BaseNotification):
    """Phase completed, new orders phase."""

    name: Literal["game_processed"] = "game_processed"
    game_id: str
    phase: str
    game_state: Dict[str, Any]


class GamePhaseUpdateNotification(BaseNotification):
    """Game state changed."""

    name: Literal["game_phase_update"] = "game_phase_update"
    game_id: str
    phase: str
    game_state: Dict[str, Any]


class GameStatusUpdateNotification(BaseNotification):
    """Game status changed (forming/active/paused/completed)."""

    name: Literal["game_status_update"] = "game_status_update"
    game_id: str
    status: str


class PowersControllersNotification(BaseNotification):
    """Power control assignments changed."""

    name: Literal["powers_controllers"] = "powers_controllers"
    game_id: str
    controllers: Dict[str, str]  # Power -> Controller mapping


class PowerOrdersUpdateNotification(BaseNotification):
    """Player submitted new orders."""

    name: Literal["power_orders_update"] = "power_orders_update"
    game_id: str
    power_name: str
    orders: List[str]
    phase: str


class PowerOrdersFlagNotification(BaseNotification):
    """Player order submission status."""

    name: Literal["power_orders_flag"] = "power_orders_flag"
    game_id: str
    power_name: str
    order_is_set: bool
    phase: str


class PowerWaitFlagNotification(BaseNotification):
    """Player wait flag changed."""

    name: Literal["power_wait_flag"] = "power_wait_flag"
    game_id: str
    power_name: str
    wait: bool


class GameMessageReceivedNotification(BaseNotification):
    """Diplomatic message received."""

    name: Literal["game_message_received"] = "game_message_received"
    game_id: str
    sender: str
    recipient: str
    message: str
    message_type: str
    time_sent: int


class VoteUpdatedNotification(BaseNotification):
    """Draw votes changed (omniscient view)."""

    name: Literal["vote_updated"] = "vote_updated"
    game_id: str
    votes: Dict[str, str]  # Power -> vote mapping


class VoteCountUpdatedNotification(BaseNotification):
    """Vote count changed (observer view)."""

    name: Literal["vote_count_updated"] = "vote_count_updated"
    game_id: str
    count_yes: int
    count_no: int


class PowerVoteUpdatedNotification(BaseNotification):
    """Own power's vote changed."""

    name: Literal["power_vote_updated"] = "power_vote_updated"
    game_id: str
    power_name: str
    vote: str


class GameDeletedNotification(BaseNotification):
    """Game removed from server."""

    name: Literal["game_deleted"] = "game_deleted"
    game_id: str


class OmniscientUpdatedNotification(BaseNotification):
    """Observer permissions changed."""

    name: Literal["omniscient_updated"] = "omniscient_updated"
    game_id: str
    omniscient_type: str


class AccountDeletedNotification(BaseNotification):
    """User account deleted."""

    name: Literal["account_deleted"] = "account_deleted"
    username: str


class ClearedCentersNotification(BaseNotification):
    """Supply centers cleared."""

    name: Literal["cleared_centers"] = "cleared_centers"
    game_id: str
    power_name: str


class ClearedOrdersNotification(BaseNotification):
    """Orders cleared."""

    name: Literal["cleared_orders"] = "cleared_orders"
    game_id: str
    power_name: str
    phase: str


class ClearedUnitsNotification(BaseNotification):
    """Units cleared."""

    name: Literal["cleared_units"] = "cleared_units"
    game_id: str
    power_name: str


# =============================================================================
# Union Types for Message Parsing
# =============================================================================

# All request types
RequestMessage = Union[
    # Connection level
    SignInRequest,
    GetDaidePortRequest,
    # Channel level
    CreateGameRequest,
    JoinGameRequest,
    JoinPowersRequest,
    ListGamesRequest,
    GetPlayablePowersRequest,
    GetAvailableMapsRequest,
    GetDummyWaitingPowersRequest,
    SetGradeRequest,
    DeleteAccountRequest,
    LogoutRequest,
    # Game level
    SetOrdersRequest,
    SetWaitFlagRequest,
    SendGameMessageRequest,
    GetAllPossibleOrdersRequest,
    GetPhaseHistoryRequest,
    ProcessGameRequest,
    VoteRequest,
    SaveGameRequest,
    SetGameStateRequest,
    SetGameStatusRequest,
    SetDummyPowersRequest,
    DeleteGameRequest,
    LeaveGameRequest,
]

# All response types
ResponseMessage = Union[
    OkResponse,
    ErrorResponse,
    DataTokenResponse,
    DataGameResponse,
    DataGameInfoResponse,
    DataGamesResponse,
    DataMapsResponse,
    DataPowerNamesResponse,
    DataPossibleOrdersResponse,
    DataGamePhasesResponse,
    DataSavedGameResponse,
    DataPortResponse,
]

# All notification types
NotificationMessage = Union[
    GameProcessedNotification,
    GamePhaseUpdateNotification,
    GameStatusUpdateNotification,
    PowersControllersNotification,
    PowerOrdersUpdateNotification,
    PowerOrdersFlagNotification,
    PowerWaitFlagNotification,
    GameMessageReceivedNotification,
    VoteUpdatedNotification,
    VoteCountUpdatedNotification,
    PowerVoteUpdatedNotification,
    GameDeletedNotification,
    OmniscientUpdatedNotification,
    AccountDeletedNotification,
    ClearedCentersNotification,
    ClearedOrdersNotification,
    ClearedUnitsNotification,
]

# All message types
WebSocketMessage = Union[RequestMessage, ResponseMessage, NotificationMessage]


# =============================================================================
# Utility Functions
# =============================================================================


def parse_message(data: Dict[str, Any]) -> WebSocketMessage:
    """
    Parse a raw WebSocket message dictionary into the appropriate pydantic model.

    Args:
        data: Raw message dictionary from WebSocket

    Returns:
        Parsed message object

    Raises:
        ValueError: If message cannot be parsed or is of unknown type
    """
    if not isinstance(data, dict) or "name" not in data:
        raise ValueError("Invalid message format: missing 'name' field")

    message_name = data["name"]

    # Map message names to their corresponding classes
    message_classes = {
        # Requests
        "sign_in": SignInRequest,
        "get_daide_port": GetDaidePortRequest,
        "create_game": CreateGameRequest,
        "join_game": JoinGameRequest,
        "join_powers": JoinPowersRequest,
        "list_games": ListGamesRequest,
        "get_playable_powers": GetPlayablePowersRequest,
        "get_available_maps": GetAvailableMapsRequest,
        "get_dummy_waiting_powers": GetDummyWaitingPowersRequest,
        "set_grade": SetGradeRequest,
        "delete_account": DeleteAccountRequest,
        "logout": LogoutRequest,
        "set_orders": SetOrdersRequest,
        "set_wait_flag": SetWaitFlagRequest,
        "send_game_message": SendGameMessageRequest,
        "get_all_possible_orders": GetAllPossibleOrdersRequest,
        "get_phase_history": GetPhaseHistoryRequest,
        "process_game": ProcessGameRequest,
        "vote": VoteRequest,
        "save_game": SaveGameRequest,
        "set_game_state": SetGameStateRequest,
        "set_game_status": SetGameStatusRequest,
        "set_dummy_powers": SetDummyPowersRequest,
        "delete_game": DeleteGameRequest,
        "leave_game": LeaveGameRequest,
        # Responses
        "ok": OkResponse,
        "error": ErrorResponse,
        "data_token": DataTokenResponse,
        "data_game": DataGameResponse,
        "data_game_info": DataGameInfoResponse,
        "data_games": DataGamesResponse,
        "data_maps": DataMapsResponse,
        "data_power_names": DataPowerNamesResponse,
        "data_possible_orders": DataPossibleOrdersResponse,
        "data_game_phases": DataGamePhasesResponse,
        "data_saved_game": DataSavedGameResponse,
        "data_port": DataPortResponse,
        # Notifications
        "game_processed": GameProcessedNotification,
        "game_phase_update": GamePhaseUpdateNotification,
        "game_status_update": GameStatusUpdateNotification,
        "powers_controllers": PowersControllersNotification,
        "power_orders_update": PowerOrdersUpdateNotification,
        "power_orders_flag": PowerOrdersFlagNotification,
        "power_wait_flag": PowerWaitFlagNotification,
        "game_message_received": GameMessageReceivedNotification,
        "vote_updated": VoteUpdatedNotification,
        "vote_count_updated": VoteCountUpdatedNotification,
        "power_vote_updated": PowerVoteUpdatedNotification,
        "game_deleted": GameDeletedNotification,
        "omniscient_updated": OmniscientUpdatedNotification,
        "account_deleted": AccountDeletedNotification,
        "cleared_centers": ClearedCentersNotification,
        "cleared_orders": ClearedOrdersNotification,
        "cleared_units": ClearedUnitsNotification,
    }

    message_class = message_classes.get(message_name)
    if message_class is None:
        raise ValueError(f"Unknown message type: {message_name}")

    return message_class(**data)


def serialize_message(message: WebSocketMessage) -> Dict[str, Any]:
    """
    Serialize a pydantic message object to a dictionary for WebSocket transmission.

    Args:
        message: Pydantic message object

    Returns:
        Dictionary representation of the message
    """
    return message.model_dump(exclude_none=True)
