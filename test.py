# import os
# from google import genai

# client = genai.Client(
#     api_key=os.environ.get("GEMINI_API_KEY"),
# )

# generation_config = {
#     'temperature': 1,
#     'max_output_tokens': 65536,
#     'top_p': 0.95,
#     'thinking_level': 'high',
# }

# interaction = client.interactions.create(
#     model='models/gemini-3-flash-preview',
#     input='Hi, can you tell me a story on Aristotle and his philosophy?',
#     generation_config=generation_config,
# )

# print(interaction.output_text)


import numpy as np
import sounddevice as sd
from openwakeword.model import Model

# 1. Load the wake word model
oww = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")

# 2. Audio config openWakeWord expects
SAMPLE_RATE = 16000
CHUNK_SIZE = 1280   # 80ms of audio at 16kHz

# 3. Callback: sounddevice calls this every time a chunk is ready
def audio_callback(indata, frames, time_info, status):
    # indata is a numpy array of shape (1280, 1), float32 by default
    # openWakeWord wants int16, so convert
    audio_chunk = (indata[:, 0] * 32767).astype(np.int16)
    
    prediction = oww.predict(audio_chunk)
    score = prediction["hey_jarvis"]
    
    if score > 0.5:
        print(f"🎯 Wake word detected! (confidence: {score:.2f})")

# 4. Open the mic stream and let it run
with sd.InputStream(
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="float32",
    blocksize=CHUNK_SIZE,
    callback=audio_callback,
):
    print("Listening for 'hey jarvis'... (Ctrl+C to stop)")
    while True:
        sd.sleep(1000)

