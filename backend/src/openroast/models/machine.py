"""Pydantic model for user-saved machine configurations.

A SavedMachine represents a user's configured roasting machine — either
created from the catalog with optional overrides, or fully custom.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from openroast.models.catalog import (  # noqa: TC001
    ChannelConfig,
    ConnectionConfig,
    ControlConfig,
    ProtocolType,
)


class SavedMachine(BaseModel):
    """A user-configured roasting machine."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(description="User-assigned display name")

    # Catalog origin (None for fully custom machines)
    catalog_manufacturer_id: str | None = Field(default=None)
    catalog_model_id: str | None = Field(default=None)

    # Protocol and connection
    protocol: ProtocolType
    connection: ConnectionConfig
    sampling_interval_ms: int = Field(default=3000, ge=500, le=10000)

    # Channel mapping
    et: ChannelConfig | None = Field(default=None)
    bt: ChannelConfig | None = Field(default=None)
    extra_channels: list[ChannelConfig] = Field(default_factory=list)

    # Control sliders
    controls: list[ControlConfig] = Field(default_factory=list)
