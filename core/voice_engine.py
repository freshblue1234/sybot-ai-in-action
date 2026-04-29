"""
Voice Engine for SYBOT
Handles speech recognition and speaker identification
Automatic voice-based user authentication - no login required
"""
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Tuple, List
import speech_recognition as sr
import soundfile as sf
import json
from datetime import datetime
import hashlib

# Optional: torch for speaker recognition
try:
    import torch
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False


class VoiceEngine:
    """Manages speech recognition and automatic speaker identification"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.recognizer = sr.Recognizer()
        self.microphone = None
        
        # Voice enrollment storage
        self.voice_samples_dir = base_dir / "memory" / "voice_samples"
        self.voice_samples_dir.mkdir(parents=True, exist_ok=True)
        
        # Load enrolled voices
        self.enrolled_voices = self._load_enrolled_voices()
        
        # Speaker recognition model (optional - requires speechbrain)
        self.speaker_model = None
        self._init_speaker_model()
        
        # Audio buffer for enrollment
        self.audio_buffer: List[np.ndarray] = []
        self.buffer_sample_rate = 16000
    
    def _init_speaker_model(self):
        """Initialize speaker recognition model"""
        if not _TORCH_AVAILABLE:
            print("[VoiceEngine] Torch not available - using feature-based recognition")
            return
            
        try:
            from speechbrain.inference.speaker import SpeakerRecognition
            self.speaker_model = SpeakerRecognition.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir=str(self.base_dir / "models" / "speaker_recognition")
            )
            print("[VoiceEngine] Speaker recognition model loaded")
        except Exception as e:
            print(f"[VoiceEngine] Speaker recognition not available: {e}")
            print("[VoiceEngine] Will use feature-based recognition")
    
    def _load_enrolled_voices(self) -> Dict[str, Dict]:
        """Load enrolled voice profiles"""
        index_file = self.voice_samples_dir / "index.json"
        if not index_file.exists():
            return {}
        
        try:
            with open(index_file, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[VoiceEngine] Failed to load voice index: {e}")
            return {}
    
    def _save_enrolled_voices(self):
        """Save enrolled voice profiles"""
        index_file = self.voice_samples_dir / "index.json"
        try:
            with open(index_file, "w") as f:
                json.dump(self.enrolled_voices, f, indent=2)
        except Exception as e:
            print(f"[VoiceEngine] Failed to save voice index: {e}")
    
    def _extract_voice_features(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """Extract simple audio features for voice matching (no ML required)"""
        try:
            import librosa
            # Extract MFCC features
            mfcc = librosa.feature.mfcc(y=audio_data.astype(float), sr=sample_rate, n_mfcc=13)
            # Take mean across time
            features = np.mean(mfcc, axis=1)
            return features
        except ImportError:
            # Fallback: use basic statistics
            energy = np.mean(audio_data ** 2)
            zero_crossings = np.sum(np.diff(np.sign(audio_data)) != 0)
            spectral_centroid = np.mean(np.abs(np.fft.fft(audio_data)))
            return np.array([energy, zero_crossings, spectral_centroid])
    
    def _calculate_similarity(self, features1: np.ndarray, features2: np.ndarray) -> float:
        """Calculate similarity between two voice feature vectors"""
        # Cosine similarity
        norm1 = np.linalg.norm(features1)
        norm2 = np.linalg.norm(features2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return np.dot(features1, features2) / (norm1 * norm2)
    
    def enroll_user_voice(self, user_id: str, user_name: str, audio_data: np.ndarray, sample_rate: int) -> bool:
        """Enroll a user's voice for automatic identification"""
        try:
            # Extract features
            features = self._extract_voice_features(audio_data, sample_rate)
            
            # Save audio sample
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_file = self.voice_samples_dir / f"{user_id}_{timestamp}.wav"
            sf.write(str(audio_file), audio_data, sample_rate)
            
            # Update enrollment index
            if user_id not in self.enrolled_voices:
                self.enrolled_voices[user_id] = {
                    "name": user_name,
                    "samples": [],
                    "features": [],
                    "enrolled_at": datetime.now().isoformat()
                }
            
            self.enrolled_voices[user_id]["samples"].append(str(audio_file.name))
            self.enrolled_voices[user_id]["features"].append(features.tolist())
            
            # Update last seen
            self.enrolled_voices[user_id]["last_seen"] = datetime.now().isoformat()
            
            self._save_enrolled_voices()
            print(f"[VoiceEngine] Enrolled voice for {user_name} ({user_id})")
            return True
            
        except Exception as e:
            print(f"[VoiceEngine] Voice enrollment failed: {e}")
            return False
    
    def identify_speaker(self, audio_data: np.ndarray, sample_rate: int) -> Optional[str]:
        """Identify speaker from audio automatically"""
        if not self.enrolled_voices:
            return None
        
        try:
            # Extract features from current audio
            current_features = self._extract_voice_features(audio_data, sample_rate)
            
            # Compare with all enrolled voices
            best_match = None
            best_score = 0.0
            
            for user_id, voice_data in self.enrolled_voices.items():
                if not voice_data.get("features"):
                    continue
                
                # Calculate average similarity with all samples
                similarities = []
                for stored_features in voice_data["features"]:
                    stored = np.array(stored_features)
                    if len(stored) == len(current_features):
                        sim = self._calculate_similarity(current_features, stored)
                        similarities.append(sim)
                
                if similarities:
                    avg_similarity = np.mean(similarities)
                    if avg_similarity > best_score and avg_similarity > 0.7:  # Threshold
                        best_score = avg_similarity
                        best_match = user_id
            
            if best_match:
                user_name = self.enrolled_voices[best_match]["name"]
                print(f"[VoiceEngine] Identified: {user_name} (confidence: {best_score:.2f})")
                return best_match
            
            return None
            
        except Exception as e:
            print(f"[VoiceEngine] Speaker identification error: {e}")
            return None
    
    def get_user_name(self, user_id: str) -> Optional[str]:
        """Get user name from enrolled voices"""
        if user_id in self.enrolled_voices:
            return self.enrolled_voices[user_id]["name"]
        return None
    
    def listen_for_speech(self, timeout: int = 5, phrase_time_limit: int = 10) -> Optional[Dict]:
        """Listen for speech and return transcription"""
        if not self.microphone:
            try:
                self.microphone = sr.Microphone()
            except Exception as e:
                print(f"[VoiceEngine] Microphone error: {e}")
                return None
        
        with self.microphone as source:
            # Adjust for ambient noise
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                
                # Transcribe
                text = self.recognizer.recognize_google(audio)
                
                # Get audio data for speaker recognition
                audio_data = np.frombuffer(audio.get_raw_data(), dtype=np.int16)
                audio_float32 = audio_data.astype(np.float32) / 32768.0
                
                return {
                    "text": text,
                    "audio": audio_float32,
                    "sample_rate": audio.sample_rate
                }
                
            except sr.WaitTimeoutError:
                return None
            except sr.UnknownValueError:
                return {"text": "", "audio": None, "sample_rate": None}
            except Exception as e:
                print(f"[VoiceEngine] Recognition error: {e}")
                return None
    
    def collect_audio_sample(self, audio_data: np.ndarray, sample_rate: int):
        """Collect audio sample for potential enrollment"""
        self.audio_buffer.append(audio_data)
        self.buffer_sample_rate = sample_rate
        
        # Keep buffer manageable
        if len(self.audio_buffer) > 10:
            self.audio_buffer.pop(0)
    
    def get_combined_audio(self) -> Tuple[Optional[np.ndarray], int]:
        """Get combined audio from buffer for enrollment"""
        if not self.audio_buffer:
            return None, self.buffer_sample_rate
        
        # Combine all samples
        combined = np.concatenate(self.audio_buffer)
        return combined, self.buffer_sample_rate
    
    def clear_buffer(self):
        """Clear audio buffer"""
        self.audio_buffer = []
    
    def create_voice_embedding(self, audio_data: np.ndarray, sample_rate: int) -> Optional[np.ndarray]:
        """Create voice embedding for a user (fallback to features)"""
        if self.speaker_model:
            try:
                audio_tensor = torch.from_numpy(audio_data).unsqueeze(0)
                embedding = self.speaker_model.encode_batch(audio_tensor)
                return embedding.squeeze().detach().cpu().numpy()
            except Exception as e:
                print(f"[VoiceEngine] Embedding creation error: {e}")
        
        # Fallback to features
        return self._extract_voice_features(audio_data, sample_rate)
    
    def transcribe_audio_file(self, audio_path: Path) -> Optional[str]:
        """Transcribe audio from file"""
        try:
            with sr.AudioFile(str(audio_path)) as source:
                audio = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio)
                return text
        except Exception as e:
            print(f"[VoiceEngine] File transcription error: {e}")
            return None
