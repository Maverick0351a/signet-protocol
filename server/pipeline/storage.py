#!/usr/bin/env python3
"""
Signet Protocol Storage Backend

Abstract storage interface with SQLite and PostgreSQL implementations
for receipts, billing data, and tenant configuration.
"""

import json
import sqlite3
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime


class StorageBackend(ABC):
    """Abstract storage backend interface"""
    
    @abstractmethod
    async def store_receipt(self, receipt_data: Dict[str, Any], idempotency_key: Optional[str] = None) -> None:
        """Store a receipt"""
        pass
    
    @abstractmethod
    async def get_receipt(self, receipt_id: str, api_key: str) -> Optional[Dict[str, Any]]:
        """Get a receipt by ID"""
        pass
    
    @abstractmethod
    async def get_by_idempotency_key(self, idempotency_key: str, api_key: str) -> Optional[Dict[str, Any]]:
        """Get receipt by idempotency key"""
        pass
    
    @abstractmethod
    async def list_receipts(self, api_key: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List receipts for API key"""
        pass
    
    @abstractmethod
    async def get_receipts_for_tenant(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Get all receipts for tenant"""
        pass
    
    @abstractmethod
    async def get_tenant_config(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Get tenant configuration"""
        pass
    
    @abstractmethod
    async def get_current_usage(self, api_key: str) -> Dict[str, int]:
        """Get current usage for tenant"""
        pass
    
    @abstractmethod
    async def record_usage(self, usage_record) -> None:
        """Record usage for billing"""
        pass
    
    @abstractmethod
    async def get_usage_summary(self, api_key: str, start_date: Optional[datetime], end_date: Optional[datetime]) -> Dict[str, Any]:
        """Get usage summary"""
        pass


class SQLiteStorage(StorageBackend):
    """SQLite storage implementation"""
    
    def __init__(self, db_path: str = "signet.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Receipts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS receipts (
                receipt_id TEXT PRIMARY KEY,
                trace_id TEXT NOT NULL,
                api_key TEXT NOT NULL,
                payload_type TEXT NOT NULL,
                target_type TEXT NOT NULL,
                receipt_data TEXT NOT NULL,
                idempotency_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(idempotency_key, api_key)
            )
        """)
        
        # Usage table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL,
                usage_type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                metadata TEXT
            )
        """)
        
        # Tenant config table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenant_config (
                api_key TEXT PRIMARY KEY,
                config_data TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def store_receipt(self, receipt_data: Dict[str, Any], idempotency_key: Optional[str] = None) -> None:
        """Store a receipt"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO receipts 
                (receipt_id, trace_id, api_key, payload_type, target_type, receipt_data, idempotency_key)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                receipt_data['receipt_id'],
                receipt_data['trace_id'],
                receipt_data['api_key'],
                receipt_data['payload_type'],
                receipt_data['target_type'],
                json.dumps(receipt_data),
                idempotency_key
            ))
            conn.commit()
        finally:
            conn.close()
    
    async def get_receipt(self, receipt_id: str, api_key: str) -> Optional[Dict[str, Any]]:
        """Get a receipt by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT receipt_data FROM receipts WHERE receipt_id = ? AND api_key = ?",
                (receipt_id, api_key)
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None
        finally:
            conn.close()
    
    async def get_by_idempotency_key(self, idempotency_key: str, api_key: str) -> Optional[Dict[str, Any]]:
        """Get receipt by idempotency key"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT receipt_data FROM receipts WHERE idempotency_key = ? AND api_key = ?",
                (idempotency_key, api_key)
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None
        finally:
            conn.close()
    
    async def list_receipts(self, api_key: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List receipts for API key"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT receipt_data FROM receipts WHERE api_key = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (api_key, limit, offset)
            )
            rows = cursor.fetchall()
            return [json.loads(row[0]) for row in rows]
        finally:
            conn.close()
    
    async def get_receipts_for_tenant(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Get all receipts for tenant"""
        return await self.list_receipts(tenant_id, limit=10000)
    
    async def get_tenant_config(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Get tenant configuration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT config_data FROM tenant_config WHERE api_key = ?",
                (api_key,)
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None
        finally:
            conn.close()
    
    async def get_current_usage(self, api_key: str) -> Dict[str, int]:
        """Get current usage for tenant"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT usage_type, SUM(amount) 
                FROM usage 
                WHERE tenant_id = ? AND timestamp >= date('now', 'start of month')
                GROUP BY usage_type
            """, (api_key,))
            
            usage = {'vex_used': 0, 'fu_used': 0}
            for usage_type, amount in cursor.fetchall():
                usage[f"{usage_type}_used"] = amount
            
            return usage
        finally:
            conn.close()
    
    async def record_usage(self, usage_record) -> None:
        """Record usage for billing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO usage (tenant_id, usage_type, amount, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                usage_record.tenant_id,
                usage_record.usage_type,
                usage_record.amount,
                usage_record.timestamp,
                json.dumps(usage_record.metadata) if usage_record.metadata else None
            ))
            conn.commit()
        finally:
            conn.close()
    
    async def get_usage_summary(self, api_key: str, start_date: Optional[datetime], end_date: Optional[datetime]) -> Dict[str, Any]:
        """Get usage summary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query = "SELECT usage_type, SUM(amount) FROM usage WHERE tenant_id = ?"
            params = [api_key]
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)
            
            query += " GROUP BY usage_type"
            
            cursor.execute(query, params)
            
            summary = {'vex_used': 0, 'fu_used': 0}
            for usage_type, amount in cursor.fetchall():
                summary[f"{usage_type}_used"] = amount
            
            return summary
        finally:
            conn.close()


def get_storage(database_url: str) -> StorageBackend:
    """Factory function to get storage backend"""
    if database_url.startswith('sqlite'):
        db_path = database_url.replace('sqlite:///', '')
        return SQLiteStorage(db_path)
    elif database_url.startswith('postgresql'):
        # Import PostgreSQL implementation if needed
        from .storage_postgres import PostgreSQLStorage
        return PostgreSQLStorage(database_url)
    else:
        # Default to SQLite
        return SQLiteStorage()