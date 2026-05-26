"""Bearer-token endpoint schemas. See SPEC §6.4 and §9.12."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from cap_backend.schemas.common import ASFUserID, IsoTimestamp


class TokenIssued(BaseModel):
    """Body returned by ``POST /token``.

    ``token`` is the bearer string the caller will present in the
    ``Authorization: bearer <token>`` header. It is shown exactly once
    (the server keeps no persistent record of the plaintext value, since
    the token store is in-memory only and resets on restart).
    """

    model_config = ConfigDict(extra="forbid")

    token: str
    uid: ASFUserID
    scopes: list[str]
    created_at: IsoTimestamp
    expires_at: IsoTimestamp
