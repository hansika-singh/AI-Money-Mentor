"""
Debt Agent - Specialized in debt management
"""

from utils.agents.base_agent import BaseAgent
from typing import Dict, Any


class DebtAgent(BaseAgent):
    """Agent specialized in debt management"""
    
    def __init__(self):
        super().__init__(
            name="Debt Agent",
            description="Expert in loans, EMIs, credit cards, and debt reduction strategies"
        )
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute debt-related task"""
        query = task.get('query', '')
        context = task.get('context', {})
        
        prompt = f"""
        You are a Debt Management Expert Agent. Analyze this debt query:
        "{query}"
        
        User Context:
        - Total debt: ₹{context.get('debt', 'Unknown')}
        - Monthly income: ₹{context.get('income', 'Unknown')}
        
        Provide:
        1. Debt reduction strategy
        2. EMI management tips
        3. Debt consolidation advice if applicable
        4. Emergency fund recommendations
        
        Focus on practical, actionable steps.
        """
        
        system_prompt = """You are an expert debt management advisor.
        Provide practical, actionable debt reduction strategies.
        Always emphasize the importance of emergency funds."""
        
        response = self._call_ai(prompt, system_prompt)
        
        return {
            'agent': self.name,
            'query': query,
            'response': response,
            'confidence': 'high' if 'specific' in response.lower() else 'medium'
        }
    
    def get_capabilities(self) -> list:
        return [
            "Debt reduction strategies",
            "EMI optimization",
            "Credit card management",
            "Debt consolidation advice",
            "Emergency fund planning"
        ]