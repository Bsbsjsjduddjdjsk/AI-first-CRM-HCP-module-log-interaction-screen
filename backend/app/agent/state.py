from typing import TypedDict, Optional, List, Any
from typing_extensions import Annotated
import operator


class AgentState(TypedDict, total=False):
    session_id: str
    rep_id: str

    # running chat transcript, appended to across turns
    messages: Annotated[List[dict], operator.add]

    # what the router decided this turn: log_interaction | edit_interaction |
    # query_history | schedule_follow_up | compliance_check | clarify
    intent: Optional[str]

    # extracted / partially-built interaction payload
    draft_record: Optional[dict]

    # existing interaction_id, when editing
    target_interaction_id: Optional[str]

    # HCP context pulled from fetch_hcp_history tool
    hcp_context: Optional[dict]

    # whether we're waiting on the rep to confirm before we persist
    awaiting_confirmation: bool

    # compliance flags raised this turn
    compliance_flags: Optional[List[dict]]

    # final message to show the rep
    agent_reply: Optional[str]
