import customtkinter as ctk
import sounddevice as sd
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import scipy.signal as signal
import scipy.io.wavfile as wav
import tkinter.filedialog as fd
import threading

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class Ultimate_AI_ANC_Telemetry(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DRDO Edge-ANC | Hybrid AI-DSP Architecture [SIH26052]")
        self.geometry("1100x750")
        self.is_running = False
        self.ml_enabled = False
        self.noise_type = "tank"
        self.audio_source = "mic"
        
        # Audio Buffers
        self.CHUNK = 1024
        self.RATE = 16000
        self.raw_buffer = np.zeros(self.CHUNK)
        self.clean_buffer = np.zeros(self.CHUNK)
        self.time_counter = 0
        
        # File Playback variables
        self.file_data = None
        self.file_idx = 0

        # AI / NLMS Parameters
        self.TAPS = 128
        self.mu = 0.05 
        self.weights = np.zeros(self.TAPS)
        self.delay_line = np.zeros(self.TAPS)
        
        self.setup_ui()
        self.setup_plots()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color="#10151b")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.sidebar, text="C2 INTERFACE", font=("Consolas", 20, "bold"), text_color="#58a6ff").pack(pady=(20, 5))
        ctk.CTkLabel(self.sidebar, text="Arch: AI-Assisted NLMS", font=("Consolas", 10), text_color="gray").pack(pady=(0, 20))
        
        self.btn_mic = ctk.CTkButton(self.sidebar, text="DEPLOY LIVE MIC", fg_color="#238636", font=("Consolas", 12, "bold"), command=self.start_mic)
        self.btn_mic.pack(pady=10, padx=20, fill="x")
        
        self.btn_file = ctk.CTkButton(self.sidebar, text="UPLOAD WAV FILE", fg_color="#d29922", font=("Consolas", 12, "bold"), command=self.load_file)
        self.btn_file.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(self.sidebar, text="BATTLEFIELD NOISE MODE", font=("Consolas", 11, "bold"), text_color="gray").pack(pady=(20,5), anchor="w", padx=20)
        self.noise_selector = ctk.CTkOptionMenu(self.sidebar, values=["Tank (Synthetic)", "Heli (Synthetic)", "Gunfire (Synthetic)", "Auto AI Adapt (Real Env)"], font=("Consolas", 12), command=self.change_noise)
        self.noise_selector.pack(padx=20, fill="x")
        self.noise_selector.set("Tank (Synthetic)")
        
        self.btn_toggle = ctk.CTkButton(self.sidebar, text="ENGAGE HYBRID AI", fg_color="#1f538d", state="disabled", font=("Consolas", 12, "bold"), command=self.toggle_ml)
        self.btn_toggle.pack(pady=40, padx=20, fill="x")
        self.btn_stop = ctk.CTkButton(self.sidebar, text="TERMINATE", fg_color="#da3633", state="disabled", font=("Consolas", 12, "bold"), command=self.stop_audio)
        self.btn_stop.pack(pady=10, padx=20, fill="x")

        # Telemetry
        self.metric_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.metric_frame.pack(side="bottom", fill="x", pady=20, padx=20)
        self.status_lbl = ctk.CTkLabel(self.metric_frame, text="AI VAD: INACTIVE", font=("Consolas", 12, "bold"), text_color="gray")
        self.status_lbl.pack(anchor="w")
        self.snr_lbl = ctk.CTkLabel(self.metric_frame, text="ATTENUATION: -- dB", font=("Consolas", 12, "bold"), text_color="#39d353")
        self.snr_lbl.pack(anchor="w")

        # Visuals
        self.main_frame = ctk.CTkFrame(self, fg_color="#090c10")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

    def setup_plots(self):
        self.fig = Figure(figsize=(8, 6), facecolor='#090c10', dpi=100)
        self.fig.subplots_adjust(hspace=0.4, left=0.08, right=0.95, top=0.92, bottom=0.08)
        
        self.ax_time = self.fig.add_subplot(211)
        self.ax_time.set_facecolor('#161b22')
        self.ax_time.set_title("Time Domain: AI-Assisted Output", color="white", fontsize=10, fontfamily='monospace')
        self.ax_time.set_ylim(-2.0, 2.0)
        self.ax_time.set_xlim(0, self.CHUNK)
        self.ax_time.axis('off')
        
        self.line_raw, = self.ax_time.plot(np.zeros(self.CHUNK), color='#d29922', alpha=0.4, label="Primary Mic (Corrupted)")
        self.line_clean, = self.ax_time.plot(np.zeros(self.CHUNK), color='#39d353', linewidth=1.5, label="ML Processed")
        self.ax_time.legend(loc="upper right", facecolor='#161b22', edgecolor='none', labelcolor='white')

        self.ax_freq = self.fig.add_subplot(212)
        self.ax_freq.set_facecolor('#161b22')
        self.ax_freq.set_title("Spectral Classification (FFT)", color="white", fontsize=10, fontfamily='monospace')
        self.ax_freq.set_ylim(0, 100)
        self.ax_freq.set_xlim(0, 4000) 
        self.ax_freq.tick_params(colors='gray', labelsize=8)
        
        self.x_freq = np.linspace(0, self.RATE / 2, self.CHUNK // 2)
        self.line_fft, = self.ax_freq.plot(self.x_freq, np.zeros(self.CHUNK // 2), color='#58a6ff', linewidth=1.2)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def change_noise(self, value):
        if "Tank" in value: self.noise_type = "tank"
        elif "Heli" in value: self.noise_type = "heli"
        elif "Gunfire" in value: self.noise_type = "gunfire"
        else: self.noise_type = "auto" # Auto Adapt to real environment

    def load_file(self):
        filepath = fd.askopenfilename(filetypes=[("WAV Audio", "*.wav")])
        if not filepath: return
        
        fs, data = wav.read(filepath)
        # Normalize and convert to mono
        if data.ndim > 1: data = data.mean(axis=1)
        self.file_data = data / np.max(np.abs(data))
        self.file_idx = 0
        self.RATE = fs
        self.audio_source = "file"
        self.start_audio_stream()

    def extract_ai_features(self, audio_frame):
        f, Pxx = signal.periodogram(audio_frame, fs=self.RATE)
        voice_energy = np.sum(Pxx[np.where((f > 300) & (f < 3000))[0]])
        noise_energy = np.sum(Pxx[np.where(f < 300)[0]]) + 1e-6
        return 1 if (voice_energy / noise_energy) > 0.8 else 0

    def process_dsp_frame(self, base_audio, frames):
        t = np.linspace(self.time_counter, self.time_counter + frames, frames)
        self.time_counter += frames
        
        # Determine Noise Injection based on Mode
        if self.noise_type == "tank":
            noise_ref = (np.sin(t * 0.05) * 0.5) + (np.sin(t * 0.02) * 0.3) + np.random.normal(0, 0.05, frames)
            primary_mic = base_audio + noise_ref
        elif self.noise_type == "heli":
            noise_ref = (np.sin(t * 0.1) * np.sin(t * 0.01) * 0.8) + np.random.normal(0, 0.02, frames)
            primary_mic = base_audio + noise_ref
        elif self.noise_type == "gunfire":
            noise_ref = np.where(np.random.random(frames) > 0.98, np.random.normal(0, 1.2, frames), np.random.normal(0, 0.05, frames))
            primary_mic = base_audio + noise_ref
        else:
            # AUTO AI ADAPT: No fake noise. Takes raw mic/file and uses self-delay as reference.
            primary_mic = base_audio
            noise_ref = np.roll(base_audio, 1) 
            
        cleaned = np.zeros(frames)
        
        if self.ml_enabled:
            speech_present = self.extract_ai_features(primary_mic)
            self.current_vad = speech_present
            
            for i in range(frames):
                self.delay_line[1:] = self.delay_line[:-1]
                self.delay_line[0] = noise_ref[i]
                
                estimated_noise = np.dot(self.weights, self.delay_line)
                error = primary_mic[i] - estimated_noise
                cleaned[i] = error
                
                if not speech_present: # Only update weights if AI detects NO speech
                    norm = np.dot(self.delay_line, self.delay_line) + 1e-6
                    self.weights += (self.mu * error * self.delay_line) / norm
        else:
            cleaned = primary_mic
            self.current_vad = -1
            
        self.raw_buffer = primary_mic
        self.clean_buffer = cleaned
        return cleaned

    def audio_callback(self, indata, outdata, frames, time_info, status):
        # Read from File or Mic
        if self.audio_source == "file" and self.file_data is not None:
            end_idx = self.file_idx + frames
            if end_idx > len(self.file_data): 
                self.file_idx = 0 # Loop file
                end_idx = frames
            base_audio = self.file_data[self.file_idx:end_idx]
            self.file_idx = end_idx
        else:
            base_audio = indata[:, 0]

        # DSP Processing
        cleaned = self.process_dsp_frame(base_audio, frames)
        
        # Output to speakers ONLY if using File (to avoid Mic feedback)
        if self.audio_source == "file" and outdata is not None:
            outdata[:, 0] = cleaned

    def update_plot(self):
        if not self.is_running: return
        
        self.line_raw.set_ydata(self.raw_buffer)
        self.line_clean.set_ydata(self.clean_buffer)
        
        fft_data = np.abs(np.fft.rfft(self.clean_buffer)) * 2 / self.CHUNK
        self.line_fft.set_ydata(fft_data[:-1])
        
        if np.max(fft_data) > 0.1: self.ax_freq.set_ylim(0, np.max(fft_data) * 1.5)
        self.canvas.draw_idle()
        
        if self.ml_enabled:
            raw_rms = np.sqrt(np.mean(self.raw_buffer**2)) + 1e-6
            cln_rms = np.sqrt(np.mean(self.clean_buffer**2)) + 1e-6
            att = 20 * np.log10(raw_rms / cln_rms)
            self.snr_lbl.configure(text=f"ATTENUATION: -{att:.1f} dB" if att > 0 else "ATTENUATION: 0.0 dB")
            self.status_lbl.configure(text="AI VAD: SPEECH DETECTED", text_color="#39d353") if self.current_vad == 1 else self.status_lbl.configure(text="AI VAD: NOISE ONLY", text_color="#d29922")
        else:
            self.snr_lbl.configure(text="ATTENUATION: -- dB")
            self.status_lbl.configure(text="AI VAD: INACTIVE", text_color="gray")

        self.after(30, self.update_plot)

    def toggle_ml(self):
        self.ml_enabled = not self.ml_enabled
        if self.ml_enabled:
            self.btn_toggle.configure(text="BYPASS FILTER", fg_color="#d29922")
            self.line_clean.set_alpha(1.0)
            self.weights.fill(0)
        else:
            self.btn_toggle.configure(text="ENGAGE HYBRID AI", fg_color="#39d353")
            self.line_clean.set_alpha(0.0)

    def start_mic(self):
        self.audio_source = "mic"
        self.RATE = 16000
        self.start_audio_stream()

    def start_audio_stream(self):
        if self.is_running: self.stop_audio()
        self.is_running = True
        self.ml_enabled = False
        self.btn_mic.configure(state="disabled")
        self.btn_file.configure(state="disabled")
        self.btn_toggle.configure(state="normal", fg_color="#39d353")
        self.btn_stop.configure(state="normal")
        
        # If file, output to speakers. If mic, input only.
        if self.audio_source == "file":
            self.stream = sd.Stream(channels=1, samplerate=self.RATE, blocksize=self.CHUNK, callback=self.audio_callback)
        else:
            self.stream = sd.InputStream(channels=1, samplerate=self.RATE, blocksize=self.CHUNK, callback=self.audio_callback)
            
        self.stream.start()
        self.update_plot()

    def stop_audio(self):
        self.is_running = False
        if hasattr(self, 'stream'): self.stream.stop()
        self.btn_mic.configure(state="normal")
        self.btn_file.configure(state="normal")
        self.btn_toggle.configure(state="disabled", text="ENGAGE HYBRID AI", fg_color="#1f538d")
        self.btn_stop.configure(state="disabled")
        
if __name__ == "__main__":
    app = Ultimate_AI_ANC_Telemetry()
    app.mainloop()
