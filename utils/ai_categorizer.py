import re
from typing import Dict, List

CATEGORY_KEYWORDS = {
    'Food Dining': ['restaurant','cafe','pizza','burger','lunch','dinner','food','coffee','mcdonald','kfc'],
    'Transportation': ['uber','taxi','bus','train','gas','petrol','fuel','parking','ola'],
    'Shopping': ['amazon','walmart','target','mall','clothes','shoes','electronics','flipkart'],
    'Entertainment': ['netflix','spotify','cinema','movie','concert','game','steam','bookmyshow'],
    'Bills': ['electric','water','internet','wifi','phone bill','utility','jio','airtel'],
    'Groceries': ['grocery','supermarket','vegetables','fruits','dairy','bigbasket','zepto'],
    'Healthcare': ['doctor','hospital','pharmacy','medicine','clinic','dental','apollo'],
    'Education': ['coursera','udemy','college','university','book','course','tuition','byjus'],
    'Rent': ['rent','mortgage','housing','apartment','flat','maintenance'],
    'Travel': ['hotel','flight','airbnb','vacation','trip','makemytrip','goibibo'],
    'Subscription': ['subscription','monthly','recurring','membership','premium'],
}

class AICategorizer:
    def categorize(self, description):
        description_lower = description.lower()
        matches = []
        
        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in description_lower:
                    matches.append(category)
                    break
        
        if matches:
            category = matches[0]
            confidence = 0.8
        else:
            category = "Other"
            confidence = 0.3
        
        return {"category": category, "confidence": confidence}