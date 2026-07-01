"""
Coder Agent - Code generation and analysis
Generates code, analyzes existing code, performs code reviews, and refactoring
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid
import ast
import re

from ...core.agent_base import BaseAgent, AgentMessage, MessageType


class CodeTaskType(Enum):
    """Types of code tasks"""
    GENERATION = "generation"
    ANALYSIS = "analysis"
    REFACTORING = "refactoring"
    DEBUGGING = "debugging"
    REVIEW = "review"
    DOCUMENTATION = "documentation"
    TESTING = "testing"


class CodeLanguage(Enum):
    """Programming languages"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CSHARP = "csharp"
    CPP = "cpp"
    GO = "go"
    RUST = "rust"
    SQL = "sql"
    HTML = "html"
    CSS = "css"


@dataclass
class CodeTask:
    """Represents a code task"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: CodeTaskType = CodeTaskType.GENERATION
    language: CodeLanguage = CodeLanguage.PYTHON
    description: str = ""
    requirements: List[str] = field(default_factory=list)
    input_code: Optional[str] = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "language": self.language.value,
            "description": self.description,
            "requirements": self.requirements,
            "input_code": self.input_code[:500] if self.input_code else None,
            "constraints": self.constraints,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class CodeResult:
    """Represents a code task result"""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    generated_code: str = ""
    analysis: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    issues: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "task_id": self.task_id,
            "generated_code": self.generated_code[:1000],  # Truncate for display
            "analysis": self.analysis,
            "suggestions": self.suggestions,
            "issues": self.issues,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


class CoderAgent(BaseAgent):
    """
    Coder Agent - Code generation and analysis
    Generates code, analyzes existing code, performs reviews and refactoring
    """
    
    def __init__(
        self,
        agent_id: str = "coder-agent-1",
        rabbitmq_url: str = "amqp://guest:guest@localhost:5672/",
        enable_tracing: bool = True,
        enable_metrics: bool = True
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="coder",
            rabbitmq_url=rabbitmq_url,
            enable_tracing=enable_tracing,
            enable_metrics=enable_metrics
        )
        
        # Task storage
        self.tasks: Dict[str, CodeTask] = {}
        self.results: Dict[str, CodeResult] = {}
        
        # Code templates and patterns
        self.code_templates = self._load_code_templates()
        
        # Code analysis patterns
        self.analysis_patterns = self._load_analysis_patterns()
        
        # Capabilities
        self.capabilities = [
            "code_generation",
            "code_analysis",
            "code_review",
            "refactoring",
            "debugging",
            "documentation_generation",
            "test_generation"
        ]
    
    def _load_code_templates(self) -> Dict[str, Dict[str, str]]:
        """Load code templates for different languages"""
        return {
            "python": {
                "function": '''def {function_name}({parameters}):
    """
    {description}
    """
    {body}
    return {return_value}''',
                "class": '''class {class_name}:
    """
    {description}
    """
    def __init__(self{init_parameters}):
        {init_body}
    
    {methods}''',
                "async_function": '''async def {function_name}({parameters}):
    """
    {description}
    """
    {body}
    return {return_value}'''
            },
            "javascript": {
                "function": '''function {function_name}({parameters}) {
    // {description}
    {body}
    return {return_value};
}''',
                "class": '''class {class_name} {
    /**
     * {description}
     */
    constructor({constructor_parameters}) {
        {constructor_body}
    }
    
    {methods}
}'''
            }
        }
    
    def _load_analysis_patterns(self) -> Dict[str, List[str]]:
        """Load code analysis patterns"""
        return {
            "anti_patterns": [
                "global variables",
                "magic numbers",
                "deep nesting",
                "long functions",
                "duplicate code",
                "hardcoded values"
            ],
            "best_practices": [
                "error handling",
                "input validation",
                "documentation",
                "type hints",
                "modular design",
                "separation of concerns"
            ],
            "security_issues": [
                "sql injection",
                "xss vulnerabilities",
                "hardcoded secrets",
                "weak encryption",
                "insecure dependencies"
            ]
        }
    
    def register_handlers(self):
        """Register message handlers"""
        self.message_handlers[MessageType.TASK_REQUEST] = self.handle_task_request
        self.message_handlers[MessageType.QUERY] = self.handle_query
        self.message_handlers[MessageType.EVENT] = self.handle_event
    
    async def start(self):
        """Start the coder agent"""
        await super().start()
        
        # Announce capabilities
        await self.announce_capabilities()
    
    async def announce_capabilities(self):
        """Announce agent capabilities"""
        capabilities_message = AgentMessage(
            sender_id=self.agent_id,
            message_type=MessageType.EVENT,
            content={
                "event_type": "agent_capabilities",
                "agent_id": self.agent_id,
                "capabilities": self.capabilities
            }
        )
        
        await self.publish_message(
            capabilities_message,
            routing_key="planner.*"
        )
    
    async def handle_task_request(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle incoming code task"""
        task_data = message.content
        
        # Create code task
        task = CodeTask(
            task_type=CodeTaskType(task_data.get("task_type", "generation")),
            language=CodeLanguage(task_data.get("language", "python")),
            description=task_data.get("description", ""),
            requirements=task_data.get("requirements", []),
            input_code=task_data.get("input_code"),
            constraints=task_data.get("constraints", {}),
            priority=task_data.get("priority", 5)
        )
        
        self.tasks[task.task_id] = task
        
        # Execute task
        result = await self.execute_code_task(task)
        
        return {
            "task_id": task.task_id,
            "result_id": result.result_id,
            "status": "completed",
            "confidence": result.confidence
        }
    
    async def handle_query(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle query messages"""
        query_type = message.content.get("query_type")
        
        if query_type == "task_status":
            task_id = message.content.get("task_id")
            if task_id in self.tasks:
                return self.tasks[task_id].to_dict()
            else:
                return {"error": "Task not found"}
        
        elif query_type == "result_status":
            result_id = message.content.get("result_id")
            if result_id in self.results:
                return self.results[result_id].to_dict()
            else:
                return {"error": "Result not found"}
        
        elif query_type == "capabilities":
            return {"capabilities": self.capabilities}
        
        else:
            return {"error": "Unknown query type"}
    
    async def handle_event(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle event messages"""
        return {"status": "acknowledged"}
    
    async def execute_code_task(self, task: CodeTask) -> CodeResult:
        """Execute a code task"""
        with self.tracer.start_as_current_span("execute_code_task") as span:
            span.set_attribute("task_id", task.task_id)
            span.set_attribute("task_type", task.task_type.value)
            span.set_attribute("language", task.language.value)
            
            result = CodeResult(task_id=task.task_id)
            
            try:
                if task.task_type == CodeTaskType.GENERATION:
                    result = await self.generate_code(task)
                elif task.task_type == CodeTaskType.ANALYSIS:
                    result = await self.analyze_code(task)
                elif task.task_type == CodeTaskType.REFACTORING:
                    result = await self.refactor_code(task)
                elif task.task_type == CodeTaskType.DEBUGGING:
                    result = await self.debug_code(task)
                elif task.task_type == CodeTaskType.REVIEW:
                    result = await self.review_code(task)
                elif task.task_type == CodeTaskType.DOCUMENTATION:
                    result = await self.generate_documentation(task)
                elif task.task_type == CodeTaskType.TESTING:
                    result = await self.generate_tests(task)
                
                self.results[result.result_id] = result
                
            except Exception as e:
                self.logger.error(f"Code task error: {e}")
                result.issues.append({
                    "type": "error",
                    "message": str(e),
                    "severity": "critical"
                })
            
            return result
    
    async def generate_code(self, task: CodeTask) -> CodeResult:
        """Generate code based on requirements"""
        result = CodeResult(task_id=task.task_id)
        
        # Analyze requirements
        code_structure = await self.analyze_requirements(task)
        
        # Generate code using templates
        if task.language == CodeLanguage.PYTHON:
            generated_code = await self.generate_python_code(task, code_structure)
        elif task.language == CodeLanguage.JAVASCRIPT:
            generated_code = await self.generate_javascript_code(task, code_structure)
        else:
            generated_code = await self.generate_generic_code(task, code_structure)
        
        result.generated_code = generated_code
        result.confidence = await self.calculate_generation_confidence(task, generated_code)
        
        # Add suggestions
        result.suggestions = await self.generate_code_suggestions(task, generated_code)
        
        return result
    
    async def analyze_requirements(self, task: CodeTask) -> Dict[str, Any]:
        """Analyze requirements to determine code structure"""
        structure = {
            "functions": [],
            "classes": [],
            "imports": [],
            "patterns": []
        }
        
        # Extract function requirements
        for req in task.requirements:
            if "function" in req.lower() or "method" in req.lower():
                structure["functions"].append(req)
            elif "class" in req.lower():
                structure["classes"].append(req)
            elif "import" in req.lower():
                structure["imports"].append(req)
        
        # Determine patterns
        if "async" in task.description.lower():
            structure["patterns"].append("async")
        if "error" in task.description.lower() or "exception" in task.description.lower():
            structure["patterns"].append("error_handling")
        
        return structure
    
    async def generate_python_code(self, task: CodeTask, structure: Dict[str, Any]) -> str:
        """Generate Python code"""
        code_parts = []
        
        # Add imports
        if structure["imports"]:
            for imp in structure["imports"]:
                code_parts.append(f"import {imp}")
            code_parts.append("")
        
        # Generate functions
        for func_req in structure["functions"]:
            if "async" in structure["patterns"]:
                template = self.code_templates["python"]["async_function"]
            else:
                template = self.code_templates["python"]["function"]
            
            func_name = self._extract_function_name(func_req)
            parameters = self._extract_parameters(func_req)
            description = func_req
            
            code_parts.append(template.format(
                function_name=func_name,
                parameters=parameters,
                description=description,
                body="    # Implementation based on requirements",
                return_value="None"
            ))
            code_parts.append("")
        
        # Generate classes
        for class_req in structure["classes"]:
            template = self.code_templates["python"]["class"]
            class_name = self._extract_class_name(class_req)
            
            code_parts.append(template.format(
                class_name=class_name,
                description=class_req,
                init_parameters="",
                init_body="        pass",
                methods=""
            ))
            code_parts.append("")
        
        return "\n".join(code_parts)
    
    async def generate_javascript_code(self, task: CodeTask, structure: Dict[str, Any]) -> str:
        """Generate JavaScript code"""
        code_parts = []
        
        # Generate functions
        for func_req in structure["functions"]:
            template = self.code_templates["javascript"]["function"]
            func_name = self._extract_function_name(func_req)
            parameters = self._extract_parameters(func_req)
            
            code_parts.append(template.format(
                function_name=func_name,
                parameters=parameters,
                description=func_req,
                body="    // Implementation based on requirements",
                return_value="null"
            ))
            code_parts.append("")
        
        return "\n".join(code_parts)
    
    async def generate_generic_code(self, task: CodeTask, structure: Dict[str, Any]) -> str:
        """Generate generic code for other languages"""
        return f"# Code generation for {task.language.value}\n# Description: {task.description}\n# Requirements: {', '.join(task.requirements)}"
    
    def _extract_function_name(self, requirement: str) -> str:
        """Extract function name from requirement"""
        # Simple extraction - in production, use NLP
        words = requirement.lower().split()
        for word in words:
            if word in ["create", "get", "set", "update", "delete", "process", "calculate"]:
            idx = words.index(word)
            if idx + 1 < len(words):
                return f"{word}_{words[idx + 1]}"
        return "function_name"
    
    def _extract_class_name(self, requirement: str) -> str:
        """Extract class name from requirement"""
        words = requirement.lower().split()
        for word in words:
            if word == "class" and len(words) > words.index(word) + 1:
                return words[words.index(word) + 1].capitalize()
        return "ClassName"
    
    def _extract_parameters(self, requirement: str) -> str:
        """Extract parameters from requirement"""
        # Simple parameter extraction
        if "data" in requirement.lower():
            return "data"
        elif "id" in requirement.lower():
            return "id"
        else:
            return "*args, **kwargs"
    
    async def calculate_generation_confidence(self, task: CodeTask, code: str) -> float:
        """Calculate confidence in generated code"""
        confidence = 0.5  # Base confidence
        
        # Increase confidence if requirements are clear
        if len(task.requirements) > 0:
            confidence += 0.2
        
        # Increase confidence if code was generated
        if code and len(code) > 50:
            confidence += 0.2
        
        # Check for basic syntax
        try:
            if task.language == CodeLanguage.PYTHON:
                ast.parse(code)
                confidence += 0.1
        except:
            confidence -= 0.2
        
        return min(confidence, 1.0)
    
    async def generate_code_suggestions(self, task: CodeTask, code: str) -> List[str]:
        """Generate suggestions for improving the code"""
        suggestions = []
        
        if "error" not in code.lower() and "try" not in code.lower():
            suggestions.append("Consider adding error handling")
        
        if "def " in code and '"""' not in code:
            suggestions.append("Add docstrings to functions")
        
        if len(code) > 500 and "class " not in code:
            suggestions.append("Consider using classes for better organization")
        
        return suggestions
    
    async def analyze_code(self, task: CodeTask) -> CodeResult:
        """Analyze existing code"""
        result = CodeResult(task_id=task.task_id)
        
        if not task.input_code:
            result.issues.append({
                "type": "error",
                "message": "No input code provided for analysis",
                "severity": "critical"
            })
            return result
        
        # Perform code analysis
        analysis = {}
        
        # Check for anti-patterns
        anti_patterns_found = []
        for pattern in self.analysis_patterns["anti_patterns"]:
            if pattern.replace(" ", "_") in task.input_code.lower():
                anti_patterns_found.append(pattern)
        
        analysis["anti_patterns"] = anti_patterns_found
        
        # Check for best practices
        best_practices_found = []
        for practice in self.analysis_patterns["best_practices"]:
            if practice.replace(" ", "_") in task.input_code.lower():
                best_practices_found.append(practice)
        
        analysis["best_practices"] = best_practices_found
        
        # Check for security issues
        security_issues = []
        for issue in self.analysis_patterns["security_issues"]:
            if issue.replace(" ", "_") in task.input_code.lower():
                security_issues.append(issue)
        
        analysis["security_issues"] = security_issues
        
        # Calculate complexity (simplified)
        complexity = len(task.input_code.split('\n'))
        analysis["complexity"] = complexity
        
        result.analysis = analysis
        result.confidence = 0.8 if not security_issues else 0.5
        
        return result
    
    async def refactor_code(self, task: CodeTask) -> CodeResult:
        """Refactor existing code"""
        result = CodeResult(task_id=task.task_id)
        
        if not task.input_code:
            result.issues.append({
                "type": "error",
                "message": "No input code provided for refactoring",
                "severity": "critical"
            })
            return result
        
        # Simple refactoring operations
        refactored_code = task.input_code
        
        # Remove excessive whitespace
        refactored_code = re.sub(r'\n\s*\n\s*\n', '\n\n', refactored_code)
        
        # Add basic structure
        if not refactored_code.strip().startswith('#'):
            refactored_code = f"# Refactored code\n{refactored_code}"
        
        result.generated_code = refactored_code
        result.suggestions = [
            "Consider breaking large functions into smaller ones",
            "Add type hints where applicable",
            "Improve variable naming for clarity"
        ]
        result.confidence = 0.7
        
        return result
    
    async def debug_code(self, task: CodeTask) -> CodeResult:
        """Debug code and find issues"""
        result = CodeResult(task_id=task.task_id)
        
        if not task.input_code:
            result.issues.append({
                "type": "error",
                "message": "No input code provided for debugging",
                "severity": "critical"
            })
            return result
        
        # Simple debugging analysis
        issues = []
        
        # Check for common issues
        if "print(" in task.input_code and "logging" not in task.input_code:
            issues.append({
                "type": "best_practice",
                "message": "Consider using logging instead of print statements",
                "severity": "info"
            })
        
        if "except:" in task.input_code and "except Exception" not in task.input_code:
            issues.append({
                "type": "error_handling",
                "message": "Broad except clause may hide errors",
                "severity": "warning"
            })
        
        result.issues = issues
        result.suggestions = [
            "Add unit tests to catch bugs early",
            "Use static analysis tools",
            "Add type checking"
        ]
        result.confidence = 0.6
        
        return result
    
    async def review_code(self, task: CodeTask) -> CodeResult:
        """Perform code review"""
        result = CodeResult(task_id=task.task_id)
        
        if not task.input_code:
            result.issues.append({
                "type": "error",
                "message": "No input code provided for review",
                "severity": "critical"
            })
            return result
        
        # Code review analysis
        analysis = {
            "readability": self._assess_readability(task.input_code),
            "maintainability": self._assess_maintainability(task.input_code),
            "performance": self._assess_performance(task.input_code),
            "security": self._assess_security(task.input_code)
        }
        
        result.analysis = analysis
        
        # Generate review comments
        comments = []
        if analysis["readability"] < 0.7:
            comments.append("Code readability could be improved")
        if analysis["maintainability"] < 0.7:
            comments.append("Consider refactoring for better maintainability")
        
        result.suggestions = comments
        result.confidence = 0.75
        
        return result
    
    def _assess_readability(self, code: str) -> float:
        """Assess code readability"""
        score = 0.8  # Base score
        
        # Check for long lines
        long_lines = [line for line in code.split('\n') if len(line) > 100]
        if long_lines:
            score -= 0.1 * (len(long_lines) / len(code.split('\n')))
        
        # Check for naming conventions
        if re.search(r'\b[a-z]\b', code):  # Single letter variables
            score -= 0.1
        
        return max(score, 0.0)
    
    def _assess_maintainability(self, code: str) -> float:
        """Assess code maintainability"""
        score = 0.7  # Base score
        
        # Check for function length
        lines = code.split('\n')
        if len(lines) > 100:
            score -= 0.2
        
        # Check for code duplication (simplified)
        unique_lines = len(set(lines))
        if unique_lines / len(lines) < 0.8:
            score -= 0.1
        
        return max(score, 0.0)
    
    def _assess_performance(self, code: str) -> float:
        """Assess code performance potential"""
        score = 0.8  # Base score
        
        # Check for potential performance issues
        if "O(n^2)" in code or "nested loop" in code.lower():
            score -= 0.2
        
        if "global " in code:
            score -= 0.1
        
        return max(score, 0.0)
    
    def _assess_security(self, code: str) -> float:
        """Assess code security"""
        score = 0.9  # Base score
        
        # Check for security issues
        if "eval(" in code or "exec(" in code:
            score -= 0.3
        
        if "password" in code.lower() and "==" in code:
            score -= 0.2
        
        return max(score, 0.0)
    
    async def generate_documentation(self, task: CodeTask) -> CodeResult:
        """Generate documentation for code"""
        result = CodeResult(task_id=task.task_id)
        
        if not task.input_code:
            result.issues.append({
                "type": "error",
                "message": "No input code provided for documentation",
                "severity": "critical"
            })
            return result
        
        # Generate documentation
        documentation = f"""
# Code Documentation

## Description
{task.description}

## Requirements
{chr(10).join(f'- {req}' for req in task.requirements)}

## Code Structure
"""
        
        # Extract functions and classes
        if "def " in task.input_code:
            documentation += "\n### Functions\n"
            for line in task.input_code.split('\n'):
                if line.strip().startswith('def '):
                    func_name = line.strip().replace('def ', '').split('(')[0]
                    documentation += f"- {func_name}\n"
        
        if "class " in task.input_code:
            documentation += "\n### Classes\n"
            for line in task.input_code.split('\n'):
                if line.strip().startswith('class '):
                    class_name = line.strip().replace('class ', '').split(':')[0]
                    documentation += f"- {class_name}\n"
        
        result.generated_code = documentation
        result.confidence = 0.7
        
        return result
    
    async def generate_tests(self, task: CodeTask) -> CodeResult:
        """Generate unit tests for code"""
        result = CodeResult(task_id=task.task_id)
        
        if not task.input_code:
            result.issues.append({
                "type": "error",
                "message": "No input code provided for test generation",
                "severity": "critical"
            })
            return result
        
        # Generate test template
        test_code = f"""
import unittest
from {task.language.value}_module import *  # Import your code here

class TestCode(unittest.TestCase):
    \"\"\"Unit tests for generated code\"\"\"
    
    def test_basic_functionality(self):
        \"\"\"Test basic functionality\"\"\"
        self.assertTrue(True)  # Replace with actual test
    
    def test_edge_cases(self):
        \"\"\"Test edge cases\"\"\"
        self.assertTrue(True)  # Replace with actual test
    
    def test_error_handling(self):
        \"\"\"Test error handling\"\"\"
        self.assertTrue(True)  # Replace with actual test

if __name__ == '__main__':
    unittest.main()
"""
        
        result.generated_code = test_code
        result.suggestions = [
            "Add specific test cases for your code",
            "Test edge cases and error conditions",
            "Add integration tests"
        ]
        result.confidence = 0.6
        
        return result
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a code task"""
        code_task = CodeTask(
            task_type=CodeTaskType(task.get("task_type", "generation")),
            language=CodeLanguage(task.get("language", "python")),
            description=task.get("description", ""),
            requirements=task.get("requirements", []),
            input_code=task.get("input_code")
        )
        
        result = await self.execute_code_task(code_task)
        
        return result.to_dict()


async def main():
    """Main entry point for the coder agent"""
    agent = CoderAgent()
    
    try:
        await agent.start()
        
        # Start consuming messages
        await agent.consume_messages()
        
    except KeyboardInterrupt:
        await agent.stop()
    except Exception as e:
        agent.logger.error(f"Agent error: {e}")
        await agent.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())