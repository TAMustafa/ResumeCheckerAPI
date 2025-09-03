"""
Enhanced skill matching with semantic similarity and fuzzy matching.
Following 2024 best practices for NLP-based skill taxonomy.
"""
import re
from typing import List, Tuple, Dict, Set
from dataclasses import dataclass
from difflib import SequenceMatcher
import asyncio
from functools import lru_cache
import math
from collections import Counter

@dataclass
class SkillMatch:
    """Represents a matched skill with confidence score."""
    original: str
    normalized: str
    confidence: float
    match_type: str  # 'exact', 'fuzzy', 'semantic', 'alias'

class EnhancedSkillTaxonomy:
    """
    Enhanced skill taxonomy with fuzzy matching, aliases, and semantic grouping.
    Follows 2024 best practices for skills-based hiring systems.
    """
    
    def __init__(self):
        # Core technical skills with common aliases and variations
        self._skill_aliases = {
            # Programming Languages
            "python": {"python", "py", "python3", "cpython", "python2"},
            "javascript": {"javascript", "js", "ecmascript", "node.js", "nodejs", "node"},
            "typescript": {"typescript", "ts"},
            "java": {"java", "openjdk", "oracle java"},
            "c#": {"c#", "csharp", "c sharp", ".net", "dotnet"},
            "c++": {"c++", "cpp", "cplusplus", "c plus plus"},
            "go": {"go", "golang", "go lang"},
            "rust": {"rust", "rust-lang"},
            "php": {"php", "php7", "php8"},
            "ruby": {"ruby", "ruby on rails", "rails"},
            "swift": {"swift", "ios swift"},
            "kotlin": {"kotlin", "android kotlin"},
            "scala": {"scala", "scala.js"},
            "r": {"r", "r programming", "r-lang"},
            
            # Databases
            "postgresql": {"postgresql", "postgres", "psql", "pg"},
            "mysql": {"mysql", "mariadb"},
            "mongodb": {"mongodb", "mongo", "mongo db"},
            "redis": {"redis", "redis cache"},
            "sqlite": {"sqlite", "sqlite3"},
            "oracle": {"oracle", "oracle db", "oracle database"},
            "cassandra": {"cassandra", "apache cassandra"},
            "elasticsearch": {"elasticsearch", "elastic search", "es"},
            
            # Cloud Platforms
            "aws": {"aws", "amazon web services", "amazon aws"},
            "azure": {"azure", "microsoft azure", "ms azure"},
            "gcp": {"gcp", "google cloud", "google cloud platform"},
            
            # DevOps & Infrastructure
            "docker": {"docker", "containerization", "containers"},
            "kubernetes": {"kubernetes", "k8s", "kube"},
            "terraform": {"terraform", "tf", "hcl"},
            "ansible": {"ansible", "ansible playbook"},
            "jenkins": {"jenkins", "jenkins ci/cd", "jenkins pipeline"},
            "git": {"git", "version control", "git scm"},
            "github": {"github", "github actions"},
            "gitlab": {"gitlab", "gitlab ci"},
            "circleci": {"circleci", "circle ci"},
            
            # Data & Analytics
            "apache spark": {"spark", "apache spark", "pyspark"},
            "hadoop": {"hadoop", "apache hadoop", "hdfs"},
            "kafka": {"kafka", "apache kafka"},
            "airflow": {"airflow", "apache airflow"},
            "tableau": {"tableau", "tableau desktop", "tableau server"},
            "power bi": {"power bi", "powerbi", "microsoft power bi"},
            "excel": {"excel", "microsoft excel", "ms excel"},
            
            # Web Technologies
            "react": {"react", "reactjs", "react.js"},
            "angular": {"angular", "angularjs", "angular.js"},
            "vue": {"vue", "vuejs", "vue.js"},
            "django": {"django", "django rest", "drf"},
            "flask": {"flask", "flask api"},
            "fastapi": {"fastapi", "fast api"},
            "express": {"express", "expressjs", "express.js"},
            "spring": {"spring", "spring boot", "spring framework"},
            
            # Operating Systems
            "linux": {"linux", "ubuntu", "centos", "rhel", "debian"},
            "windows": {"windows", "windows server", "microsoft windows"},
            "macos": {"macos", "mac os", "osx", "os x"},
            
            # Testing
            "pytest": {"pytest", "python testing"},
            "junit": {"junit", "java testing"},
            "selenium": {"selenium", "selenium webdriver"},
            "cypress": {"cypress", "cypress.io"},
            
            # Machine Learning
            "tensorflow": {"tensorflow", "tf", "keras"},
            "pytorch": {"pytorch", "torch"},
            "scikit-learn": {"scikit-learn", "sklearn", "scikit learn"},
            "pandas": {"pandas", "python pandas"},
            "numpy": {"numpy", "python numpy"},
        }
        
        # Skill categories for semantic grouping
        self._skill_categories = {
            "programming": {"python", "javascript", "typescript", "java", "c#", "c++", "go", "rust", "php", "ruby", "swift", "kotlin", "scala", "r"},
            "databases": {"postgresql", "mysql", "mongodb", "redis", "sqlite", "oracle", "cassandra", "elasticsearch"},
            "cloud": {"aws", "azure", "gcp"},
            "devops": {"docker", "kubernetes", "terraform", "ansible", "jenkins", "git", "github", "gitlab", "circleci"},
            "data_analytics": {"apache spark", "hadoop", "kafka", "airflow", "tableau", "power bi", "excel"},
            "web_frameworks": {"react", "angular", "vue", "django", "flask", "fastapi", "express", "spring"},
            "operating_systems": {"linux", "windows", "macos"},
            "testing": {"pytest", "junit", "selenium", "cypress"},
            "machine_learning": {"tensorflow", "pytorch", "scikit-learn", "pandas", "numpy"}
        }
        
        # Build normalized skill set
        self._normalized_skills = set(self._skill_aliases.keys())
        
        # Build reverse lookup for aliases
        self._alias_to_skill = {}
        for skill, aliases in self._skill_aliases.items():
            for alias in aliases:
                self._alias_to_skill[alias.lower()] = skill
    
    @lru_cache(maxsize=1000)
    def normalize_skill(self, skill: str) -> str:
        """Normalize a skill name to its canonical form."""
        if not skill:
            return ""
        
        clean_skill = re.sub(r'[^\w\s\+\#\.]', '', skill.lower().strip())
        clean_skill = re.sub(r'\s+', ' ', clean_skill)
        
        # Direct alias lookup
        if clean_skill in self._alias_to_skill:
            return self._alias_to_skill[clean_skill]
        
        return clean_skill
    
    def fuzzy_match_skill(self, skill: str, threshold: float = 0.7) -> List[SkillMatch]:
        """
        Find fuzzy matches for a skill using multiple techniques including semantic similarity.
        
        Args:
            skill: Input skill to match
            threshold: Minimum similarity threshold (0.0-1.0)
            
        Returns:
            List of SkillMatch objects sorted by confidence
        """
        if not skill or not skill.strip():
            return []
        
        normalized_input = self.normalize_skill(skill)
        matches = []
        
        # Check for exact match first
        if normalized_input in self._normalized_skills:
            matches.append(SkillMatch(
                original=skill,
                normalized=normalized_input,
                confidence=1.0,
                match_type='exact'
            ))
            return matches
        
        # Check alias matches
        if normalized_input in self._alias_to_skill:
            canonical = self._alias_to_skill[normalized_input]
            matches.append(SkillMatch(
                original=skill,
                normalized=canonical,
                confidence=0.95,
                match_type='alias'
            ))
        
        # If we found high-confidence match, return early unless threshold is very high
        if matches and matches[0].confidence >= 0.95 and threshold <= 0.8:
            return matches
        
        # Fuzzy matching using sequence matcher
        fuzzy_threshold = max(threshold, 0.7)  # Use higher threshold for fuzzy
        for canonical_skill in self._normalized_skills:
            similarity = SequenceMatcher(None, normalized_input, canonical_skill).ratio()
            
            if similarity >= fuzzy_threshold:
                matches.append(SkillMatch(
                    original=skill,
                    normalized=canonical_skill,
                    confidence=similarity,
                    match_type='fuzzy'
                ))
        
        # Add semantic matches if we don't have good fuzzy matches
        if not matches or matches[0].confidence < 0.8:
            semantic_matches = self.find_semantic_matches(skill, threshold=max(threshold, 0.6))
            matches.extend(semantic_matches)
        
        # Remove duplicates and sort by confidence (descending)
        seen_skills = set()
        unique_matches = []
        for match in sorted(matches, key=lambda x: x.confidence, reverse=True):
            if match.normalized not in seen_skills:
                unique_matches.append(match)
                seen_skills.add(match.normalized)
        
        return unique_matches[:3]  # Return top 3 matches
    
    def get_skill_category(self, skill: str) -> str:
        """Get the category for a normalized skill."""
        normalized = self.normalize_skill(skill)
        
        for category, skills in self._skill_categories.items():
            if normalized in skills:
                return category
        return "other"
    
    def get_related_skills(self, skill: str) -> List[str]:
        """Get skills in the same category as the input skill."""
        normalized = self.normalize_skill(skill)
        category = self.get_skill_category(normalized)
        
        if category == "other":
            return []
            
        related = list(self._skill_categories[category])
        if normalized in related:
            related.remove(normalized)
        return related
    
    def semantic_similarity(self, skill1: str, skill2: str) -> float:
        """
        Calculate semantic similarity between two skills using multiple techniques.
        Combines token-based similarity with domain knowledge.
        
        Args:
            skill1: First skill to compare
            skill2: Second skill to compare
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not skill1 or not skill2:
            return 0.0
            
        # Normalize inputs
        norm1 = self.normalize_skill(skill1)
        norm2 = self.normalize_skill(skill2)
        
        if norm1 == norm2:
            return 1.0
        
        # Check if both skills are in same category
        cat1 = self.get_skill_category(norm1)
        cat2 = self.get_skill_category(norm2)
        
        category_bonus = 0.3 if cat1 == cat2 and cat1 != "other" else 0.0
        
        # Calculate token-based similarity
        tokens1 = set(norm1.split())
        tokens2 = set(norm2.split())
        
        if not tokens1 or not tokens2:
            token_similarity = 0.0
        else:
            # Jaccard similarity
            intersection = len(tokens1.intersection(tokens2))
            union = len(tokens1.union(tokens2))
            token_similarity = intersection / union if union > 0 else 0.0
        
        # Calculate character-based similarity for single tokens
        char_similarity = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Weighted combination
        base_similarity = (token_similarity * 0.6 + char_similarity * 0.4)
        final_similarity = min(1.0, base_similarity + category_bonus)
        
        return final_similarity
    
    def find_semantic_matches(self, skill: str, threshold: float = 0.6) -> List[SkillMatch]:
        """
        Find semantically similar skills above threshold.
        
        Args:
            skill: Input skill to find matches for
            threshold: Minimum semantic similarity threshold
            
        Returns:
            List of semantically similar skills sorted by similarity
        """
        if not skill or not skill.strip():
            return []
        
        semantic_matches = []
        
        for canonical_skill in self._normalized_skills:
            similarity = self.semantic_similarity(skill, canonical_skill)
            
            if similarity >= threshold:
                match_type = 'semantic' if similarity < 0.9 else 'near_exact'
                semantic_matches.append(SkillMatch(
                    original=skill,
                    normalized=canonical_skill,
                    confidence=similarity,
                    match_type=match_type
                ))
        
        # Sort by similarity (descending)
        semantic_matches.sort(key=lambda x: x.confidence, reverse=True)
        return semantic_matches[:5]  # Return top 5 matches
    
    def validate_and_match_skills(self, skills: List[str]) -> Tuple[List[SkillMatch], List[str]]:
        """
        Validate and match a list of skills against the taxonomy.
        
        Args:
            skills: List of skill strings to validate
            
        Returns:
            Tuple of (matched_skills, unmatched_skills)
        """
        matched = []
        unmatched = []
        seen_normalized = set()
        
        for skill in skills:
            if not skill or not skill.strip():
                continue
                
            matches = self.fuzzy_match_skill(skill, threshold=0.7)
            
            if matches and matches[0].confidence >= 0.7:
                best_match = matches[0]
                # Avoid duplicates based on normalized form
                if best_match.normalized not in seen_normalized:
                    matched.append(best_match)
                    seen_normalized.add(best_match.normalized)
            else:
                unmatched.append(skill.strip())
        
        return matched, unmatched

# Global instance for use in agents.py
enhanced_taxonomy = EnhancedSkillTaxonomy()