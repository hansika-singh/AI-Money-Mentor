"""
Tax Agent - Specialized in tax planning and optimization
"""

from utils.agents.base_agent import BaseAgent
from typing import Dict, Any


class TaxAgent(BaseAgent):
    """Agent specialized in tax planning"""
    
    def __init__(self):
        super().__init__(
            name="Tax Agent",
            description="Expert in Indian tax planning, regime comparison, and deductions"
        )
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tax-related task"""
        query = task.get('query', '')
        context = task.get('context', {})
        
        prompt = f"""
        You are a Tax Expert Agent. Analyze this tax query:
        "{query}"
        
        User Context:
        - Income: ₹{context.get('income', 'Unknown')}
        - Existing deductions: 80C: ₹{context.get('deduction_80c', 0)}, 80D: ₹{context.get('deduction_80d', 0)}
        
        Provide:
        1. Tax regime recommendation (Old vs New)
        2. Specific deduction opportunities
        3. Tax-saving investment suggestions
        4. Estimated tax savings
        
        Be specific and actionable.
        """
        
        system_prompt = """You are an expert Indian tax consultant. 
        Provide accurate, actionable tax advice based on Indian tax laws.
        Always recommend consulting a CA for final decisions."""
        
        response = self._call_ai(prompt, system_prompt)
        
        return {
            'agent': self.name,
            'query': query,
            'response': response,
            'confidence': 'high' if 'specific' in response.lower() else 'medium'
        }
    
    def get_capabilities(self) -> list:
        return [
            "Tax regime comparison",
            "Deduction optimization (80C, 80D, HRA)",
            "Tax-saving investment recommendations",
            "Income tax calculation",
            "Capital gains tax planning"
        ]