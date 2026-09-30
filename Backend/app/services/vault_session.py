import time
from typing import Dict
from pydantic import BaseModel

class VaultSession(BaseModel):
    evidence_id: int
    user_id: int
    dek: bytes
    expires_at: float

class VaultSessionManager:
    def __init__(self):
        # Maps session_token (or evidence_id_user_id) to VaultSession
        self._sessions: Dict[str, VaultSession] = {}

    def _generate_key(self, evidence_id: int, user_id: int) -> str:
        return f"{evidence_id}_{user_id}"

    def create_session(self, evidence_id: int, user_id: int, dek: bytes, timeout_minutes: int = 10) -> None:
        key = self._generate_key(evidence_id, user_id)
        expires_at = time.time() + (timeout_minutes * 60)
        self._sessions[key] = VaultSession(
            evidence_id=evidence_id,
            user_id=user_id,
            dek=dek,
            expires_at=expires_at
        )

    def get_session_dek(self, evidence_id: int, user_id: int) -> bytes | None:
        key = self._generate_key(evidence_id, user_id)
        session = self._sessions.get(key)
        
        if not session:
            return None
            
        if time.time() > session.expires_at:
            # Session expired
            self.revoke_session(evidence_id, user_id)
            return None
            
        return session.dek

    def revoke_session(self, evidence_id: int, user_id: int) -> bool:
        key = self._generate_key(evidence_id, user_id)
        if key in self._sessions:
            # Overwrite DEK memory conceptually (Python makes this tricky, but we dereference)
            self._sessions[key].dek = b"" 
            del self._sessions[key]
            return True
        return False

vault_sessions = VaultSessionManager()
