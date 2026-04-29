# SYBOT Advanced Integration Guide

## Overview
This guide explains how to integrate the new advanced modules into main.py to enable multi-user support, voice recognition, emotion detection, and advisory capabilities.

## New Modules Created
1. `core/user_manager.py` - Multi-user profile management with leader prioritization
2. `core/memory_manager.py` - Persistent additive memory system
3. `core/voice_engine.py` - Speech recognition and speaker identification
4. `core/emotion_detector.py` - Emotion detection from speech
5. `core/advisor_engine.py` - Intelligence and advisory layer

## Integration Steps

### Step 1: Add Imports to main.py

Add these imports at the top of main.py after the existing imports:

```python
# Advanced Multi-User System
from core.user_manager import UserManager
from core.memory_manager import MemoryManager
from core.voice_engine import VoiceEngine
from core.emotion_detector import EmotionDetector
from core.advisor_engine import AdvisorEngine
```

### Step 2: Initialize New Systems in SybotLive.__init__

Modify the `__init__` method of the SybotLive class:

```python
def __init__(self, ui: SybotUI):
    self.ui = ui
    self.session = None
    self.audio_in_queue = None
    self.out_queue = None
    self._loop = None
    self._is_speaking = False
    self._speaking_lock = threading.Lock()
    self.ui.on_text_command = self._on_text_command
    self._turn_done_event: asyncio.Event | None = None
    
    # NEW: Initialize advanced systems
    self.user_manager = UserManager(BASE_DIR)
    self.memory_manager = MemoryManager(BASE_DIR)
    self.voice_engine = VoiceEngine(BASE_DIR)
    self.emotion_detector = EmotionDetector(BASE_DIR)
    self.advisor_engine = AdvisorEngine(BASE_DIR)
    
    # Set current user (default to leader for now)
    self.user_manager.set_current_user(
        user_id=UserManager.LEADER_ID,
        name=UserManager.LEADER_NAME
    )
```

### Step 3: Update _build_config to Include User Context

Modify the `_build_config` method to include user context and emotion:

```python
def _build_config(self) -> types.LiveConnectConfig:
    from datetime import datetime
    
    # Get current user info
    current_user = self.user_manager.get_current_user()
    is_leader = self.user_manager.is_leader() if current_user else False
    
    # Get user memory summary
    user_memory = ""
    if current_user:
        user_memory = self.memory_manager.get_user_summary(current_user.user_id)
    
    memory = load_memory()
    mem_str = format_memory_for_prompt(memory)
    sys_prompt = _load_system_prompt()
    
    now = datetime.now()
    time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
    time_ctx = (
        f"[CURRENT DATE & TIME]\n"
        f"Right now it is: {time_str}\n"
        f"Use this to calculate exact times for reminders.\n\n"
    )
    
    # NEW: User context
    user_ctx = ""
    if current_user:
        user_ctx = (
            f"[CURRENT USER]\n"
            f"Name: {current_user.name}\n"
            f"Is Leader: {is_leader}\n"
            f"Interactions: {current_user.interaction_count}\n\n"
        )
        if user_memory:
            user_ctx += f"[USER MEMORY]\n{user_memory}\n\n"
    
    parts = [time_ctx, user_ctx]
    if mem_str:
        parts.append(mem_str)
    parts.append(sys_prompt)
    
    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        output_audio_transcription={},
        input_audio_transcription={},
        system_instruction="\n".join(parts),
        tools=[{"function_declarations": TOOL_DECLARATIONS}],
        session_resumption=types.SessionResumptionConfig(),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Charon"
                )
            )
        ),
    )
```

### Step 4: Add Permission Check in _execute_tool

Modify the `_execute_tool` method to check permissions:

```python
async def _execute_tool(self, fc) -> types.FunctionResponse:
    name = fc.name
    args = dict(fc.args or {})
    
    print(f"[SYBOT] 🔧 {name}  {args}")
    self.ui.set_state("THINKING")
    
    # NEW: Permission check for non-leader users
    current_user = self.user_manager.get_current_user()
    is_leader = self.user_manager.is_leader() if current_user else False
    
    sensitive_actions = ["shutdown", "restart", "delete", "format", "file_controller"]
    if not is_leader and any(s in name.lower() for s in sensitive_actions):
        # For non-leaders, require confirmation for sensitive actions
        confirmed = args.get("confirmed", "").lower() in ("yes", "true", "1")
        if not confirmed:
            result = f"Confirmation required for {name}. Please call again with confirmed=yes."
            print(f"[SYBOT] 🔒 Permission check: {result}")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": result}
            )
    
    # NEW: Get advisor suggestions
    advisor_suggestions = ""
    try:
        analysis = self.advisor_engine.analyze_request(
            user_input=str(args),
            context={"is_leader": is_leader, "user_name": current_user.name if current_user else "Unknown"}
        )
        if analysis["risks"]:
            advisor_suggestions = f"⚠️ Risks: {', '.join(analysis['risks'])}"
            print(f"[SYBOT] 💡 {advisor_suggestions}")
    except Exception as e:
        print(f"[SYBOT] Advisor error: {e}")
    
    # ... rest of the existing tool execution code ...
```

