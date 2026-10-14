"""Create a ServiceNow incident for a flight anomaly event.

Ported from the SLB Maximo-ServiceNow integration pattern, simplified
to airline incident fields only. Uses a named WXO connection `service-now`
configured via Basic Auth.
"""

from typing import Optional

import requests
from pydantic import BaseModel, Field
from requests.auth import HTTPBasicAuth

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from ibm_watsonx_orchestrate.run import connections
from ibm_watsonx_orchestrate.agent_builder.connections import (
    ConnectionType,
    ExpectedCredentials,
)

CONNECTION_SNOW = "service-now"


class AirlineIncident(BaseModel):
    """A ServiceNow incident representing a flight anomaly event."""
    number:            str            = Field(..., description="ServiceNow incident number (INCxxxxxxx)")
    short_description: str            = Field(..., description="Brief summary of the incident")
    priority:          Optional[str]  = Field(None, description="Priority: 1=Critical, 2=High, 3=Moderate, 4=Low")
    urgency:           Optional[str]  = Field(None, description="Urgency: 1=High, 2=Medium, 3=Low")
    state:             Optional[str]  = Field(None, description="Incident state (New, In Progress, etc.)")
    opened_at:         str            = Field(..., description="When the incident was opened (ISO timestamp)")


@tool(
    name="create_service_now_incident",
    permission=ToolPermission.READ_WRITE,
    expected_credentials=[
        ExpectedCredentials(app_id=CONNECTION_SNOW, type=ConnectionType.BASIC_AUTH)
    ],
)
def create_service_now_incident(
    short_description: str,
    description: str,
    urgency: int = 2,
) -> AirlineIncident:
    """Create a new ServiceNow incident for a flight anomaly.

    Args:
        short_description: Brief title, e.g. '[HIGH] AX303 gate_wait anomaly at DFW'.
        description: Full structured triage summary from the Flight Triage Agent.
        urgency: 1=High (CRITICAL/HIGH severity), 2=Medium, 3=Low. Default 2.

    Returns:
        AirlineIncident with the new incident number and metadata.
    """
    creds    = connections.basic_auth(CONNECTION_SNOW)
    base_url = creds.url
    url      = f"{base_url}/api/now/table/incident"

    headers = {
        "Content-Type": "application/json",
        "Accept":       "application/json",
    }
    payload = {
        "short_description": short_description,
        "description":       description,
        "urgency":           urgency,
    }

    response = requests.post(
        url, headers=headers, json=payload,
        auth=HTTPBasicAuth(creds.username, creds.password),
    )
    response.raise_for_status()
    data   = response.json()["result"]
    sys_id = data["sys_id"]

    # Fetch the full record to return normalized fields
    get_resp = requests.get(
        f"{base_url}/api/now/table/incident/{sys_id}",
        headers=headers,
        auth=HTTPBasicAuth(creds.username, creds.password),
    )
    get_resp.raise_for_status()
    rec = get_resp.json()["result"]

    return AirlineIncident(
        number=rec.get("number", ""),
        short_description=rec.get("short_description", ""),
        priority=rec.get("priority"),
        urgency=str(rec.get("urgency", urgency)),
        state=rec.get("state"),
        opened_at=rec.get("opened_at", ""),
    )
