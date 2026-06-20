"""
Portfolio Agent - Specialized in portfolio management
"""

from utils.agents.base_agent import BaseAgent
from typing import Dict, Any


class PortfolioAgent(BaseAgent):
    """Agent specialized in portfolio management"""
    
    def __init__(self):
        super().__init__(
            name="Portfolio Agent",
            description="Expert in asset allocation, rebalancing, and portfolio optimization"
        )
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute portfolio-related task"""
        query = task.get('query', '')
        context = task.get('context', {})
        
        prompt = f"""
        You are a Portfolio Management Expert Agent. Analyze this portfolio query:
        "{query}"
        
        User Context:
        - Total portfolio value: ₹{context.get('portfolio_value', 'Unknown')}
        - Risk profile: {context.get('risk_profile', 'Moderate')}
        
        Provide:
        1. Current asset allocation review
        2. Rebalancing recommendations
        3. Diversification suggestions
        4. Performance optimization strategies
        
        Consider modern portfolio theory principles.
        """
        
        system_prompt = """You are an expert portfolio manager.
        Provide sophisticated portfolio optimization recommendations.
        Always consider risk-return tradeoffs."""
        
        response = self._call_ai(prompt, system_prompt)
        
        return {
            'agent': self.name,
            'query': query,
            'response': response,
            'confidence': 'high' if 'specific' in response.lower() else 'medium'
        }
    
    def get_capabilities(self) -> list:
        return [
            "Asset allocation",
            "Portfolio rebalancing",
            "Diversification strategies",
            "Risk management",
            "Performance optimization"
        ]