### Step 5: Update Memory Saving to Use New Memory Manager

Modify the save_memory tool handler:

```python
# In _execute_tool method, replace the existing save_memory handler:
if name == "save_memory":
    category = args.get("category", "notes")
    key = args.get("key", "")
    value = args.get("value", "")
    
    if key and value and current_user:
        # NEW: Use new memory manager
        self.memory_manager.add_user_memory(
            user_id=current_user.user_id,
            category=category,
            key=key,
            value=value
        )
        # Also add interaction to history
        self.memory_manager.add_interaction(
            user_id=current_user.user_id,
            interaction={
                "intent": "save_memory",
                "category": category,
                "key": key,
                "summary": f"Saved {category}/{key}"
            }
        )
        print(f"[Memory] 💾 save_memory: {category}/{key} = {value}")
    
    if not self.ui.muted:
        self.ui.set_state("LISTENING")
    return types.FunctionResponse(
        id=fc.id, name=name,
        response={"result": "ok", "silent": True}
    )
```

### Step 6: Add Voice Recognition (Optional Enhancement)

To enable voice recognition in the `_listen_audio` method, you can add:

```python
async def _listen_audio(self):
    print("[SYBOT] 🎤 Mic started")
    loop = asyncio.get_event_loop()
    
    def callback(indata, frames, time_info, status):
        with self._speaking_lock:
            sybot_speaking = self._is_speaking
        if not sybot_speaking and not self.ui.muted:
            data = indata.tobytes()
            
            # NEW: Optional speaker identification
            # This would require collecting audio samples and processing them
            # For now, we'll skip this to keep the system responsive
            
            loop.call_soon_threadsafe(
                self.out_queue.put_nowait,
                {"data": data, "mime_type": "audio/pcm"}
            )
    
    # ... rest of the existing code ...
```

## Installation Instructions

### Install New Dependencies

```bash
pip install -r requirements_new.txt
```

Or install individually:

```bash
# Voice & Speech
pip install speechrecognition pydub webrtcvad librosa soundfile

# Speaker Recognition
pip install speechbrain resemblyzer

# Emotion Detection
pip install transformers torch
```

## Testing the Integration

1. **Test User Manager:**
```python
from core.user_manager import UserManager
from pathlib import Path

um = UserManager(Path(__file__).parent.parent)
print(um.list_users())
```

2. **Test Memory Manager:**
```python
from core.memory_manager import MemoryManager
from pathlib import Path

mm = MemoryManager(Path(__file__).parent.parent)
mm.add_user_memory("test_user", "preferences", "test_key", "test_value")
print(mm.get_user_memory("test_user"))
```

3. **Test Advisor Engine:**
```python
from core.advisor_engine import AdvisorEngine
from pathlib import Path

ae = AdvisorEngine(Path(__file__).parent.parent)
analysis = ae.analyze_request("delete system32", {})
print(analysis)
```

## Security Considerations

1. **Leader Privileges:** The system now distinguishes between the leader (Nshuti Moise) and other users. Leader commands execute without confirmation.

2. **File System Access:** Previously removed restrictions are still in place. Ensure you understand the risks of unlimited file system access.

3. **Voice Data:** Voice embeddings are stored in `memory/user_profiles/` - ensure this directory is protected.

4. **Memory Storage:** All user data is stored in `memory/long_term.json` - keep this file secure.

## Rollback Plan

If you need to rollback:
1. Remove the new imports from main.py
2. Remove the initialization code from `__init__`
3. Restore the original `_build_config` method
4. Remove permission checks from `_execute_tool`
5. The existing memory system will continue to work

## Next Steps

1. **Backup main.py** before making changes
2. **Apply changes incrementally** - one section at a time
3. **Test after each change** to ensure the system still works
4. **Monitor logs** for any errors from the new modules
5. **Gradually enable features** - start with user manager, then memory, then voice/emotion

## Optional Enhancements

After basic integration, consider:
1. Adding a voice enrollment process for new users
2. Implementing emotion-based response adaptation
3. Adding proactive suggestions based on user history
4. Creating a web dashboard for user management
5. Adding encryption for stored voice embeddings
