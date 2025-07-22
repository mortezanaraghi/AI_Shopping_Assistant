"""
Distributed State Manager
Manages conversation state, user profiles, and agent insights using Redis with in-memory fallback.
"""
from __future__ import annotations
import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

from .utils.logging import init_logger
from .models import (
    ConversationContext, UserProfile, AgentInsight, InteractionEvent,
    PurchaseEvent, ProductRecommendation, SearchContext
)

log = init_logger()

class DistributedStateManager:
    """
    Centralized state management using Redis for scalability and persistence.
    Handles caching, conversation history, and user profiles.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._redis_client: Optional[redis.Redis] = None
        
        # TTL configurations for different data types
        self.ttl_config = {
            "recommendations": 1800,  # 30 minutes
            "conversation": 86400,    # 24 hours
            "user_profile": 604800,   # 7 days
            "product_data": 14400,    # 4 hours
            "agent_insights": 3600,   # 1 hour
            "temp_data": 300          # 5 minutes
        }
    
    async def _get_redis_client(self) -> redis.Redis:
        """Get or create Redis client connection."""
        if self._redis_client is None:
            self._redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5.0,
                retry_on_timeout=True,
                max_connections=20
            )
        return self._redis_client
    
    async def close(self):
        """Close Redis connection."""
        if self._redis_client:
            await self._redis_client.close()
    
    # ─── Recommendation Caching ─────────────────────────────────────
    async def cache_recommendations(
        self, 
        cache_key: str, 
        recommendations: List[ProductRecommendation],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache product recommendations with expiration."""
        try:
            redis_client = await self._get_redis_client()
            ttl = ttl or self.ttl_config["recommendations"]
            
            # Serialize recommendations
            data = [rec.model_dump() for rec in recommendations]
            serialized = json.dumps(data, default=str)
            
            # Store with expiration
            await redis_client.setex(
                f"recommendations:{cache_key}",
                ttl,
                serialized
            )
            
            log.debug(f"Cached {len(recommendations)} recommendations for key: {cache_key}")
            return True
            
        except Exception as e:
            log.error(f"Failed to cache recommendations: {e}")
            return False
    
    async def get_cached_recommendations(self, cache_key: str) -> Optional[List[ProductRecommendation]]:
        """Retrieve cached recommendations."""
        try:
            redis_client = await self._get_redis_client()
            cached_data = await redis_client.get(f"recommendations:{cache_key}")
            
            if cached_data:
                data = json.loads(cached_data)
                return [ProductRecommendation.model_validate(item) for item in data]
            
            return None
            
        except Exception as e:
            log.error(f"Failed to retrieve cached recommendations: {e}")
            return None
    
    def generate_cache_key(self, user_query: UserQuery, context: Dict[str, Any] = None) -> str:
        """Generate a deterministic cache key for queries."""
        key_components = [
            user_query.text,
            user_query.user_id or "anonymous",
            json.dumps(user_query.extracted_entities, sort_keys=True),
            json.dumps(context or {}, sort_keys=True, default=str)
        ]
        
        key_string = "|".join(key_components)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    # ─── Conversation State Management ──────────────────────────────
    async def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history for a session."""
        try:
            redis_client = await self._get_redis_client()
            
            # Get conversation messages (stored as a list)
            messages = await redis_client.lrange(f"conversation:{session_id}", 0, limit - 1)
            
            # Parse messages
            history = []
            for message in messages:
                try:
                    parsed_message = json.loads(message)
                    history.append(parsed_message)
                except json.JSONDecodeError:
                    log.warning(f"Failed to parse conversation message: {message}")
            
            return history
            
        except Exception as e:
            log.error(f"Failed to get conversation history: {e}")
            return []
    
    async def append_to_conversation(
        self, 
        session_id: str, 
        message: Dict[str, Any]
    ) -> bool:
        """Add a message to conversation history."""
        try:
            redis_client = await self._get_redis_client()
            
            # Add timestamp if not present
            if "timestamp" not in message:
                message["timestamp"] = datetime.now().isoformat()
            
            # Add session_id to message for cross-session tracking
            message["session_id"] = session_id
            
            # Serialize message
            serialized_message = json.dumps(message, default=str)
            
            # Add to conversation list (newest first)
            await redis_client.lpush(f"conversation:{session_id}", serialized_message)
            
            # Trim to keep only recent messages (limit to 100)
            await redis_client.ltrim(f"conversation:{session_id}", 0, 99)
            
            # Set expiration for the conversation
            await redis_client.expire(
                f"conversation:{session_id}",
                self.ttl_config["conversation"]
            )
            
            return True
            
        except Exception as e:
            log.error(f"Failed to append to conversation: {e}")
            return False
    
    async def clear_conversation(self, session_id: str) -> bool:
        """Clear conversation history for a session."""
        try:
            redis_client = await self._get_redis_client()
            await redis_client.delete(f"conversation:{session_id}")
            return True
        except Exception as e:
            log.error(f"Failed to clear conversation: {e}")
            return False
    
    # ─── User Profile Management ────────────────────────────────────
    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile from storage."""
        try:
            redis_client = await self._get_redis_client()
            profile_data = await redis_client.get(f"user_profile:{user_id}")
            
            if profile_data:
                data = json.loads(profile_data)
                return UserProfile.model_validate(data)
            
            return None
            
        except Exception as e:
            log.error(f"Failed to get user profile: {e}")
            return None
    
    async def update_user_profile(self, user_profile: UserProfile) -> bool:
        """Save or update user profile."""
        try:
            redis_client = await self._get_redis_client()
            
            # Update last_updated timestamp
            user_profile.last_updated = datetime.now()
            
            # Serialize profile
            serialized = json.dumps(user_profile.model_dump(), default=str)
            
            # Store with expiration
            await redis_client.setex(
                f"user_profile:{user_profile.user_id}",
                self.ttl_config["user_profile"],
                serialized
            )
            
            log.debug(f"Updated profile for user: {user_profile.user_id}")
            return True
            
        except Exception as e:
            log.error(f"Failed to update user profile: {e}")
            return False
    
    async def create_user_profile(self, user_id: str, initial_query: Optional[str] = None) -> UserProfile:
        """Create a new user profile with optional initial query for cold start."""
        # Create basic profile
        profile = UserProfile(user_id=user_id)
        
        # If initial query provided, use it for cold start preferences
        if initial_query:
            try:
                from personalization import PersonalizationEngine
                personalization_engine = PersonalizationEngine()
                cold_start_profile = await personalization_engine.cold_start(
                    UserRequirements(query=initial_query, user_id=user_id)
                )
                # Transfer cold start preferences to our profile
                if hasattr(cold_start_profile, 'prefs'):
                    profile.preferences = cold_start_profile.prefs
            except ImportError:
                log.warning("PersonalizationEngine not available for cold start")
            
            profile.record_interaction("search", query=initial_query, session_id="initial")
        
        # Save the new profile
        await self.update_user_profile(profile)
        return profile
    
    async def get_user_conversation_history(
        self, 
        user_id: str, 
        limit: int = 50, 
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """Get conversation history across all sessions for a user."""
        try:
            redis_client = await self._get_redis_client()
            
            # Get all session keys for this user (scan for pattern)
            cursor = 0
            session_keys = []
            while True:
                cursor, keys = await redis_client.scan(
                    cursor, match=f"conversation:*", count=100
                )
                session_keys.extend(keys)
                if cursor == 0:
                    break
            
            # Collect all messages from user's sessions
            all_messages = []
            cutoff_time = datetime.now() - timedelta(days=days_back)
            
            for session_key in session_keys:
                try:
                    # Get messages from this session
                    messages = await redis_client.lrange(session_key, 0, -1)
                    
                    for message in messages:
                        try:
                            parsed_message = json.loads(message)
                            
                            # Check if message belongs to this user and is recent
                            msg_time = datetime.fromisoformat(parsed_message.get("timestamp", "1970-01-01"))
                            if (parsed_message.get("user_id") == user_id and 
                                msg_time >= cutoff_time):
                                all_messages.append(parsed_message)
                                
                        except (json.JSONDecodeError, ValueError):
                            continue
                            
                except Exception:
                    continue
            
            # Sort by timestamp (newest first) and limit
            all_messages.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return all_messages[:limit]
            
        except Exception as e:
            log.error(f"Failed to get user conversation history: {e}")
            return []
    
    async def load_user_context(
        self, 
        user_id: str, 
        session_id: str, 
        initial_query: Optional[str] = None
    ) -> 'ConversationContext':
        """Load comprehensive user context across sessions."""
        from models import ConversationContext
        
        # Load or create user profile
        user_profile = await self.get_user_profile(user_id)
        if not user_profile:
            user_profile = await self.create_user_profile(user_id, initial_query)
        
        # Load recent conversation history across sessions
        recent_history = await self.get_user_conversation_history(
            user_id, limit=20, days_back=7
        )
        
        # Load current session history
        session_history = await self.get_conversation_history(session_id, limit=10)
        
        # Combine and prioritize current session
        combined_history = session_history + [
            msg for msg in recent_history 
            if msg.get("session_id") != session_id
        ][:30]  # Limit total history
        
        return ConversationContext(
            session_id=session_id,
            user_id=user_id,
            history=combined_history,
            user_profile=user_profile,
            metadata={
                "session_count": user_profile.recency,
                "last_active": user_profile.last_updated.isoformat() if user_profile.last_updated else None,
                "expertise_level": user_profile.expertise_level,
                "profile_completeness": user_profile.completeness
            }
        )
    
    async def record_user_interaction(
        self, 
        user_id: str, 
        event_type: str, 
        product_id: Optional[int] = None,
        query: Optional[str] = None,
        session_id: str = "",
        confidence: Optional[float] = None
    ) -> bool:
        """Record user interaction and update profile."""
        try:
            # Get user profile
            user_profile = await self.get_user_profile(user_id)
            if not user_profile:
                user_profile = await self.create_user_profile(user_id, query)
            
            # Record the interaction
            user_profile.record_interaction(event_type, product_id, query, session_id, confidence)
            
            # Update profile
            return await self.update_user_profile(user_profile)
            
        except Exception as e:
            log.error(f"Failed to record user interaction: {e}")
            return False
    
    # ─── Agent Context and Insights ─────────────────────────────────
    async def store_agent_insight(
        self, 
        session_id: str, 
        agent_insight: AgentInsight
    ) -> bool:
        """Store agent insights for a session."""
        try:
            redis_client = await self._get_redis_client()
            
            # Serialize insight
            serialized = json.dumps(agent_insight.model_dump(), default=str)
            
            # Store in hash for the session
            await redis_client.hset(
                f"agent_insights:{session_id}",
                agent_insight.agent_id,
                serialized
            )
            
            # Set expiration
            await redis_client.expire(
                f"agent_insights:{session_id}",
                self.ttl_config["agent_insights"]
            )
            
            return True
            
        except Exception as e:
            log.error(f"Failed to store agent insight: {e}")
            return False
    
    async def get_agent_insights(self, session_id: str) -> Dict[str, AgentInsight]:
        """Get all agent insights for a session."""
        try:
            redis_client = await self._get_redis_client()
            
            # Get all insights for the session
            insights_data = await redis_client.hgetall(f"agent_insights:{session_id}")
            
            insights = {}
            for agent_id, serialized_insight in insights_data.items():
                try:
                    data = json.loads(serialized_insight)
                    insights[agent_id] = AgentInsight.model_validate(data)
                except (json.JSONDecodeError, ValueError) as e:
                    log.warning(f"Failed to parse agent insight for {agent_id}: {e}")
            
            return insights
            
        except Exception as e:
            log.error(f"Failed to get agent insights: {e}")
            return {}
    
    # ─── Generic Caching Methods ────────────────────────────────────
    async def set_cache(
        self, 
        key: str, 
        data: Any, 
        ttl: int = 300,
        namespace: str = "general"
    ) -> bool:
        """Generic cache setter."""
        try:
            redis_client = await self._get_redis_client()
            
            # Serialize data
            serialized = json.dumps(data, default=str)
            
            # Store with namespace
            cache_key = f"{namespace}:{key}"
            await redis_client.setex(cache_key, ttl, serialized)
            
            return True
            
        except Exception as e:
            log.error(f"Failed to set cache for {key}: {e}")
            return False
    
    async def get_cache(self, key: str, namespace: str = "general") -> Any:
        """Generic cache getter."""
        try:
            redis_client = await self._get_redis_client()
            cache_key = f"{namespace}:{key}"
            cached_data = await redis_client.get(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            log.error(f"Failed to get cache for {key}: {e}")
            return None
    
    async def delete_cache(self, key: str, namespace: str = "general") -> bool:
        """Delete cache entry."""
        try:
            redis_client = await self._get_redis_client()
            cache_key = f"{namespace}:{key}"
            await redis_client.delete(cache_key)
            return True
        except Exception as e:
            log.error(f"Failed to delete cache for {key}: {e}")
            return False
    
    # ─── Health and Maintenance ─────────────────────────────────────
    async def health_check(self) -> bool:
        """Check if Redis connection is healthy."""
        try:
            redis_client = await self._get_redis_client()
            await redis_client.ping()
            return True
        except Exception as e:
            log.error(f"Redis health check failed: {e}")
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            redis_client = await self._get_redis_client()
            
            # Get basic info
            info = await redis_client.info()
            
            # Count keys by namespace
            key_counts = {}
            for namespace in ["recommendations", "conversation", "user_profile", "agent_insights"]:
                keys = await redis_client.keys(f"{namespace}:*")
                key_counts[namespace] = len(keys)
            
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "unknown"),
                "key_counts": key_counts,
                "hit_rate": info.get("keyspace_hits", 0) / max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0))
            }
            
        except Exception as e:
            log.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}
    
    async def cleanup_expired_keys(self) -> int:
        """Manually cleanup expired keys (Redis does this automatically, but this can help)."""
        try:
            redis_client = await self._get_redis_client()
            
            # Get all keys and check expiration
            all_keys = await redis_client.keys("*")
            expired_count = 0
            
            for key in all_keys:
                ttl = await redis_client.ttl(key)
                if ttl == -2:  # Key doesn't exist (expired and removed)
                    expired_count += 1
            
            return expired_count
            
        except Exception as e:
            log.error(f"Failed to cleanup expired keys: {e}")
            return 0 