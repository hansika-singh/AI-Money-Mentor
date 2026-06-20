"""
Insurance Agent - Specialized in insurance planning
"""

from utils.agents.base_agent import BaseAgent
from typing import Dict, Any


class InsuranceAgent(BaseAgent):
    """Agent specialized in insurance planning"""
    
    def __init__(self):
        super().__init__(
            name="Insurance Agent",
            description="Expert in life, health, term, and general insurance"
        )
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute insurance-related task"""
        query = task.get('query', '')
        context = task.get('context', {})
        
        prompt = f"""
        You are an Insurance Planning Expert Agent. Analyze this insurance query:
        "{query}"
        
        User Context:
        - Age: {context.get('age', 'Unknown')}
        - Dependents: {context.get('dependents', 'Unknown')}
        
        Provide:
        1. Insurance coverage recommendations
        2. Term vs health insurance advice
        3. Premium optimization
        4. Claim process guidance
        
        Consider Indian insurance market context.
        """
        
        system_prompt = """You are an expert insurance advisor.
        Provide comprehensive insurance planning recommendations.
        Always recommend comparing multiple policies."""
        
        response = self._call_ai(prompt, system_prompt)
        
        return {
            'agent': self.name,
            'query': query,
            'response': response,
            'confidence': 'high' if 'specific' in response.lower() else 'medium'
        }
    
    def get_capabilities(self) -> list:
        return [
            "Life insurance planning",
            "Health insurance selection",
            "Term insurance guidance",
            "Premium optimization",
            "Policy comparison"
        ]