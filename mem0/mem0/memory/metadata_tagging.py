"""
Enhanced metadata tagging system for autonomous AI memory storage.
This module provides advanced metadata tagging and semantic enrichment.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict
import json
import hashlib

from mem0.configs.coding_config import CodingMemoryConfig

logger = logging.getLogger(__name__)


def _safe_datetime_now(reference_time: Optional[datetime] = None) -> datetime:
    """
    Safely get current datetime with proper timezone handling.
    
    Args:
        reference_time: Optional reference datetime to match timezone
        
    Returns:
        Current datetime with proper timezone handling
    """
    if reference_time is None:
        return datetime.now()
    
    # Handle timezone-aware reference time
    if reference_time.tzinfo is not None:
        return datetime.now(reference_time.tzinfo)
    
    # Handle timezone-naive reference time - return naive datetime
    return datetime.now()


def _safe_datetime_diff(dt1: datetime, dt2: datetime) -> timedelta:
    """
    Safely calculate difference between two datetimes, handling timezone mismatches.
    
    Args:
        dt1: First datetime
        dt2: Second datetime
        
    Returns:
        Time difference as timedelta
    """
    # If both are naive or both are aware, calculate normally
    if (dt1.tzinfo is None) == (dt2.tzinfo is None):
        return dt1 - dt2
    
    # If one is aware and other is naive, convert naive to aware (UTC)
    if dt1.tzinfo is None:
        dt1 = dt1.replace(tzinfo=dt2.tzinfo)
    elif dt2.tzinfo is None:
        dt2 = dt2.replace(tzinfo=dt1.tzinfo)
    
    return dt1 - dt2


class SemanticTagger:
    """
    Semantic tagging system for autonomous AI memory storage.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.coding_config = CodingMemoryConfig()
        
        # Semantic tag categories
        self.semantic_categories = {
            'technical_concepts': {
                'patterns': [
                    r'\b(algorithm|data structure|design pattern|architecture)\b',
                    r'\b(recursion|iteration|optimization|complexity)\b',
                    r'\b(inheritance|polymorphism|encapsulation|abstraction)\b'
                ],
                'weight': 0.9
            },
            'problem_solving': {
                'patterns': [
                    r'\b(problem|solution|approach|strategy)\b',
                    r'\b(debug|troubleshoot|diagnose|analyze)\b',
                    r'\b(implement|develop|build|create)\b'
                ],
                'weight': 0.85
            },
            'error_handling': {
                'patterns': [
                    r'\b(error|exception|bug|issue|fault)\b',
                    r'\b(try|catch|handle|raise|throw)\b',
                    r'\b(validation|sanitization|check)\b'
                ],
                'weight': 0.9
            },
            'performance': {
                'patterns': [
                    r'\b(performance|speed|optimization|efficiency)\b',
                    r'\b(memory|cpu|resource|benchmark)\b',
                    r'\b(cache|buffer|pool|queue)\b'
                ],
                'weight': 0.8
            },
            'testing': {
                'patterns': [
                    r'\b(test|testing|spec|assert|verify)\b',
                    r'\b(mock|stub|fixture|double)\b',
                    r'\b(unit|integration|e2e|regression)\b'
                ],
                'weight': 0.75
            },
            'documentation': {
                'patterns': [
                    r'\b(document|documentation|readme|guide)\b',
                    r'\b(comment|docstring|annotation|note)\b',
                    r'\b(example|tutorial|howto|manual)\b'
                ],
                'weight': 0.7
            }
        }
        
        # Technology-specific tags
        self.technology_tags = {
            'languages': {
                'python': [r'\bpython\b', r'\bpy\b', r'\.py\b', r'\bpytest\b', r'\bpip\b'],
                'javascript': [r'\bjavascript\b', r'\bjs\b', r'\.js\b', r'\bnpm\b', r'\bnode\b'],
                'typescript': [r'\btypescript\b', r'\bts\b', r'\.ts\b', r'\btsc\b'],
                'java': [r'\bjava\b', r'\.java\b', r'\bmaven\b', r'\bgradle\b'],
                'cpp': [r'\bc\+\+\b', r'\bcpp\b', r'\.cpp\b', r'\bg\+\+\b'],
                'go': [r'\bgolang\b', r'\bgo\b', r'\.go\b', r'\bmod\b'],
                'rust': [r'\brust\b', r'\.rs\b', r'\bcargo\b'],
                'php': [r'\bphp\b', r'\.php\b', r'\bcomposer\b']
            },
            'frameworks': {
                'react': [r'\breact\b', r'\bjsx\b', r'\breact[\-\s]native\b'],
                'vue': [r'\bvue\b', r'\bvuejs\b', r'\bnuxt\b'],
                'angular': [r'\bangular\b', r'\bangularjs\b', r'\bionic\b'],
                'django': [r'\bdjango\b', r'\bdrf\b'],
                'flask': [r'\bflask\b', r'\bjinja\b'],
                'fastapi': [r'\bfastapi\b', r'\bfast[\s\-]api\b'],
                'express': [r'\bexpress\b', r'\bexpress\.js\b'],
                'spring': [r'\bspring\b', r'\bspring[\s\-]boot\b']
            },
            'databases': {
                'postgresql': [r'\bpostgresql\b', r'\bpostgres\b', r'\bpsql\b'],
                'mysql': [r'\bmysql\b', r'\bmariadb\b'],
                'mongodb': [r'\bmongodb\b', r'\bmongo\b', r'\bnosql\b'],
                'redis': [r'\bredis\b', r'\bcache\b'],
                'sqlite': [r'\bsqlite\b', r'\bsql\b']
            },
            'tools': {
                'docker': [r'\bdocker\b', r'\bcontainer\b', r'\bdockerfile\b'],
                'kubernetes': [r'\bkubernetes\b', r'\bk8s\b', r'\bkubectl\b'],
                'git': [r'\bgit\b', r'\bgithub\b', r'\bversion\s+control\b'],
                'aws': [r'\baws\b', r'\bamazon\b', r'\bec2\b', r'\bs3\b'],
                'terraform': [r'\bterraform\b', r'\binfrastructure\b']
            }
        }
        
        # Context-specific tags
        self.context_tags = {
            'urgency': {
                'critical': [r'\bcritical\b', r'\burgent\b', r'\bemergency\b', r'\bimmediate\b'],
                'high': [r'\bhigh\s+priority\b', r'\bimportant\b', r'\bpriority\b'],
                'medium': [r'\bmedium\b', r'\bnormal\b', r'\broutine\b'],
                'low': [r'\blow\s+priority\b', r'\bnice\s+to\s+have\b', r'\boptional\b']
            },
            'complexity': {
                'simple': [r'\bsimple\b', r'\beasy\b', r'\bstraightforward\b', r'\bbasic\b'],
                'medium': [r'\bmedium\b', r'\bmoderate\b', r'\bintermediate\b'],
                'complex': [r'\bcomplex\b', r'\badvanced\b', r'\bsophisticated\b', r'\bdifficult\b']
            },
            'scope': {
                'local': [r'\blocal\b', r'\bfunction\b', r'\bmethod\b', r'\bvariable\b'],
                'module': [r'\bmodule\b', r'\bpackage\b', r'\bnamespace\b'],
                'system': [r'\bsystem\b', r'\barchitecture\b', r'\bapplication\b', r'\bservice\b']
            }
        }
        
        # Auto-tagging rules
        self.auto_tagging_rules = {
            'file_extension_tags': True,
            'error_detection_tags': True,
            'solution_detection_tags': True,
            'code_pattern_tags': True,
            'temporal_tags': True,
            'quality_tags': True
        }
        
        # Tag statistics
        self.tag_stats = {
            'total_tagged': 0,
            'tag_frequency': defaultdict(int),
            'tag_combinations': defaultdict(int),
            'auto_tag_accuracy': 0.0
        }
        
        logger.info("Semantic tagger initialized")
    
    def tag_memory(
        self,
        memory_content: str,
        metadata: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive tags for memory content.
        
        Args:
            memory_content: The memory content to tag
            metadata: Memory metadata
            context: Optional context for tagging
            
        Returns:
            Dictionary containing all generated tags
        """
        context = context or {}
        
        # Extract semantic tags
        semantic_tags = self._extract_semantic_tags(memory_content)
        
        # Extract technology tags
        technology_tags = self._extract_technology_tags(memory_content, metadata)
        
        # Extract context tags
        context_tags = self._extract_context_tags(memory_content, context)
        
        # Generate auto-tags
        auto_tags = self._generate_auto_tags(memory_content, metadata, context)
        
        # Generate quality tags
        quality_tags = self._generate_quality_tags(memory_content, metadata)
        
        # Generate relationship tags
        relationship_tags = self._generate_relationship_tags(metadata, context)
        
        # Combine all tags
        all_tags = {
            'semantic': semantic_tags,
            'technology': technology_tags,
            'context': context_tags,
            'auto': auto_tags,
            'quality': quality_tags,
            'relationship': relationship_tags
        }
        
        # Calculate tag confidence
        tag_confidence = self._calculate_tag_confidence(all_tags, memory_content)
        
        # Update statistics
        self._update_tag_statistics(all_tags)
        
        return {
            'tags': all_tags,
            'confidence': tag_confidence,
            'tag_summary': self._generate_tag_summary(all_tags),
            'recommended_tags': self._recommend_additional_tags(all_tags, memory_content)
        }
    
    def _extract_semantic_tags(self, content: str) -> Dict[str, Any]:
        """
        Extract semantic tags from content.
        """
        semantic_tags = {}
        content_lower = content.lower()
        
        for category, config in self.semantic_categories.items():
            patterns = config['patterns']
            weight = config['weight']
            
            matches = []
            for pattern in patterns:
                found_matches = re.findall(pattern, content_lower, re.IGNORECASE)
                matches.extend(found_matches)
            
            if matches:
                semantic_tags[category] = {
                    'matches': list(set(matches)),
                    'count': len(matches),
                    'weight': weight,
                    'confidence': min(len(matches) / 3, 1.0) * weight
                }
        
        return semantic_tags
    
    def _extract_technology_tags(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract technology-specific tags.
        """
        technology_tags = {}
        content_lower = content.lower()
        
        for tech_category, technologies in self.technology_tags.items():
            category_tags = {}
            
            for tech_name, patterns in technologies.items():
                for pattern in patterns:
                    if re.search(pattern, content_lower, re.IGNORECASE):
                        category_tags[tech_name] = {
                            'detected': True,
                            'confidence': 0.8,
                            'source': 'content_analysis'
                        }
                        break
            
            if category_tags:
                technology_tags[tech_category] = category_tags
        
        # Add tags from file references
        file_refs = metadata.get('file_references', [])
        if file_refs:
            file_extension_tags = {}
            for file_ref in file_refs:
                for tech_category, technologies in self.technology_tags.items():
                    for tech_name, patterns in technologies.items():
                        for pattern in patterns:
                            if re.search(pattern, file_ref, re.IGNORECASE):
                                file_extension_tags[tech_name] = {
                                    'detected': True,
                                    'confidence': 0.9,
                                    'source': 'file_reference'
                                }
            
            if file_extension_tags:
                if 'languages' not in technology_tags:
                    technology_tags['languages'] = {}
                technology_tags['languages'].update(file_extension_tags)
        
        return technology_tags
    
    def _extract_context_tags(self, content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract context-specific tags.
        """
        context_tags = {}
        content_lower = content.lower()
        
        for context_category, contexts in self.context_tags.items():
            detected_contexts = {}
            
            for context_name, patterns in contexts.items():
                for pattern in patterns:
                    if re.search(pattern, content_lower, re.IGNORECASE):
                        detected_contexts[context_name] = {
                            'detected': True,
                            'confidence': 0.7,
                            'source': 'pattern_match'
                        }
                        break
            
            if detected_contexts:
                context_tags[context_category] = detected_contexts
        
        # Add context from explicit context parameter
        if context:
            explicit_context = {}
            for key, value in context.items():
                if key in ['urgency', 'complexity', 'scope']:
                    explicit_context[key] = {
                        'detected': True,
                        'confidence': 1.0,
                        'source': 'explicit_context',
                        'value': value
                    }
            
            if explicit_context:
                context_tags['explicit'] = explicit_context
        
        return context_tags
    
    def _generate_auto_tags(
        self,
        content: str,
        metadata: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate automatic tags based on rules.
        """
        auto_tags = {}
        
        # Error detection tags
        if self.auto_tagging_rules['error_detection_tags']:
            error_tags = self._detect_error_tags(content)
            if error_tags:
                auto_tags['error_detection'] = error_tags
        
        # Solution detection tags
        if self.auto_tagging_rules['solution_detection_tags']:
            solution_tags = self._detect_solution_tags(content)
            if solution_tags:
                auto_tags['solution_detection'] = solution_tags
        
        # Code pattern tags
        if self.auto_tagging_rules['code_pattern_tags']:
            code_pattern_tags = self._detect_code_patterns(content)
            if code_pattern_tags:
                auto_tags['code_patterns'] = code_pattern_tags
        
        # Temporal tags
        if self.auto_tagging_rules['temporal_tags']:
            temporal_tags = self._generate_temporal_tags(metadata)
            if temporal_tags:
                auto_tags['temporal'] = temporal_tags
        
        # Quality tags
        if self.auto_tagging_rules['quality_tags']:
            quality_tags = self._detect_quality_indicators(content)
            if quality_tags:
                auto_tags['quality_indicators'] = quality_tags
        
        return auto_tags
    
    def _detect_error_tags(self, content: str) -> Dict[str, Any]:
        """
        Detect error-related tags.
        """
        error_patterns = {
            'syntax_error': [r'\bsyntax\s+error\b', r'\bindentation\s+error\b', r'\bparsing\s+error\b'],
            'runtime_error': [r'\bruntime\s+error\b', r'\bexception\b', r'\bcrash\b'],
            'logic_error': [r'\blogic\s+error\b', r'\bwrong\s+result\b', r'\bincorrect\b'],
            'type_error': [r'\btype\s+error\b', r'\btype\s+mismatch\b', r'\bwrong\s+type\b'],
            'memory_error': [r'\bmemory\s+error\b', r'\bsegmentation\s+fault\b', r'\bstack\s+overflow\b'],
            'network_error': [r'\bnetwork\s+error\b', r'\bconnection\s+error\b', r'\btimeout\b']
        }
        
        detected_errors = {}
        content_lower = content.lower()
        
        for error_type, patterns in error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    detected_errors[error_type] = {
                        'detected': True,
                        'confidence': 0.85,
                        'pattern': pattern
                    }
                    break
        
        return detected_errors
    
    def _detect_solution_tags(self, content: str) -> Dict[str, Any]:
        """
        Detect solution-related tags.
        """
        solution_patterns = {
            'workaround': [r'\bworkaround\b', r'\btemporary\s+fix\b', r'\bquick\s+fix\b'],
            'permanent_fix': [r'\bpermanent\s+fix\b', r'\bproper\s+solution\b', r'\bfinal\s+fix\b'],
            'patch': [r'\bpatch\b', r'\bhotfix\b', r'\bband\-aid\b'],
            'optimization': [r'\boptimization\b', r'\bimprovement\b', r'\benhancement\b'],
            'refactoring': [r'\brefactor\b', r'\bcleanup\b', r'\brestructure\b'],
            'configuration': [r'\bconfiguration\s+change\b', r'\bsetting\s+update\b', r'\bparameter\s+adjustment\b']
        }
        
        detected_solutions = {}
        content_lower = content.lower()
        
        for solution_type, patterns in solution_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    detected_solutions[solution_type] = {
                        'detected': True,
                        'confidence': 0.8,
                        'pattern': pattern
                    }
                    break
        
        return detected_solutions
    
    def _detect_code_patterns(self, content: str) -> Dict[str, Any]:
        """
        Detect code-related patterns.
        """
        code_patterns = {
            'function_definition': [r'\bdef\s+\w+\(', r'\bfunction\s+\w+\(', r'\w+\s*\([^)]*\)\s*\{'],
            'class_definition': [r'\bclass\s+\w+', r'\binterface\s+\w+', r'\bstruct\s+\w+'],
            'import_statement': [r'\bimport\s+\w+', r'\bfrom\s+\w+\s+import', r'\b#include\s*<'],
            'variable_declaration': [r'\bvar\s+\w+', r'\blet\s+\w+', r'\bconst\s+\w+'],
            'loop_construct': [r'\bfor\s+\w+\s+in\b', r'\bwhile\s*\(', r'\bdo\s*\{'],
            'conditional': [r'\bif\s*\(', r'\belse\s+if\b', r'\bswitch\s*\('],
            'error_handling': [r'\btry\s*\{', r'\bcatch\s*\(', r'\bfinally\s*\{'],
            'async_pattern': [r'\basync\s+\w+', r'\bawait\s+\w+', r'\bPromise\s*\<']
        }
        
        detected_patterns = {}
        
        for pattern_type, patterns in code_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    detected_patterns[pattern_type] = {
                        'detected': True,
                        'confidence': 0.9,
                        'pattern': pattern
                    }
                    break
        
        return detected_patterns
    
    def _generate_temporal_tags(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate temporal tags based on metadata.
        """
        temporal_tags = {}
        
        created_at = metadata.get('created_at')
        if created_at:
            try:
                created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                current_time = _safe_datetime_now(created_time)
                
                age_hours = _safe_datetime_diff(current_time, created_time).total_seconds() / 3600
                
                if age_hours < 1:
                    temporal_tags['freshness'] = 'fresh'
                elif age_hours < 24:
                    temporal_tags['freshness'] = 'recent'
                elif age_hours < 168:  # 1 week
                    temporal_tags['freshness'] = 'current'
                elif age_hours < 720:  # 1 month
                    temporal_tags['freshness'] = 'aging'
                else:
                    temporal_tags['freshness'] = 'old'
                
                # Add specific time periods
                if age_hours < 24:
                    temporal_tags['period'] = 'today'
                elif age_hours < 168:
                    temporal_tags['period'] = 'this_week'
                elif age_hours < 720:
                    temporal_tags['period'] = 'this_month'
                else:
                    temporal_tags['period'] = 'older'
                
            except Exception:
                temporal_tags['freshness'] = 'unknown'
        
        return temporal_tags
    
    def _detect_quality_indicators(self, content: str) -> Dict[str, Any]:
        """
        Detect quality indicators in content.
        """
        quality_indicators = {}
        
        # Content length assessment
        length = len(content)
        if length < 50:
            quality_indicators['length'] = 'short'
        elif length < 200:
            quality_indicators['length'] = 'medium'
        elif length < 500:
            quality_indicators['length'] = 'long'
        else:
            quality_indicators['length'] = 'very_long'
        
        # Detail level assessment
        detail_patterns = [
            r'\bstep\s+\d+', r'\bfirst\b', r'\bsecond\b', r'\bthen\b',
            r'\bfor\s+example\b', r'\bspecifically\b', r'\bnamely\b'
        ]
        
        detail_count = sum(1 for pattern in detail_patterns 
                          if re.search(pattern, content, re.IGNORECASE))
        
        if detail_count >= 3:
            quality_indicators['detail_level'] = 'high'
        elif detail_count >= 1:
            quality_indicators['detail_level'] = 'medium'
        else:
            quality_indicators['detail_level'] = 'low'
        
        # Code quality indicators
        code_quality_patterns = [
            r'\bbest\s+practice\b', r'\bclean\s+code\b', r'\bcode\s+review\b',
            r'\boptimize\b', r'\bperformance\b', r'\befficient\b'
        ]
        
        if any(re.search(pattern, content, re.IGNORECASE) for pattern in code_quality_patterns):
            quality_indicators['code_quality'] = 'high'
        
        return quality_indicators
    
    def _generate_quality_tags(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate quality-related tags.
        """
        quality_tags = {}
        
        # Content completeness
        completeness_indicators = [
            r'\bcomplete\b', r'\bfinished\b', r'\bfinal\b', r'\bdone\b'
        ]
        
        if any(re.search(pattern, content, re.IGNORECASE) for pattern in completeness_indicators):
            quality_tags['completeness'] = 'complete'
        elif any(word in content.lower() for word in ['partial', 'incomplete', 'draft', 'wip']):
            quality_tags['completeness'] = 'partial'
        else:
            quality_tags['completeness'] = 'unknown'
        
        # Accuracy indicators
        accuracy_indicators = [
            r'\bverified\b', r'\btested\b', r'\bconfirmed\b', r'\bvalidated\b'
        ]
        
        if any(re.search(pattern, content, re.IGNORECASE) for pattern in accuracy_indicators):
            quality_tags['accuracy'] = 'verified'
        elif any(word in content.lower() for word in ['untested', 'unverified', 'uncertain']):
            quality_tags['accuracy'] = 'uncertain'
        else:
            quality_tags['accuracy'] = 'unknown'
        
        # Usefulness indicators
        usefulness_indicators = [
            r'\buseful\b', r'\bhelpful\b', r'\bvaluable\b', r'\bimportant\b'
        ]
        
        if any(re.search(pattern, content, re.IGNORECASE) for pattern in usefulness_indicators):
            quality_tags['usefulness'] = 'high'
        
        return quality_tags
    
    def _generate_relationship_tags(self, metadata: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate relationship tags based on metadata and context.
        """
        relationship_tags = {}
        
        # File relationship tags
        file_refs = metadata.get('file_references', [])
        if file_refs:
            relationship_tags['file_count'] = len(file_refs)
            
            # Determine file relationship type
            if len(file_refs) == 1:
                relationship_tags['file_scope'] = 'single_file'
            elif len(file_refs) <= 3:
                relationship_tags['file_scope'] = 'few_files'
            else:
                relationship_tags['file_scope'] = 'many_files'
        
        # Category relationship
        category = metadata.get('category')
        if category:
            relationship_tags['primary_category'] = category
        
        # Context relationships
        if context:
            if context.get('session_id'):
                relationship_tags['session_scoped'] = True
            
            if context.get('project_id'):
                relationship_tags['project_scoped'] = True
            
            if context.get('user_id'):
                relationship_tags['user_scoped'] = True
        
        return relationship_tags
    
    def _calculate_tag_confidence(self, all_tags: Dict[str, Any], content: str) -> Dict[str, float]:
        """
        Calculate confidence scores for different tag categories.
        """
        confidence_scores = {}
        
        # Semantic tags confidence
        semantic_confidence = 0.0
        if 'semantic' in all_tags:
            total_weight = sum(tag_info['weight'] for tag_info in all_tags['semantic'].values())
            semantic_confidence = min(total_weight / 3, 1.0)
        confidence_scores['semantic'] = semantic_confidence
        
        # Technology tags confidence
        tech_confidence = 0.0
        if 'technology' in all_tags:
            tech_count = sum(len(category) for category in all_tags['technology'].values())
            tech_confidence = min(tech_count / 5, 1.0)
        confidence_scores['technology'] = tech_confidence
        
        # Auto tags confidence
        auto_confidence = 0.0
        if 'auto' in all_tags:
            auto_count = sum(len(category) for category in all_tags['auto'].values())
            auto_confidence = min(auto_count / 3, 1.0)
        confidence_scores['auto'] = auto_confidence
        
        # Overall confidence
        confidence_scores['overall'] = sum(confidence_scores.values()) / len(confidence_scores)
        
        return confidence_scores
    
    def _generate_tag_summary(self, all_tags: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a summary of all tags.
        """
        summary = {
            'total_categories': len(all_tags),
            'total_tags': 0,
            'primary_tags': [],
            'tag_distribution': {}
        }
        
        for category, tags in all_tags.items():
            if isinstance(tags, dict):
                tag_count = len(tags)
                summary['total_tags'] += tag_count
                summary['tag_distribution'][category] = tag_count
                
                # Add primary tags (most confident ones)
                if category == 'semantic':
                    for tag_name, tag_info in tags.items():
                        if tag_info.get('confidence', 0) > 0.7:
                            summary['primary_tags'].append(f"{category}:{tag_name}")
                elif category == 'technology':
                    for tech_category, tech_tags in tags.items():
                        for tech_name, tech_info in tech_tags.items():
                            if tech_info.get('confidence', 0) > 0.8:
                                summary['primary_tags'].append(f"{tech_category}:{tech_name}")
        
        return summary
    
    def _recommend_additional_tags(self, all_tags: Dict[str, Any], content: str) -> List[str]:
        """
        Recommend additional tags that might be relevant.
        """
        recommendations = []
        
        # Check for missing common patterns
        content_lower = content.lower()
        
        # Recommend testing tags if code patterns are detected
        if 'auto' in all_tags and 'code_patterns' in all_tags['auto']:
            if not any('test' in str(tags) for tags in all_tags.values()):
                if any(word in content_lower for word in ['test', 'spec', 'assert']):
                    recommendations.append('testing:unit_test')
        
        # Recommend performance tags if optimization mentioned
        if any(word in content_lower for word in ['slow', 'fast', 'performance', 'optimize']):
            if 'performance' not in all_tags.get('semantic', {}):
                recommendations.append('semantic:performance')
        
        # Recommend documentation tags if explanation is detailed
        if len(content) > 200 and any(word in content_lower for word in ['example', 'how to', 'guide']):
            if 'documentation' not in all_tags.get('semantic', {}):
                recommendations.append('semantic:documentation')
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _update_tag_statistics(self, all_tags: Dict[str, Any]):
        """
        Update tag usage statistics.
        """
        self.tag_stats['total_tagged'] += 1
        
        # Update frequency for each tag
        for category, tags in all_tags.items():
            if isinstance(tags, dict):
                for tag_name in tags.keys():
                    full_tag = f"{category}:{tag_name}"
                    self.tag_stats['tag_frequency'][full_tag] += 1
        
        # Update tag combinations (simple pairs)
        all_tag_names = []
        for category, tags in all_tags.items():
            if isinstance(tags, dict):
                for tag_name in tags.keys():
                    all_tag_names.append(f"{category}:{tag_name}")
        
        # Record combinations of most frequent tags
        if len(all_tag_names) > 1:
            primary_tags = sorted(all_tag_names)[:3]  # Take top 3
            for i in range(len(primary_tags)):
                for j in range(i + 1, len(primary_tags)):
                    combo = f"{primary_tags[i]}+{primary_tags[j]}"
                    self.tag_stats['tag_combinations'][combo] += 1
    
    def get_tag_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive tag statistics.
        """
        return {
            'total_tagged': self.tag_stats['total_tagged'],
            'most_frequent_tags': sorted(
                self.tag_stats['tag_frequency'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            'most_frequent_combinations': sorted(
                self.tag_stats['tag_combinations'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            'tag_categories': list(self.semantic_categories.keys()),
            'auto_tagging_accuracy': self.tag_stats['auto_tag_accuracy']
        }
    
    def update_tagging_rules(self, new_rules: Dict[str, Any]):
        """
        Update auto-tagging rules.
        """
        self.auto_tagging_rules.update(new_rules)
        logger.info(f"Updated auto-tagging rules: {new_rules}")
    
    def add_custom_semantic_category(self, category_name: str, patterns: List[str], weight: float):
        """
        Add a custom semantic category.
        """
        self.semantic_categories[category_name] = {
            'patterns': patterns,
            'weight': weight
        }
        logger.info(f"Added custom semantic category: {category_name}")
    
    def reset_statistics(self):
        """
        Reset tag statistics.
        """
        self.tag_stats = {
            'total_tagged': 0,
            'tag_frequency': defaultdict(int),
            'tag_combinations': defaultdict(int),
            'auto_tag_accuracy': 0.0
        }
        logger.info("Tag statistics reset")


class AutoTaggingManager:
    """
    Autonomous tagging manager for AI agents.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.semantic_tagger = SemanticTagger(config)
        
        # Learning parameters
        self.learning_enabled = config.get('enable_learning', True)
        self.feedback_history = []
        self.tag_performance = defaultdict(lambda: {'correct': 0, 'total': 0})
        
        # Auto-tagging thresholds
        self.auto_thresholds = {
            'high_confidence': 0.9,
            'medium_confidence': 0.7,
            'low_confidence': 0.5,
            'auto_tag_threshold': 0.8
        }
        
        # Tag validation
        self.tag_validation_rules = {
            'max_tags_per_category': 5,
            'max_total_tags': 20,
            'min_confidence_for_auto': 0.7
        }
    
    def auto_tag_memory(
        self,
        memory_content: str,
        metadata: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Automatically tag memory with confidence-based decisions.
        """
        # Generate tags
        tagging_result = self.semantic_tagger.tag_memory(memory_content, metadata, context)
        
        # Apply auto-tagging logic
        auto_tagged = self._apply_auto_tagging_logic(tagging_result)
        
        # Validate tags
        validated_tags = self._validate_tags(auto_tagged['tags'])
        
        # Generate final result
        result = {
            'auto_tags': validated_tags,
            'confidence': tagging_result['confidence'],
            'tag_summary': tagging_result['tag_summary'],
            'recommendations': tagging_result['recommended_tags'],
            'auto_tagging_decision': auto_tagged['decision'],
            'validation_results': auto_tagged['validation']
        }
        
        # Record for learning
        if self.learning_enabled:
            self._record_auto_tagging(result, memory_content, metadata)
        
        return result
    
    def _apply_auto_tagging_logic(self, tagging_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply logic to determine which tags to auto-apply.
        """
        confidence = tagging_result['confidence']
        all_tags = tagging_result['tags']
        
        # Determine auto-tagging decision
        overall_confidence = confidence.get('overall', 0.0)
        
        if overall_confidence >= self.auto_thresholds['high_confidence']:
            decision = 'auto_tag_all'
            approved_tags = all_tags
        elif overall_confidence >= self.auto_thresholds['medium_confidence']:
            decision = 'auto_tag_high_confidence'
            approved_tags = self._filter_high_confidence_tags(all_tags)
        elif overall_confidence >= self.auto_thresholds['low_confidence']:
            decision = 'suggest_with_review'
            approved_tags = self._filter_medium_confidence_tags(all_tags)
        else:
            decision = 'manual_tagging_required'
            approved_tags = {}
        
        return {
            'decision': decision,
            'tags': approved_tags,
            'validation': self._validate_auto_decision(decision, overall_confidence)
        }
    
    def _filter_high_confidence_tags(self, all_tags: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter tags with high confidence for auto-tagging.
        """
        filtered_tags = {}
        
        for category, tags in all_tags.items():
            if isinstance(tags, dict):
                high_confidence_tags = {}
                
                for tag_name, tag_info in tags.items():
                    if isinstance(tag_info, dict):
                        tag_confidence = tag_info.get('confidence', 0.0)
                        if tag_confidence >= self.auto_thresholds['auto_tag_threshold']:
                            high_confidence_tags[tag_name] = tag_info
                    else:
                        # For simple tags without confidence scores
                        high_confidence_tags[tag_name] = tag_info
                
                if high_confidence_tags:
                    filtered_tags[category] = high_confidence_tags
        
        return filtered_tags
    
    def _filter_medium_confidence_tags(self, all_tags: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter tags with medium confidence for suggestion.
        """
        filtered_tags = {}
        
        for category, tags in all_tags.items():
            if isinstance(tags, dict):
                medium_confidence_tags = {}
                
                for tag_name, tag_info in tags.items():
                    if isinstance(tag_info, dict):
                        tag_confidence = tag_info.get('confidence', 0.0)
                        if tag_confidence >= self.auto_thresholds['medium_confidence']:
                            medium_confidence_tags[tag_name] = tag_info
                    else:
                        # For simple tags, include them
                        medium_confidence_tags[tag_name] = tag_info
                
                if medium_confidence_tags:
                    filtered_tags[category] = medium_confidence_tags
        
        return filtered_tags
    
    def _validate_tags(self, tags: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate tags against validation rules.
        """
        validated_tags = {}
        
        for category, category_tags in tags.items():
            if isinstance(category_tags, dict):
                # Limit tags per category
                max_tags = self.tag_validation_rules['max_tags_per_category']
                if len(category_tags) > max_tags:
                    # Keep highest confidence tags
                    sorted_tags = sorted(
                        category_tags.items(),
                        key=lambda x: x[1].get('confidence', 0) if isinstance(x[1], dict) else 0,
                        reverse=True
                    )
                    validated_tags[category] = dict(sorted_tags[:max_tags])
                else:
                    validated_tags[category] = category_tags
        
        return validated_tags
    
    def _validate_auto_decision(self, decision: str, confidence: float) -> Dict[str, Any]:
        """
        Validate auto-tagging decision.
        """
        validation = {
            'decision_valid': True,
            'confidence_appropriate': True,
            'warnings': []
        }
        
        # Check if decision matches confidence
        if decision == 'auto_tag_all' and confidence < self.auto_thresholds['high_confidence']:
            validation['decision_valid'] = False
            validation['warnings'].append('Decision too aggressive for confidence level')
        
        if decision == 'manual_tagging_required' and confidence > self.auto_thresholds['medium_confidence']:
            validation['confidence_appropriate'] = False
            validation['warnings'].append('Confidence level suggests auto-tagging is possible')
        
        return validation
    
    def _record_auto_tagging(self, result: Dict[str, Any], content: str, metadata: Dict[str, Any]):
        """
        Record auto-tagging decision for learning.
        """
        record = {
            'timestamp': datetime.now().isoformat(),
            'decision': result['auto_tagging_decision'],
            'confidence': result['confidence']['overall'],
            'content_length': len(content),
            'category': metadata.get('category', 'unknown'),
            'tag_count': sum(len(tags) for tags in result['auto_tags'].values() if isinstance(tags, dict))
        }
        
        self.feedback_history.append(record)
        
        # Keep only recent history
        if len(self.feedback_history) > 1000:
            self.feedback_history = self.feedback_history[-1000:]
    
    def provide_feedback(self, memory_id: str, correct_tags: List[str], incorrect_tags: List[str]):
        """
        Provide feedback on auto-tagging performance.
        """
        # Update performance metrics
        for tag in correct_tags:
            self.tag_performance[tag]['correct'] += 1
            self.tag_performance[tag]['total'] += 1
        
        for tag in incorrect_tags:
            self.tag_performance[tag]['total'] += 1
        
        # Adapt thresholds based on performance
        if self.learning_enabled:
            self._adapt_thresholds_based_on_feedback()
        
        logger.info(f"Feedback recorded for memory {memory_id}: {len(correct_tags)} correct, {len(incorrect_tags)} incorrect")
    
    def _adapt_thresholds_based_on_feedback(self):
        """
        Adapt auto-tagging thresholds based on feedback.
        """
        # Calculate overall accuracy
        total_correct = sum(perf['correct'] for perf in self.tag_performance.values())
        total_attempts = sum(perf['total'] for perf in self.tag_performance.values())
        
        if total_attempts < 10:  # Need minimum feedback
            return
        
        accuracy = total_correct / total_attempts
        
        # Adjust thresholds
        if accuracy > 0.9:
            # High accuracy, can be more aggressive
            self.auto_thresholds['auto_tag_threshold'] = max(
                self.auto_thresholds['auto_tag_threshold'] - 0.05,
                0.6
            )
        elif accuracy < 0.7:
            # Low accuracy, be more conservative
            self.auto_thresholds['auto_tag_threshold'] = min(
                self.auto_thresholds['auto_tag_threshold'] + 0.05,
                0.95
            )
        
        logger.info(f"Adapted auto-tagging thresholds based on accuracy: {accuracy:.3f}")
    
    def get_performance_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive performance analytics.
        """
        # Calculate tag accuracy
        tag_accuracy = {}
        for tag, performance in self.tag_performance.items():
            if performance['total'] > 0:
                tag_accuracy[tag] = performance['correct'] / performance['total']
        
        # Calculate overall statistics
        total_correct = sum(perf['correct'] for perf in self.tag_performance.values())
        total_attempts = sum(perf['total'] for perf in self.tag_performance.values())
        overall_accuracy = total_correct / total_attempts if total_attempts > 0 else 0.0
        
        return {
            'overall_accuracy': overall_accuracy,
            'total_attempts': total_attempts,
            'tag_accuracy': tag_accuracy,
            'current_thresholds': self.auto_thresholds,
            'learning_enabled': self.learning_enabled,
            'feedback_history_size': len(self.feedback_history)
        }
    
    def reset_learning_data(self):
        """
        Reset learning data.
        """
        self.feedback_history.clear()
        self.tag_performance.clear()
        logger.info("Auto-tagging learning data reset")