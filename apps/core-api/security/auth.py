# Copyright 2025 ODIN Protocol Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from fastapi import Header, HTTPException

from ..settings import load_settings


def get_api_key(
    x_signet_api_key: str | None = Header(default=None, alias="X-SIGNET-API-Key"),
    x_odin_api_key: str | None = Header(default=None, alias="X-ODIN-API-Key"),
) -> str:
    """
    Extract API key from either X-SIGNET-API-Key or X-ODIN-API-Key headers.
    Supports both header names for backward compatibility.
    """
    api_key = x_signet_api_key or x_odin_api_key
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key header")

    # Validate API key exists in settings
    settings = load_settings()
    if api_key not in settings.api_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return api_key


def get_tenant_config(api_key: str):
    """Get tenant configuration for a validated API key."""
    settings = load_settings()
    return settings.api_keys[api_key]
