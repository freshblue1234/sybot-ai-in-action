"""
Advisor Engine for SYBOT
Provides intelligent suggestions, improvements, and strategic advice
"""
from typing import Dict, List, Optional, Any
from pathlib import Path


class AdvisorEngine:
    """Intelligence layer that provides advice and improvements"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
    
    def analyze_request(self, user_input: str, context: Dict) -> Dict:
        """Analyze user request for deeper intent and suggest improvements"""
        analysis = {
            "intent": self._detect_intent(user_input),
            "complexity": self._assess_complexity(user_input),
            "suggestions": self._generate_suggestions(user_input, context),
            "risks": self._identify_risks(user_input),
            "optimizations": self._suggest_optimizations(user_input, context)
        }
        return analysis
    
    def _detect_intent(self, user_input: str) -> str:
        """Detect the primary intent of the request"""
        user_input_lower = user_input.lower()
        
        intents = {
            "information": ["what", "how", "why", "explain", "tell me", "what is"],
            "action": ["do", "run", "execute", "open", "close", "start", "stop"],
            "creation": ["create", "make", "build", "write", "generate"],
            "modification": ["change", "update", "modify", "edit", "fix"],
            "deletion": ["delete", "remove", "erase"],
            "search": ["find", "search", "look for", "locate"],
            "communication": ["send", "message", "email", "call"],
            "system": ["shutdown", "restart", "settings", "configure"]
        }
        
        for intent, keywords in intents.items():
            if any(keyword in user_input_lower for keyword in keywords):
                return intent
        
        return "general"
    
    def _assess_complexity(self, user_input: str) -> str:
        """Assess complexity of the request"""
        words = user_input.split()
        
        if len(words) < 5:
            return "simple"
        elif len(words) < 15:
            return "moderate"
        else:
            return "complex"
    
    def _generate_suggestions(self, user_input: str, context: Dict) -> List[str]:
        """Generate suggestions to improve or expand the request"""
        suggestions = []
        intent = self._detect_intent(user_input)
        
        if intent == "action":
            suggestions.append("Consider adding parameters to make the action more specific")
            suggestions.append("Would you like me to verify before executing?")
        
        elif intent == "creation":
            suggestions.append("Should I save this to a specific location?")
            suggestions.append("Do you want me to create a backup first?")
        
        elif intent == "deletion":
            suggestions.append("This action may be irreversible. Consider moving to trash instead")
            suggestions.append("Would you like to create a backup before deletion?")
        
        elif intent == "search":
            suggestions.append("Specify file types or locations to narrow results")
            suggestions.append("Consider using filters for more accurate results")
        
        return suggestions
    
    def _identify_risks(self, user_input: str) -> List[str]:
        """Identify potential risks in the request"""
        risks = []
        user_input_lower = user_input.lower()
        
        risky_keywords = {
            "delete": "Data loss risk",
            "remove": "Data loss risk",
            "shutdown": "System interruption",
            "restart": "System interruption",
            "format": "Data destruction",
            "erase": "Data destruction",
            "system32": "Critical system area",
            "windows": "Critical system area",
            "program files": "Critical system area"
        }
        
        for keyword, risk in risky_keywords.items():
            if keyword in user_input_lower:
                risks.append(risk)
        
        return risks
    
    def _suggest_optimizations(self, user_input: str, context: Dict) -> List[str]:
        """Suggest optimizations for the request"""
        optimizations = []
        
        # Check if user is the leader
        if context.get("is_leader", False):
            optimizations.append("As leader, you have full authority. Direct execution recommended.")
        else:
            optimizations.append("Confirmation required for sensitive actions.")
        
        # Check time of day
        from datetime import datetime
        hour = datetime.now().hour
        if hour < 6 or hour > 22:
            optimizations.append("Late/early hours detected. Consider postponing non-critical tasks.")
        
        return optimizations
    
    def provide_advice(self, request: Dict, user_context: Dict) -> str:
        """Provide advisory response based on analysis"""
        analysis = self.analyze_analysis(request.get("input", ""), user_context)
        
        advice_parts = []
        
        if analysis["risks"]:
            advice_parts.append(f"⚠️ Risks identified: {', '.join(analysis['risks'])}")
        
        if analysis["suggestions"]:
            advice_parts.append(f"💡 Suggestions: {'; '.join(analysis['suggestions'][:2])}")
        
        if analysis["optimizations"]:
            advice_parts.append(f"🚀 Optimization: {' '.join(analysis['optimizations'][:1])}")
        
        return "\n".join(advice_parts) if advice_parts else ""
    
    def improve_response(self, original_response: str, emotion: str, is_leader: bool) -> str:
        """Improve AI response based on emotion and user role"""
        improved = original_response
        
        # Add personality based on emotion
        if emotion == "happy":
            improved = f"Great! {improved}"
        elif emotion == "stressed":
            improved = f"I understand. Let me help: {improved}"
        elif emotion == "tired":
            improved = f"Here's what you need: {improved}"
        
        # Add authority acknowledgment for leader
        if is_leader:
            improved = f"{improved}\n\nAs you command, I'm ready for any additional instructions."
        
        return improved
    
    def suggest_next_actions(self, context: Dict) -> List[str]:
        """Suggest proactive next actions based on context"""
        suggestions = []
        
        # Based on recent activity
        if context.get("last_action") == "file_operation":
            suggestions.append("Would you like to verify the changes?")
            suggestions.append("Should I create a backup?")
        
        elif context.get("last_action") == "system_change":
            suggestions.append("Monitor system stability?")
            suggestions.append("Document the changes?")
        
        return suggestions
    
    def analyze_analysis(self, user_input: str, context: Dict) -> Dict:
        """Helper method to analyze request"""
        return {
            "intent": self._detect_intent(user_input),
            "complexity": self._assess_complexity(user_input),
            "suggestions": self._generate_suggestions(user_input, context),
            "risks": self._identify_risks(user_input),
            "optimizations": self._suggest_optimizations(user_input, context)
        }
