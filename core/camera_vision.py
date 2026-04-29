"""
Continuous Camera Vision System for SYBOT
Provides real-time camera feed analysis with conversational commentary
"""

import asyncio
import threading
import time
from pathlib import Path
from typing import Optional, Callable
import json

try:
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

try:
    import numpy as np
    _NP_AVAILABLE = True
except ImportError:
    _NP_AVAILABLE = False


class CameraVision:
    """Continuous camera vision with real-time analysis and commentary"""
    
    def __init__(self, base_dir: Path, on_commentary: Optional[Callable[[str], None]] = None):
        self.base_dir = base_dir
        self.on_commentary = on_commentary
        
        self.camera = None
        self.is_running = False
        self.analysis_thread = None
        self.last_commentary = ""
        self.commentary_cooldown = 2.0  # seconds between commentary (more frequent)
        self.last_commentary_time = 0
        
        # Vision state
        self.last_frame = None
        self.frame_count = 0
        
        # Activity tracking
        self.detected_activities = []
        self.activity_history = []
        
    def is_available(self) -> bool:
        """Check if camera vision is available"""
        return _CV2_AVAILABLE and _NP_AVAILABLE
    
    def start_camera(self, camera_index: int = 0) -> bool:
        """Start camera capture with multiple backend fallbacks"""
        if not self.is_available():
            print("[CameraVision] OpenCV or NumPy not available")
            return False
        
        try:
            # Try different backends for Windows - DirectShow first (most reliable)
            backends = [
                (cv2.CAP_DSHOW, "DirectShow"),
                (cv2.CAP_ANY, "Auto-detect"),
            ]
            
            for backend, backend_name in backends:
                try:
                    print(f"[CameraVision] Trying {backend_name} backend...")
                    self.camera = cv2.VideoCapture(camera_index, backend)
                    
                    if not self.camera.isOpened():
                        print(f"[CameraVision] {backend_name}: Camera not opened")
                        if self.camera:
                            self.camera.release()
                        self.camera = None
                        continue
                    
                    # Set camera properties for better performance
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    self.camera.set(cv2.CAP_PROP_FPS, 30)
                    self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer for real-time
                    
                    # Test if we can actually read a frame (try multiple times)
                    test_success = False
                    for attempt in range(3):
                        ret, test_frame = self.camera.read()
                        if ret and test_frame is not None:
                            test_success = True
                            break
                        time.sleep(0.1)
                    
                    if test_success:
                        self.is_running = True
                        self.analysis_thread = threading.Thread(
                            target=self._analysis_loop,
                            daemon=True
                        )
                        self.analysis_thread.start()
                        
                        print(f"[CameraVision] Camera {camera_index} started successfully with {backend_name}")
                        return True
                    else:
                        print(f"[CameraVision] {backend_name}: Could not read frames")
                        if self.camera:
                            self.camera.release()
                        self.camera = None
                        continue
                        
                except Exception as e:
                    print(f"[CameraVision] {backend_name} failed: {e}")
                    if self.camera:
                        self.camera.release()
                    self.camera = None
                    continue
            
            print(f"[CameraVision] Could not open camera {camera_index} with any backend")
            print("[CameraVision] Possible reasons: Camera in use, no camera connected, or driver issues")
            return False
            
        except Exception as e:
            print(f"[CameraVision] Error starting camera: {e}")
            return False
    
    def stop_camera(self):
        """Stop camera capture"""
        self.is_running = False
        if self.analysis_thread:
            self.analysis_thread.join(timeout=2)
        
        if self.camera:
            self.camera.release()
            self.camera = None
        
        print("[CameraVision] Camera stopped")
    
    def _analysis_loop(self):
        """Main analysis loop for camera feed"""
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        while self.is_running and self.camera:
            try:
                ret, frame = self.camera.read()
                if not ret:
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"[CameraVision] Too many consecutive errors ({consecutive_errors}), stopping camera")
                        self.is_running = False  # Just set flag, don't call stop_camera from thread
                        break
                    time.sleep(0.1)
                    continue
                
                # Reset error counter on successful frame
                consecutive_errors = 0
                self.last_frame = frame
                self.frame_count += 1
                
                # Analyze frame every 30 frames (approx 1 second at 30fps)
                if self.frame_count % 30 == 0:
                    self._analyze_frame(frame)
                
                time.sleep(0.033)  # ~30fps
                
            except Exception as e:
                consecutive_errors += 1
                print(f"[CameraVision] Analysis error: {e}")
                if consecutive_errors >= max_consecutive_errors:
                    print(f"[CameraVision] Too many consecutive errors, stopping camera")
                    self.is_running = False  # Just set flag, don't call stop_camera from thread
                    break
                time.sleep(0.1)
        
        # Thread is ending - release camera if needed
        if self.camera:
            try:
                self.camera.release()
                self.camera = None
                print("[CameraVision] Camera released by analysis thread")
            except Exception as e:
                print(f"[CameraVision] Error releasing camera: {e}")
    
    def _analyze_frame(self, frame):
        """Analyze a single frame and generate commentary"""
        try:
            current_time = time.time()
            
            # Check cooldown
            if current_time - self.last_commentary_time < self.commentary_cooldown:
                return
            
            # Simple visual analysis
            commentary = self._generate_commentary(frame)
            
            if commentary and commentary != self.last_commentary:
                self.last_commentary = commentary
                self.last_commentary_time = current_time
                
                # Send commentary through callback
                if self.on_commentary:
                    self.on_commentary(commentary)
                    print(f"[CameraVision] Commentary: {commentary}")
        
        except Exception as e:
            print(f"[CameraVision] Frame analysis error: {e}")
    
    def _generate_commentary(self, frame) -> Optional[str]:
        """Generate conversational commentary about what's seen"""
        try:
            # Basic visual features
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness = gray.mean()
            
            # Detect motion by comparing with previous frame
            motion_detected = self._detect_motion(gray)
            
            # Generate commentary based on visual features
            commentary = []
            
            # Lighting condition (varied responses)
            if brightness < 50:
                lighting_comments = [
                    "It's quite dark here",
                    "The lighting is dim",
                    "It's getting dark",
                    "Hard to see clearly"
                ]
                commentary.append(lighting_comments[self.frame_count % len(lighting_comments)])
            elif brightness > 200:
                lighting_comments = [
                    "It's very bright",
                    "Lots of light here",
                    "Quite bright",
                    "Good lighting"
                ]
                commentary.append(lighting_comments[self.frame_count % len(lighting_comments)])
            
            # Activity (varied responses)
            if motion_detected:
                activity_comments = [
                    "I see some movement",
                    "Something's happening",
                    "You're moving around",
                    "Activity detected",
                    "I can see you're active"
                ]
                commentary.append(activity_comments[self.frame_count % len(activity_comments)])
            else:
                still_comments = [
                    "Everything seems still",
                    "It's quiet and still",
                    "No movement right now",
                    "Everything's calm",
                    "Looks peaceful"
                ]
                commentary.append(still_comments[self.frame_count % len(still_comments)])
            
            # Combine commentary
            if commentary:
                return ". ".join(commentary) + "."
            
            return None
            
        except Exception as e:
            print(f"[CameraVision] Commentary generation error: {e}")
            return None
    
    def _detect_motion(self, current_gray) -> bool:
        """Detect motion between frames"""
        try:
            if not hasattr(self, 'prev_gray'):
                self.prev_gray = current_gray
                return False
            
            # Calculate frame difference
            diff = cv2.absdiff(self.prev_gray, current_gray)
            motion_score = diff.mean()
            
            self.prev_gray = current_gray
            
            # Motion threshold
            return motion_score > 10
            
        except Exception as e:
            return False
    
    def get_current_frame(self):
        """Get the current camera frame"""
        return self.last_frame
    
    def get_status(self) -> dict:
        """Get camera vision status"""
        return {
            "available": self.is_available(),
            "running": self.is_running,
            "frame_count": self.frame_count,
            "last_commentary": self.last_commentary,
            "camera_open": self.camera.is_open() if self.camera else False
        }
