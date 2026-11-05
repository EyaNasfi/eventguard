"""EventGuard gateway: the only path from the agent to EventSim (FR-GW-01).

Layout (S1-02):
    registry.py   tool registry: name, description, input schema, handler (plain data, SR-10)
    pipeline.py   ordered layer hooks before/after each call (all no-op in C0)
    platform.py   EventSim client protocol + HTTP implementation (NFR-10)
    identity.py   MCP bearer token -> EventSim user (SR-14, FR-GW-04)
    tools.py      the C0 tool set (FR-AGT-03)
    server.py     MCP server, Streamable HTTP transport
"""
