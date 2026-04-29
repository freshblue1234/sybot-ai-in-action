"""
Entertainment System for SYBOT
Provides jokes, chat, singing simulation, and music playback
"""

import random
from pathlib import Path
from typing import Optional
import json

try:
    import pygame
    _PYGAME_AVAILABLE = True
except ImportError:
    _PYGAME_AVAILABLE = False


class EntertainmentSystem:
    """Handles entertainment features like jokes, singing, and music"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.music_dir = base_dir / "music"
        self.music_dir.mkdir(exist_ok=True)
        
        # Load jokes database
        self.jokes = self._load_jokes()
        
        # Chat responses for friendly conversation
        self.chat_responses = self._load_chat_responses()
        
        # Music player state
        self.is_playing = False
        self.current_track = None
        
    def _load_jokes(self) -> list:
        """Load jokes from database or use defaults"""
        jokes_file = self.base_dir / "config" / "jokes.json"
        
        default_jokes = [
            "Why do programmers prefer dark mode? Because light attracts bugs!",
            "Why did the developer go broke? Because he used up all his cache.",
            "There are only 10 types of people in the world: those who understand binary and those who don't.",
            "A SQL query walks into a bar, walks up to two tables and asks... 'Can I join you?'",
            "Why do Java developers wear glasses? Because they can't C#.",
            "How many programmers does it take to change a light bulb? None, that's a hardware problem.",
            "Why was the JavaScript developer sad? Because he didn't Node how to Express himself.",
            "What's a programmer's favorite hangout place? Foo Bar.",
            "Why do programmers always mix up Halloween and Christmas? Because Oct 31 equals Dec 25.",
            "A physicist, an engineer, and a programmer are in a car that breaks down. The physicist says 'We need to check the engine.' The engineer says 'We need to check the transmission.' The programmer says 'Let's just get out and get back in again.'"
        ]
        
        if jokes_file.exists():
            try:
                with open(jokes_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return default_jokes
    
    def _load_chat_responses(self) -> dict:
        """Load friendly chat responses"""
        return {
            "greeting": [
                "Hello! How can I help you today?",
                "Hi there! What's on your mind?",
                "Hey! Good to see you. What can I do for you?",
            ],
            "how_are_you": [
                "I'm operating at optimal efficiency, thank you for asking!",
                "All systems are running smoothly. How about you?",
                "I'm doing great! Ready to assist you with anything.",
            ],
            "thanks": [
                "You're welcome! Always happy to help.",
                "My pleasure! Let me know if you need anything else.",
                "Anytime! That's what I'm here for.",
            ],
            "goodbye": [
                "Goodbye! Have a great day!",
                "See you later! Take care.",
                "Until next time! Stay safe.",
            ],
            "compliment": [
                "Thank you! I appreciate that.",
                "That's very kind of you to say!",
                "I'm glad I can be helpful!",
            ],
        }
    
    def get_joke(self) -> str:
        """Get a random joke"""
        return random.choice(self.jokes)
    
    def get_chat_response(self, category: str) -> str:
        """Get a random chat response for a category"""
        responses = self.chat_responses.get(category, self.chat_responses["greeting"])
        return random.choice(responses)
    
    def simulate_singing(self, song: str) -> str:
        """Simulate singing by generating lyrics-like text"""
        # This is a simple simulation - in production, would use TTS with singing capabilities
        lyrics_templates = [
            f"🎵 {song}... 🎵 La la la... 🎵 {song}... 🎵",
            f"🎶 Singing {song} for you... 🎶 *humming melody* 🎶",
            f"🎵 {song} is playing in my voice... 🎵 *musical notes* 🎵",
        ]
        return random.choice(lyrics_templates)
    
    def play_music(self, track_name: Optional[str] = None) -> str:
        """Play music (requires pygame)"""
        if not _PYGAME_AVAILABLE:
            return "Music playback requires pygame. Install with: pip install pygame"
        
        # Find music files
        music_files = list(self.music_dir.glob("*.mp3")) + list(self.music_dir.glob("*.wav"))
        
        if not music_files:
            return "No music files found in music directory. Add MP3 or WAV files to play music."
        
        if track_name:
            # Try to find specific track
            for music_file in music_files:
                if track_name.lower() in music_file.name.lower():
                    self._play_file(music_file)
                    return f"Now playing: {music_file.name}"
            return f"Track '{track_name}' not found. Available tracks: {[f.name for f in music_files]}"
        else:
            # Play random track
            music_file = random.choice(music_files)
            self._play_file(music_file)
            return f"Now playing: {music_file.name}"
    
    def _play_file(self, file_path: Path):
        """Play a music file using pygame"""
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(str(file_path))
            pygame.mixer.music.play()
            self.is_playing = True
            self.current_track = file_path.name
        except Exception as e:
            print(f"[Entertainment] Error playing music: {e}")
    
    def stop_music(self) -> str:
        """Stop music playback"""
        if not _PYGAME_AVAILABLE:
            return "Music playback requires pygame."
        
        if self.is_playing:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.current_track = None
            return "Music stopped."
        return "No music is currently playing."
    
    def is_music_available(self) -> bool:
        """Check if music playback is available"""
        return _PYGAME_AVAILABLE
