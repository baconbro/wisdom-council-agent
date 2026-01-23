"""
Wisdom Council - Checkpointing System

Enables save/restore of agent state for crash recovery and long-running tasks.
"""

import sqlite3
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Checkpoint:
    """A saved checkpoint"""
    thread_id: str
    checkpoint_id: str
    state: dict
    timestamp: str
    step: int
    progress: float


class Checkpointer(ABC):
    """Abstract base class for checkpointing backends"""
    
    @abstractmethod
    async def save(self, thread_id: str, state: dict, checkpoint_id: str) -> None:
        """Save a checkpoint"""
        pass
    
    @abstractmethod
    async def get(self, thread_id: str, checkpoint_id: str) -> Optional[Checkpoint]:
        """Get a specific checkpoint"""
        pass
    
    @abstractmethod
    async def get_latest(self, thread_id: str) -> Optional[Checkpoint]:
        """Get the latest checkpoint for a thread"""
        pass
    
    @abstractmethod
    async def list(self, thread_id: str) -> list[Checkpoint]:
        """List all checkpoints for a thread"""
        pass
    
    @abstractmethod
    async def delete(self, thread_id: str, checkpoint_id: str) -> None:
        """Delete a checkpoint"""
        pass


class SqliteCheckpointer(Checkpointer):
    """SQLite-based checkpointer for local development"""
    
    def __init__(self, db_path: str = "./checkpoints", save_frequency: int = 5):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.db_file = self.db_path / "checkpoints.db"
        self.save_frequency = save_frequency
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                checkpoint_id TEXT NOT NULL,
                state TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                step INTEGER DEFAULT 0,
                progress REAL DEFAULT 0.0,
                UNIQUE(thread_id, checkpoint_id)
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_thread_id ON checkpoints(thread_id)
        """)
        conn.commit()
        conn.close()
    
    async def save(self, thread_id: str, state: dict, checkpoint_id: str) -> None:
        """Save a checkpoint to SQLite"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO checkpoints 
            (thread_id, checkpoint_id, state, timestamp, step, progress)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            thread_id,
            checkpoint_id,
            json.dumps(state),
            datetime.utcnow().isoformat(),
            state.get("step", 0),
            state.get("progress", 0.0)
        ))
        
        conn.commit()
        conn.close()
    
    async def get(self, thread_id: str, checkpoint_id: str) -> Optional[Checkpoint]:
        """Get a specific checkpoint"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT thread_id, checkpoint_id, state, timestamp, step, progress
            FROM checkpoints
            WHERE thread_id = ? AND checkpoint_id = ?
        """, (thread_id, checkpoint_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Checkpoint(
                thread_id=row[0],
                checkpoint_id=row[1],
                state=json.loads(row[2]),
                timestamp=row[3],
                step=row[4],
                progress=row[5]
            )
        return None
    
    async def get_latest(self, thread_id: str) -> Optional[Checkpoint]:
        """Get the latest checkpoint for a thread"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT thread_id, checkpoint_id, state, timestamp, step, progress
            FROM checkpoints
            WHERE thread_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (thread_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Checkpoint(
                thread_id=row[0],
                checkpoint_id=row[1],
                state=json.loads(row[2]),
                timestamp=row[3],
                step=row[4],
                progress=row[5]
            )
        return None
    
    async def list(self, thread_id: str) -> list[Checkpoint]:
        """List all checkpoints for a thread"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT thread_id, checkpoint_id, state, timestamp, step, progress
            FROM checkpoints
            WHERE thread_id = ?
            ORDER BY timestamp DESC
        """, (thread_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            Checkpoint(
                thread_id=row[0],
                checkpoint_id=row[1],
                state=json.loads(row[2]),
                timestamp=row[3],
                step=row[4],
                progress=row[5]
            )
            for row in rows
        ]
    
    async def delete(self, thread_id: str, checkpoint_id: str) -> None:
        """Delete a checkpoint"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM checkpoints
            WHERE thread_id = ? AND checkpoint_id = ?
        """, (thread_id, checkpoint_id))
        
        conn.commit()
        conn.close()


class RedisCheckpointer(Checkpointer):
    """Redis-based checkpointer for production"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, ttl: int = 86400):
        self.host = host
        self.port = port
        self.ttl = ttl
        # In production: initialize Redis client
    
    async def save(self, thread_id: str, state: dict, checkpoint_id: str) -> None:
        # Redis implementation
        pass
    
    async def get(self, thread_id: str, checkpoint_id: str) -> Optional[Checkpoint]:
        # Redis implementation
        pass
    
    async def get_latest(self, thread_id: str) -> Optional[Checkpoint]:
        # Redis implementation
        pass
    
    async def list(self, thread_id: str) -> list[Checkpoint]:
        # Redis implementation
        pass
    
    async def delete(self, thread_id: str, checkpoint_id: str) -> None:
        # Redis implementation
        pass
