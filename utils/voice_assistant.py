"""
Advanced Multi-Language Voice Financial Assistant
Support for Indian languages with natural language understanding
"""

import speech_recognition as sr
import pyttsx3
import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import tempfile
import os

from groq import Groq
from gtts import gTTS


class MultiLanguageVoiceAssistant:
    """
    Advanced Voice Assistant with Multi-Language Support
    """
    
    def __init__(self, client=None):
        self.client = client
        self.recognizer = sr.Recognizer()
        
        # Supported languages
        self.languages = {
            'en-IN': {
                'name': 'English',
                'code': 'en-IN',
                'tts_lang': 'en',
                'flag': '🇬🇧'
            },
            'hi-IN': {
                'name': 'Hindi',
                'code': 'hi-IN',
                'tts_lang': 'hi',
                'flag': '🇮🇳'
            },
            'ta-IN': {
                'name': 'Tamil',
                'code': 'ta-IN',
                'tts_lang': 'ta',
                'flag': '🇮🇳'
            },
            'te-IN': {
                'name': 'Telugu',
                'code': 'te-IN',
                'tts_lang': 'te',
                'flag': '🇮🇳'
            },
            'bn-IN': {
                'name': 'Bengali',
                'code': 'bn-IN',
                'tts_lang': 'bn',
                'flag': '🇮🇳'
            },
            'mr-IN': {
                'name': 'Marathi',
                'code': 'mr-IN',
                'tts_lang': 'mr',
                'flag': '🇮🇳'
            },
            'gu-IN': {
                'name': 'Gujarati',
                'code': 'gu-IN',
                'tts_lang': 'gu',
                'flag': '🇮🇳'
            },
            'kn-IN': {
                'name': 'Kannada',
                'code': 'kn-IN',
                'tts_lang': 'kn',
                'flag': '🇮🇳'
            },
            'ml-IN': {
                'name': 'Malayalam',
                'code': 'ml-IN',
                'tts_lang': 'ml',
                'flag': '🇮🇳'
            },
            'pa-IN': {
                'name': 'Punjabi',
                'code': 'pa-IN',
                'tts_lang': 'pa',
                'flag': '🇮🇳'
            }
        }
        
        # Intent patterns
        self.intent_patterns = {
            'TRANSFER': [
                r'transfer\s+(\d+)\s+to\s+(.+)',
                r'send\s+(\d+)\s+to\s+(.+)',
                r'pay\s+(\d+)\s+to\s+(.+)',
                r'transfer\s+₹?(\d+)\s+to\s+(.+)',
                r'स्थानांतरित\s+(\d+)\s+को\s+(.+)',  # Hindi
                r'ट्रांसफर\s+(\d+)\s+को\s+(.+)',   # Hindi
            ],
            'BALANCE_QUERY': [
                r'balance',
                r'how much (do i have|money)',
                r'what\'s my balance',
                r'check balance',
                r'my balance',
                r'बैलेंस',
                r'कितना पैसा',
            ],
            'SPENDING_QUERY': [
                r'how much (did i spend|spent)',
                r'spending (this|last) month',
                r'my (spending|expenses)',
                r'expenses',
                r'खर्च',
                r'कितना खर्च',
            ],
            'NET_WORTH_QUERY': [
                r'net worth',
                r'my net worth',
                r'what\'s my net worth',
                r'how much am i worth',
                r'नेट वर्थ',
                r'कुल संपत्ति',
            ],
            'EXPENSE_ADD': [
                r'add expense (\d+) for (.+)',
                r'spent (\d+) on (.+)',
                r'expense (\d+) (.+)',
                r'खर्च (\d+) (.+)',
                r'लगा (\d+) (.+)',
            ]
        }
        
        # TTS engine for offline synthesis
        self.tts_engine = None
        try:
            self.tts_engine = pyttsx3.init()
        except:
            self.tts_engine = None
    
    def transcribe_voice(self, audio_file_path: str) -> Dict:
        """
        Transcribe voice to text with automatic language detection
        
        Args:
            audio_file_path: Path to audio file
        
        Returns:
            Dict with transcribed text and detected language
        """
        try:
            with sr.AudioFile(audio_file_path) as source:
                audio_data = self.recognizer.record(source)
        except Exception as e:
            # Fallback for microphone input
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                audio_data = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
        
        # Try each language
        for lang_code, lang_info in self.languages.items():
            try:
                text = self.recognizer.recognize_google_cloud(
                    audio_data,
                    language_code=lang_code,
                    preferred_phrases=[
                        "transfer", "send", "pay", "balance", "spend", 
                        "expense", "net worth", "money", "income", "saving",
                        "transferred", "payment", "wallet", "account",
                        "स्थानांतरित", "बैलेंस", "खर्च", "ट्रांसफर",  # Hindi
                        "பரிமாற்றம்", "இருப்பு", "செலவு",  # Tamil
                        "బదిలీ", "బ్యాలెన్స్", "ఖర్చు"  # Telugu
                    ],
                    show_all=True
                )
                
                if text and isinstance(text, str):
                    return {
                        'success': True,
                        'text': text,
                        'language': lang_code,
                        'language_name': lang_info['name'],
                        'confidence': 0.9
                    }
            except:
                continue
        
        # Fallback to Google Speech Recognition (free, limited languages)
        try:
            text = self.recognizer.recognize_google(audio_data)
            return {
                'success': True,
                'text': text,
                'language': 'en-IN',
                'language_name': 'English',
                'confidence': 0.7
            }
        except:
            pass
        
        return {
            'success': False,
            'error': 'Could not transcribe audio. Please try again.'
        }
    
    def parse_command(self, text: str, language: str = 'en-IN') -> Dict:
        """
        Parse natural language command to extract intent and parameters
        
        Args:
            text: Transcribed text
            language: Detected language code
        
        Returns:
            Dict with intent, parameters, and confidence
        """
        text_lower = text.lower().strip()
        
        # Try pattern matching first
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    if intent == 'TRANSFER':
                        return {
                            'intent': intent,
                            'amount': float(match.group(1)),
                            'recipient': match.group(2).strip(),
                            'confidence': 0.9,
                            'language': language
                        }
                    elif intent == 'EXPENSE_ADD':
                        return {
                            'intent': intent,
                            'amount': float(match.group(1)),
                            'category': match.group(2).strip(),
                            'confidence': 0.9,
                            'language': language
                        }
                    elif intent in ['BALANCE_QUERY', 'SPENDING_QUERY', 'NET_WORTH_QUERY']:
                        return {
                            'intent': intent,
                            'confidence': 0.8,
                            'language': language
                        }
        
        # If no pattern matches, use AI for intent parsing
        if self.client:
            return self._parse_with_ai(text, language)
        
        return {
            'intent': 'UNKNOWN',
            'confidence': 0.3,
            'language': language,
            'message': "I didn't understand that command. Try: 'Transfer 500 to savings' or 'Show my spending'"
        }
    
    def _parse_with_ai(self, text: str, language: str) -> Dict:
        """Parse command using AI (Groq/LLaMA)"""
        system_prompt = """You are a financial command parser. Parse the user's command and return JSON.

        Categories:
        - TRANSFER: Transfer money to someone/somewhere
        - BALANCE_QUERY: Check account balance
        - SPENDING_QUERY: Check spending/expenses
        - NET_WORTH_QUERY: Check net worth
        - EXPENSE_ADD: Add a new expense
        - UNKNOWN: Could not determine

        Return JSON format:
        {
            "intent": "INTENT_NAME",
            "amount": number or null,
            "recipient": string or null,
            "category": string or null,
            "confidence": 0.0-1.0
        }"""
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Parse this command: {text}"}
                ],
                temperature=0.1,
                max_tokens=150
            )
            
            result_text = response.choices[0].message.content.strip()
            # Extract JSON from response
            start = result_text.find('{')
            end = result_text.rfind('}') + 1
            if start != -1 and end > start:
                result = json.loads(result_text[start:end])
                result['language'] = language
                return result
        except:
            pass
        
        return {
            'intent': 'UNKNOWN',
            'confidence': 0.3,
            'language': language
        }
    
    def execute_command(self, parsed_command: Dict) -> Dict:
        """
        Execute the parsed command
        
        Args:
            parsed_command: Parsed command from parse_command()
        
        Returns:
            Dict with execution result and response
        """
        intent = parsed_command.get('intent', 'UNKNOWN')
        language = parsed_command.get('language', 'en-IN')
        lang_info = self.languages.get(language, self.languages['en-IN'])
        
        if intent == 'TRANSFER':
            amount = parsed_command.get('amount', 0)
            recipient = parsed_command.get('recipient', '')
            return self._execute_transfer(amount, recipient, lang_info)
        
        elif intent == 'BALANCE_QUERY':
            return self._execute_balance_query(lang_info)
        
        elif intent == 'SPENDING_QUERY':
            return self._execute_spending_query(lang_info)
        
        elif intent == 'NET_WORTH_QUERY':
            return self._execute_net_worth_query(lang_info)
        
        elif intent == 'EXPENSE_ADD':
            amount = parsed_command.get('amount', 0)
            category = parsed_command.get('category', 'Other')
            return self._execute_expense_add(amount, category, lang_info)
        
        else:
            return {
                'success': False,
                'response': self._get_translation('unknown_command', lang_info['name']),
                'language': language
            }
    
    def _execute_transfer(self, amount: float, recipient: str, lang_info: Dict) -> Dict:
        """Execute transfer command"""
        # For demo, return mock response
        # In production, this would call the ledger system
        response_text = f"✅ {amount} transferred to {recipient} successfully!"
        return {
            'success': True,
            'response': self._get_translation('transfer_success', lang_info['name'], amount=amount, recipient=recipient),
            'data': {
                'amount': amount,
                'recipient': recipient,
                'transaction_id': f"TX-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
        }
    
    def _execute_balance_query(self, lang_info: Dict) -> Dict:
        """Execute balance query"""
        # Mock balance - in production fetch from database
        balance = 150000
        return {
            'success': True,
            'response': self._get_translation('balance_response', lang_info['name'], balance=balance),
            'data': {'balance': balance}
        }
    
    def _execute_spending_query(self, lang_info: Dict) -> Dict:
        """Execute spending query"""
        # Mock spending - in production fetch from database
        spending = 45000
        return {
            'success': True,
            'response': self._get_translation('spending_response', lang_info['name'], spending=spending),
            'data': {'spending': spending}
        }
    
    def _execute_net_worth_query(self, lang_info: Dict) -> Dict:
        """Execute net worth query"""
        # Mock net worth - in production fetch from database
        net_worth = 500000
        return {
            'success': True,
            'response': self._get_translation('net_worth_response', lang_info['name'], net_worth=net_worth),
            'data': {'net_worth': net_worth}
        }
    
    def _execute_expense_add(self, amount: float, category: str, lang_info: Dict) -> Dict:
        """Execute expense add command"""
        return {
            'success': True,
            'response': self._get_translation('expense_added', lang_info['name'], amount=amount, category=category),
            'data': {'amount': amount, 'category': category}
        }
    
    def _get_translation(self, key: str, language: str, **kwargs) -> str:
        """Get translated response based on language"""
        # Simplified translation map - expand as needed
        translations = {
            'en-IN': {
                'unknown_command': "I didn't understand that command. Try: 'Transfer 500 to savings' or 'Show my spending'",
                'transfer_success': f"✅ ₹{kwargs.get('amount', 0)} transferred to {kwargs.get('recipient', '')} successfully!",
                'balance_response': f"💰 Your current balance is ₹{kwargs.get('balance', 0):,}",
                'spending_response': f"💳 Your spending this month is ₹{kwargs.get('spending', 0):,}",
                'net_worth_response': f"💎 Your net worth is ₹{kwargs.get('net_worth', 0):,}",
                'expense_added': f"✅ Expense of ₹{kwargs.get('amount', 0)} added to {kwargs.get('category', 'Other')}",
            },
            'hi-IN': {
                'unknown_command': "मुझे यह कमांड समझ नहीं आया। कोशिश करें: '500 बचत को ट्रांसफर करें' या 'मेरा खर्च दिखाएं'",
                'transfer_success': f"✅ ₹{kwargs.get('amount', 0)} {kwargs.get('recipient', '')} को सफलतापूर्वक ट्रांसफर किया गया!",
                'balance_response': f"💰 आपका वर्तमान बैलेंस ₹{kwargs.get('balance', 0):,} है",
                'spending_response': f"💳 इस महीने आपका खर्च ₹{kwargs.get('spending', 0):,} है",
                'net_worth_response': f"💎 आपकी कुल संपत्ति ₹{kwargs.get('net_worth', 0):,} है",
                'expense_added': f"✅ ₹{kwargs.get('amount', 0)} का खर्च {kwargs.get('category', 'Other')} में जोड़ा गया",
            },
            'ta-IN': {
                'unknown_command': "இந்த கட்டளையை என்னால் புரிந்து கொள்ள முடியவில்லை. முயற்சிக்கவும்: '500 சேமிப்பிற்கு மாற்றவும்' அல்லது 'எனது செலவினங்களைக் காட்டு'",
                'transfer_success': f"✅ ₹{kwargs.get('amount', 0)} {kwargs.get('recipient', '')} க்கு வெற்றிகரமாக மாற்றப்பட்டது!",
                'balance_response': f"💰 உங்கள் தற்போதைய இருப்பு ₹{kwargs.get('balance', 0):,}",
                'spending_response': f"💳 இந்த மாதம் உங்கள் செலவு ₹{kwargs.get('spending', 0):,}",
                'net_worth_response': f"💎 உங்கள் நிகர மதிப்பு ₹{kwargs.get('net_worth', 0):,}",
                'expense_added': f"✅ ₹{kwargs.get('amount', 0)} செலவு {kwargs.get('category', 'Other')} இல் சேர்க்கப்பட்டது",
            },
            'te-IN': {
                'unknown_command': "నాకు ఈ కమాండ్ అర్థం కాలేదు. ప్రయత్నించండి: '500 సేవింగ్స్‌కు బదిలీ చేయండి' లేదా 'నా ఖర్చు చూపించు'",
                'transfer_success': f"✅ ₹{kwargs.get('amount', 0)} {kwargs.get('recipient', '')} కు విజయవంతంగా బదిలీ చేయబడింది!",
                'balance_response': f"💰 మీ ప్రస్తుత బ్యాలెన్స్ ₹{kwargs.get('balance', 0):,}",
                'spending_response': f"💳 ఈ నెల మీ ఖర్చు ₹{kwargs.get('spending', 0):,}",
                'net_worth_response': f"💎 మీ నికర విలువ ₹{kwargs.get('net_worth', 0):,}",
                'expense_added': f"✅ ₹{kwargs.get('amount', 0)} ఖర్చు {kwargs.get('category', 'Other')} కు జోడించబడింది",
            }
        }
        
        lang_translations = translations.get(language, translations['en-IN'])
        return lang_translations.get(key, translations['en-IN'].get(key, "Sorry, I couldn't understand that."))
    
    def synthesize_voice(self, text: str, language: str = 'en-IN') -> Optional[str]:
        """
        Convert text to speech using TTS
        
        Args:
            text: Text to speak
            language: Target language code
        
        Returns:
            Path to generated audio file or None
        """
        try:
            lang_code = self.languages.get(language, {}).get('tts_lang', 'en')
            
            # Try gTTS first (online)
            try:
                tts = gTTS(text=text, lang=lang_code, slow=False)
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                tts.save(temp_file.name)
                return temp_file.name
            except:
                pass
            
            # Fallback to pyttsx3 (offline)
            if self.tts_engine:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
                return None
            
        except Exception as e:
            print(f"TTS error: {e}")
        
        return None