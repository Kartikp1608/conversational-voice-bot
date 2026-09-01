import numpy as np

from utils.audio_utils import AudioUtils
from vad.vad_engine import VADEngine, VADState


def test_vad_silence_detection():
    vad = VADEngine(speech_pad_ms=60, silence_timeout_ms=100)
    silence_frame = AudioUtils.create_silence(20)

    state, rms, is_speech = vad.process_frame(silence_frame)
    assert state == VADState.SILENCE
    assert not is_speech
    assert rms < 0.01


def test_vad_speech_start_and_end():
    vad = VADEngine(speech_pad_ms=40, silence_timeout_ms=60)

    # Generate loud speech frame (sine wave)
    samples = (np.sin(np.linspace(0, 1, 320)) * 20000).astype(np.int16).tobytes()
    silence_frame = AudioUtils.create_silence(20)

    # Frame 1: speech detected but pad not reached
    state, _, _ = vad.process_frame(samples)

    # Frame 2: speech pad reached -> SPEECH_START
    state, _, _ = vad.process_frame(samples)
    assert state == VADState.SPEECH_START

    # Silence frames -> SPEECH_END
    vad.process_frame(silence_frame)
    vad.process_frame(silence_frame)
    state, _, _ = vad.process_frame(silence_frame)
    assert state == VADState.SPEECH_END
