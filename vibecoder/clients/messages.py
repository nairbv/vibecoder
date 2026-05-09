"""Provider-neutral message types for vibecoder.clients.

These are the canonical representation of conversation history. Each
provider client converts to/from its own wire format at the boundary,
so a history can survive switching providers mid-session.

Design notes:
- Each ClientMessage is a single yieldable unit. A logical assistant
  "turn" may produce several (Reasoning, then TextOutput, then
  ToolCall, ...). Clients append every yielded message to history in
  order, which is what the per-provider converters assume.
- `Usage` is attached only to messages that the provider reports usage
  for (typically the terminating message of an API call). Clients sum
  across messages when computing totals.
- Server-side tools (web_search, code_interpreter, google_search) are
  represented as ServerToolUse / ServerToolResult — the Client yields
  them but does not execute them; the provider runs them server-side.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    reasoning_tokens: int = 0


@dataclass
class ClientMessage(ABC):
    """Base class for all messages flowing through a Client."""

    usage: Optional[Usage] = None


# --- User input parts ---


@dataclass
class UserText(ClientMessage):
    """A text message from the user."""

    content: str = ""


@dataclass
class UserImage(ClientMessage):
    """An image attached to a user turn.

    Either `data` (raw bytes) + `media_type`, or `url` for hosted images.
    """

    data: Optional[bytes] = None
    media_type: Optional[str] = None  # e.g. "image/png"
    url: Optional[str] = None


@dataclass
class UserFile(ClientMessage):
    """A file attached to a user turn (PDFs, docs).

    Either `data` (raw bytes) + `media_type` + `filename`, or `url`.
    """

    data: Optional[bytes] = None
    media_type: Optional[str] = None
    filename: Optional[str] = None
    url: Optional[str] = None


# --- Assistant output parts ---


@dataclass
class TextOutput(ClientMessage):
    """A text response from the assistant."""

    content: str = ""


@dataclass
class Reasoning(ClientMessage):
    """A reasoning / thinking block from the assistant.

    Different providers expose reasoning differently:
    - OpenAI Responses returns opaque reasoning items keyed by id; the
      visible `summary` (if any) is plaintext, and the full reasoning is
      passed back via `id` reference.
    - Anthropic returns `thinking` blocks with plaintext + a signature
      that must be echoed back to use the reasoning in subsequent turns.
    - Gemini returns `thought` parts with plaintext.

    `content` is the human-readable summary/thoughts. `signature` and
    `provider_id` carry the opaque pass-through state needed to use
    this reasoning on a follow-up call.
    """

    content: str = ""
    signature: Optional[str] = None  # Anthropic thinking signature
    provider_id: Optional[str] = None  # OpenAI reasoning item id
    encrypted_content: Optional[str] = None  # OpenAI encrypted_content
    redacted: bool = False  # Anthropic redacted thinking


# --- Tool calling (client-side, executed locally) ---


@dataclass
class ToolCall(ClientMessage):
    """A request from the assistant to invoke a local tool."""

    tool_name: str = ""
    tool_call_id: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolOutput(ClientMessage):
    """Result of executing a local tool, returned to the assistant."""

    tool_name: str = ""
    tool_call_id: str = ""
    content: str = ""
    is_error: bool = False


# --- Server-side tools (executed by the provider, not us) ---


@dataclass
class ServerToolUse(ClientMessage):
    """A server-side tool invocation reported by the provider.

    We yield these for visibility/logging but do not execute them.
    """

    tool_name: str = ""  # e.g. "web_search", "code_interpreter"
    tool_call_id: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class ServerToolResult(ClientMessage):
    """Result of a server-side tool, reported by the provider."""

    tool_name: str = ""
    tool_call_id: str = ""
    content: str = ""
    is_error: bool = False


# --- Convenience aliases / type unions ---

USER_PARTS = (UserText, UserImage, UserFile)
ASSISTANT_PARTS = (
    TextOutput,
    Reasoning,
    ToolCall,
    ServerToolUse,
    ServerToolResult,
)
TOOL_PARTS = (ToolOutput,)
