"""
Memory Retrieval - Local Memory Search and Retrieval
Vector-based semantic search with local scoring, not LLM-dependent
"""

from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import asyncio
from datetime import datetime, timedelta
import math
from collections import defaultdict


class RetrievalMethod(Enum):
    """Memory retrieval methods"""
    SEMANTIC = "semantic"  # Vector similarity
    EPISODIC = "episodic"  # Time-based sequence
    TEMPORAL = "temporal"  # Recent events
    ASSOCIATIVE = "associative"  # Related concepts
    HYBRID = "hybrid"  # Combination of methods


class MemoryRetrieval:
    """
    Memory retrieval system with multiple strategies
    Uses local vector similarity and scoring, not LLM-dependent
    """
    
    def __init__(self):
        self.memory_embeddings: Dict[str, Dict[str, List[float]]] = {}  # character_id -> memory_id -> embedding
        self.memory_index: Dict[str, Dict[str, List[str]]] = {}  # character_id -> term -> memory_ids
        self.temporal_index: Dict[str, List[Tuple[str, datetime]]] = {}  # character_id -> (memory_id, timestamp)
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize memory retrieval"""
        self.is_initialized = True
        print("Memory Retrieval initialized")
    
    async def shutdown(self):
        """Shutdown memory retrieval"""
        self.is_initialized = False
        print("Memory Retrieval shutdown")
    
    async def index_memory(
        self,
        character_id: str,
        memory_id: str,
        content: str,
        embedding: Optional[List[float]] = None,
        timestamp: Optional[datetime] = None
    ):
        """Index a memory for retrieval"""
        
        if embedding is None:
            # Generate simple embedding (word frequency based)
            embedding = self._generate_simple_embedding(content)
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Store embedding
        if character_id not in self.memory_embeddings:
            self.memory_embeddings[character_id] = {}
        
        self.memory_embeddings[character_id][memory_id] = embedding
        
        # Build inverted index
        if character_id not in self.memory_index:
            self.memory_index[character_id] = defaultdict(list)
        
        terms = self._extract_terms(content)
        for term in terms:
            self.memory_index[character_id][term].append(memory_id)
        
        # Build temporal index
        if character_id not in self.temporal_index:
            self.temporal_index[character_id] = []
        
        self.temporal_index[character_id].append((memory_id, timestamp))
        # Keep sorted by time
        self.temporal_index[character_id].sort(key=lambda x: x[1], reverse=True)
    
    async def retrieve_memories(
        self,
        character_id: str,
        query: str,
        method: RetrievalMethod = RetrievalMethod.HYBRID,
        limit: int = 5,
        time_window: Optional[timedelta] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve memories using specified method"""
        
        if character_id not in self.memory_embeddings:
            return []
        
        if method == RetrievalMethod.SEMANTIC:
            return await self._semantic_retrieval(character_id, query, limit)
        elif method == RetrievalMethod.EPISODIC:
            return await self._episodic_retrieval(character_id, query, limit, time_window)
        elif method == RetrievalMethod.TEMPORAL:
            return await self._temporal_retrieval(character_id, limit, time_window)
        elif method == RetrievalMethod.ASSOCIATIVE:
            return await self._associative_retrieval(character_id, query, limit)
        else:  # HYBRID
            return await self._hybrid_retrieval(character_id, query, limit, time_window)
    
    async def _semantic_retrieval(
        self,
        character_id: str,
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Semantic retrieval using vector similarity"""
        
        query_embedding = self._generate_simple_embedding(query)
        
        similarities = []
        for memory_id, memory_embedding in self.memory_embeddings[character_id].items():
            similarity = self._cosine_similarity(query_embedding, memory_embedding)
            similarities.append((memory_id, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Return top results
        results = []
        for memory_id, similarity in similarities[:limit]:
            results.append({
                "memory_id": memory_id,
                "relevance_score": similarity,
                "retrieval_method": "semantic"
            })
        
        return results
    
    async def _episodic_retrieval(
        self,
        character_id: str,
        query: str,
        limit: int,
        time_window: Optional[timedelta]
    ) -> List[Dict[str, Any]]:
        """Episodic retrieval - sequence of related memories"""
        
        # Get query terms
        query_terms = self._extract_terms(query)
        
        # Find memories with matching terms
        matching_memory_ids = set()
        for term in query_terms:
            if character_id in self.memory_index and term in self.memory_index[character_id]:
                matching_memory_ids.update(self.memory_index[character_id][term])
        
        # Apply time window if specified
        if time_window and character_id in self.temporal_index:
            cutoff_time = datetime.utcnow() - time_window
            recent_memories = [
                (mid, ts) for mid, ts in self.temporal_index[character_id]
                if ts > cutoff_time
            ]
            matching_memory_ids = matching_memory_ids.intersection(set(mid for mid, _ in recent_memories))
        
        # Convert to list and score
        results = []
        for memory_id in matching_memory_ids:
            # Score based on term overlap
            memory_embedding = self.memory_embeddings[character_id].get(memory_id)
            query_embedding = self._generate_simple_embedding(query)
            similarity = self._cosine_similarity(query_embedding, memory_embedding) if memory_embedding else 0.0
            
            results.append({
                "memory_id": memory_id,
                "relevance_score": similarity,
                "retrieval_method": "episodic"
            })
        
        # Sort and limit
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:limit]
    
    async def _temporal_retrieval(
        self,
        character_id: str,
        limit: int,
        time_window: Optional[timedelta]
    ) -> List[Dict[str, Any]]:
        """Temporal retrieval - most recent memories"""
        
        if character_id not in self.temporal_index:
            return []
        
        # Apply time window
        memories = self.temporal_index[character_id]
        if time_window:
            cutoff_time = datetime.utcnow() - time_window
            memories = [(mid, ts) for mid, ts in memories if ts > cutoff_time]
        
        # Return most recent
        results = []
        for memory_id, timestamp in memories[:limit]:
            # Decay score based on time
            time_diff = (datetime.utcnow() - timestamp).total_seconds()
            time_score = math.exp(-time_diff / 3600)  # Decay over hours
            
            results.append({
                "memory_id": memory_id,
                "relevance_score": time_score,
                "retrieval_method": "temporal",
                "timestamp": timestamp.isoformat()
            })
        
        return results
    
    async def _associative_retrieval(
        self,
        character_id: str,
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Associative retrieval - find related concepts"""
        
        query_terms = self._extract_terms(query)
        
        # Find related terms through co-occurrence
        related_memory_ids = set()
        
        if character_id in self.memory_index:
            for term in query_terms:
                if term in self.memory_index[character_id]:
                    # Get memories containing this term
                    term_memories = self.memory_index[character_id][term]
                    related_memory_ids.update(term_memories)
                    
                    # Find other terms that co-occur
                    for memory_id in term_memories:
                        # Find other terms in this memory
                        for other_term, other_memories in self.memory_index[character_id].items():
                            if memory_id in other_memories and other_term != term:
                                related_memory_ids.update(other_memories)
        
        # Score results
        results = []
        for memory_id in related_memory_ids:
            # Simple scoring based on co-occurrence count
            score = 1.0 / (len(related_memory_ids) + 1)  # Normalize
            
            results.append({
                "memory_id": memory_id,
                "relevance_score": score,
                "retrieval_method": "associative"
            })
        
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:limit]
    
    async def _hybrid_retrieval(
        self,
        character_id: str,
        query: str,
        limit: int,
        time_window: Optional[timedelta]
    ) -> List[Dict[str, Any]]:
        """Hybrid retrieval - combine multiple methods"""
        
        # Get results from different methods
        semantic_results = await self._semantic_retrieval(character_id, query, limit * 2)
        temporal_results = await self._temporal_retrieval(character_id, limit * 2, time_window)
        associative_results = await self._associative_retrieval(character_id, query, limit * 2)
        
        # Combine and re-score
        combined_scores = defaultdict(float)
        method_counts = defaultdict(int)
        
        for result in semantic_results:
            combined_scores[result["memory_id"]] += result["relevance_score"] * 0.5
            method_counts[result["memory_id"]] += 1
        
        for result in temporal_results:
            combined_scores[result["memory_id"]] += result["relevance_score"] * 0.3
            method_counts[result["memory_id"]] += 1
        
        for result in associative_results:
            combined_scores[result["memory_id"]] += result["relevance_score"] * 0.2
            method_counts[result["memory_id"]] += 1
        
        # Boost scores for memories found by multiple methods
        final_results = []
        for memory_id, score in combined_scores.items():
            # Boost by method count
            boosted_score = score * (1.0 + method_counts[memory_id] * 0.2)
            
            final_results.append({
                "memory_id": memory_id,
                "relevance_score": min(boosted_score, 1.0),
                "retrieval_method": "hybrid",
                "method_count": method_counts[memory_id]
            })
        
        # Sort and limit
        final_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return final_results[:limit]
    
    def _generate_simple_embedding(self, text: str) -> List[float]:
        """Generate enhanced embedding based on advanced local analysis"""
        # Enhanced local embedding with multiple features
        words = text.lower().split()
        
        # Feature 1: Word frequency with TF-IDF-like weighting
        word_freq = defaultdict(int)
        for word in words:
            word_freq[word] += 1
        
        # Feature 2: Character n-grams (2-grams and 3-grams)
        char_ngrams = []
        for word in words:
            for i in range(len(word) - 1):
                char_ngrams.append(word[i:i+2])  # 2-grams
            for i in range(len(word) - 2):
                char_ngrams.append(word[i:i+3])  # 3-grams
        
        # Feature 3: Position-weighted terms (beginning and end of text)
        position_weights = {}
        for i, word in enumerate(words):
            # Weight words at beginning and end higher
            position_weight = 1.0
            if i < len(words) * 0.2:  # First 20%
                position_weight = 1.5
            elif i > len(words) * 0.8:  # Last 20%
                position_weight = 1.3
            position_weights[word] = position_weight
        
        # Convert to fixed-size vector with multi-feature hashing
        embedding_size = 256  # Increased size for better representation
        embedding = [0.0] * embedding_size
        
        # Hash word frequencies
        for word, freq in word_freq.items():
            hash_val = hash(word) % embedding_size
            weight = position_weights.get(word, 1.0)
            embedding[hash_val] += freq * weight
        
        # Hash character n-grams
        for ngram in char_ngrams:
            hash_val = hash(f"ngram_{ngram}") % embedding_size
            embedding[hash_val] += 0.5
        
        # Add positional features
        if words:
            first_word_hash = hash(f"first_{words[0]}") % embedding_size
            last_word_hash = hash(f"last_{words[-1]}") % embedding_size
            embedding[first_word_hash] += 2.0
            embedding[last_word_hash] += 2.0
        
        # Add length feature
        length_hash = hash(f"length_{len(words)}") % embedding_size
        embedding[length_hash] += len(words) / 100.0
        
        # Normalize
        magnitude = math.sqrt(sum(x * x for x in embedding))
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]
        
        return embedding
    
    def _extract_terms(self, text: str) -> List[str]:
        """Extract terms from text with enhanced local processing"""
        # Enhanced tokenization and filtering
        words = text.lower().split()
        
        # Enhanced stop words list
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "shall", "can", "need", "dare",
            "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
            "from", "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "under", "again", "further", "then", "once",
            "here", "there", "when", "where", "why", "how", "all", "each", "every",
            "both", "few", "more", "most", "other", "some", "such", "no", "nor",
            "not", "only", "own", "same", "so", "than", "too", "very", "just"
        }
        
        # Filter and apply stemming (simplified)
        terms = []
        for word in words:
            if word not in stop_words and len(word) > 2:
                # Simple stemming: remove common suffixes
                suffixes = ["ing", "ed", "ly", "es", "s", "ment", "tion", "ness"]
                stemmed = word
                for suffix in suffixes:
                    if stemmed.endswith(suffix):
                        stemmed = stemmed[:-len(suffix)]
                        break  # Only remove one suffix
                
                if len(stemmed) > 2:  # Ensure stemmed word is still valid
                    terms.append(stemmed)
                else:
                    terms.append(word)
        
        return terms
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    async def remove_memory(self, character_id: str, memory_id: str):
        """Remove a memory from indexes"""
        if character_id in self.memory_embeddings and memory_id in self.memory_embeddings[character_id]:
            del self.memory_embeddings[character_id][memory_id]
        
        # Remove from inverted index
        if character_id in self.memory_index:
            for term in list(self.memory_index[character_id].keys()):
                if memory_id in self.memory_index[character_id][term]:
                    self.memory_index[character_id][term].remove(memory_id)
                    if not self.memory_index[character_id][term]:
                        del self.memory_index[character_id][term]
        
        # Remove from temporal index
        if character_id in self.temporal_index:
            self.temporal_index[character_id] = [
                (mid, ts) for mid, ts in self.temporal_index[character_id]
                if mid != memory_id
            ]
    
    async def clear_character_memories(self, character_id: str):
        """Clear all memories for a character"""
        if character_id in self.memory_embeddings:
            del self.memory_embeddings[character_id]
        if character_id in self.memory_index:
            del self.memory_index[character_id]
        if character_id in self.temporal_index:
            del self.temporal_index[character_id]