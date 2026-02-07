import wave
import numpy as np

def find_best_moment(wav_path, window_size_sec=30, step_size_sec=5):
    with wave.open(wav_path, 'rb') as wav:
        params = wav.getparams()
        n_channels, sampwidth, framerate, n_frames = params[:4]
        
        # Read in chunks to avoid memory issues
        chunk_size = framerate * window_size_sec
        step_size = framerate * step_size_sec
        
        max_rms = 0
        best_start_time = 0
        
        for start_frame in range(0, n_frames - chunk_size, step_size):
            wav.setpos(start_frame)
            frames = wav.readframes(chunk_size)
            samples = np.frombuffer(frames, dtype=np.int16)
            
            if len(samples) == 0:
                continue
                
            rms = np.sqrt(np.mean(samples.astype(np.float32)**2))
            if rms > max_rms:
                max_rms = rms
                best_start_time = start_frame / framerate
                
    return best_start_time, max_rms

if __name__ == "__main__":
    start_time, rms = find_best_moment('/mnt/d/ai-videos/audio.wav')
    print(f"BEST_START_TIME: {start_time}")
    print(f"MAX_RMS: {rms}")
