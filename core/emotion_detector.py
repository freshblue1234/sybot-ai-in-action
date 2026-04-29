"""
Emotion Detection from Speech for SYBOT
Detects emotional state from speech patterns and tone
"""
import numpy as np
from pathlib import Path
from typing import Optional, Dict

# Optional: torch for emotion detection
try:
    import torch
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False


class EmotionDetector:
    """Detects emotion from speech audio"""
    
    EMOTIONS = {
        "happy": {"response_tone": "energetic, enthusiastic, engaging"},
        "sad": {"response_tone": "empathetic, gentle, supportive"},
        "neutral": {"response_tone": "professional, balanced, clear"},
        "stressed": {"response_tone": "calm, reassuring, patient"},
        "angry": {"response_tone": "de-escalating, understanding, patient"},
        "excited": {"response_tone": "energetic, matching enthusiasm"},
        "tired": {"response_tone": "gentle, concise, helpful"},
        "confused": {"response_tone": "clarifying, patient, explanatory"}
    }
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.model = None
        self._init_model()
    
    def _init_model(self):
        """Initialize emotion detection model"""
        if not _TORCH_AVAILABLE:
            print("[EmotionDetector] Torch not available - using rule-based detection")
            return
            
        try:
            # Use a lightweight emotion detection model
            from transformers import pipeline
            self.model = pipeline(
                "audio-classification",
                model="superb/wav2vec2-base-superb-er",
                device=0 if torch.cuda.is_available() else -1
            )
            print("[EmotionDetector] Model loaded successfully")
        except Exception as e:
            print(f"[EmotionDetector] Model not available: {e}")
            print("[EmotionDetector] Will use rule-based detection")
    
    def detect_emotion(self, audio_data: np.ndarray, sample_rate: int) -> Dict:
        """Detect emotion from audio"""
        if self.model:
            try:
                # Use model-based detection
                result = self.model({"array": audio_data, "sampling_rate": sample_rate})
                
                # Get top emotion
                top_result = result[0]
                emotion = top_result["label"].lower()
                confidence = top_result["score"]
                
                # Map to our emotion categories
                emotion = self._map_emotion(emotion)
                
                return {
                    "emotion": emotion,
                    "confidence": confidence,
                    "response_tone": self.EMOTIONS.get(emotion, {}).get("response_tone", "neutral")
                }
            except Exception as e:
                print(f"[EmotionDetector] Detection error: {e}")
        
        # Fallback: rule-based detection from audio features
        return self._rule_based_detection(audio_data, sample_rate)
    
    def _map_emotion(self, model_emotion: str) -> str:
        """Map model emotion output to our categories"""
        emotion_map = {
            "happy": "happy",
            "sad": "sad",
            "angry": "angry",
            "neutral": "neutral",
            "fear": "stressed",
            "disgust": "stressed",
            "surprise": "excited"
        }
        return emotion_map.get(model_emotion, "neutral")
    
    def _rule_based_detection(self, audio_data: np.ndarray, sample_rate: int) -> Dict:
        """Fallback rule-based emotion detection"""
        # Extract simple audio features
        energy = np.mean(audio_data ** 2)
        zero_crossings = np.sum(np.diff(np.sign(audio_data)) != 0)
        
        # Very basic heuristics
        if energy > 0.01 and zero_crossings > 1000:
            return {"emotion": "excited", "confidence": 0.5, "response_tone": self.EMOTIONS["excited"]["response_tone"]}
        elif energy < 0.001:
            return {"emotion": "tired", "confidence": 0.5, "response_tone": self.EMOTIONS["tired"]["response_tone"]}
        else:
            return {"emotion": "neutral", "confidence": 0.5, "response_tone": self.EMOTIONS["neutral"]["response_tone"]}
    
    def get_response_tone(self, emotion: str) -> str:
        """Get appropriate response tone for detected emotion"""
        return self.EMOTIONS.get(emotion, {}).get("response_tone", "professional, balanced, clear")
