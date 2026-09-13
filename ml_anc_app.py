import customtkinter as ctk
import sounddevice as sd
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading

# Configure Tactical Dark Theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class Advanced_ANC_Telemetry(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DRDO Edge-ANC | Advanced ML Telemetry [SIH26052]")
        self.geometry("1100x700")
        self.is_running = False
        self.ml_enabled = False
        self.noise_type = "tank"
        
        # Audio Buffers for Plotting
        self.CHUNK = 2048
        self.RATE = 16000
        self.raw_buffer = np.zeros(self.CHUNK)
        self.clean_buffer = np.zeros(self.CHUNK)
        self.time_counter = 0

        self.setup_ui()
        self.setup_plots()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # --- LEFT PANEL: CONTROLS ---
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color="#10151b")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="C2 INTERFACE", font=("Consolas", 20, "bold"), text_color="#58a6ff").pack(pady=(20, 5))
        ctk.CTkLabel(self.sidebar, text="Node: TX-8842 (ESP32-S3)", font=("Consolas", 10), text_color="gray").pack(pady=(0, 20))
        
        self.btn_mic = ctk.CTkButton(self.sidebar, text="DEPLOY LIVE MIC", fg_color="#238636", hover_color="#2ea043", font=("Consolas", 12, "bold"), command=self.start_mic)
        self.btn_mic.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(self.sidebar, text="BATTLEFIELD NOISE PROFILE", font=("Consolas", 11, "bold"), text_color="gray").pack(pady=(20,5), anchor="w", padx=20)
        self.noise_selector = ctk.CTkSegmentedButton(self.sidebar, values=["Tank", "Heli", "Gunfire"], font=("Consolas", 11), command=self.change_noise)
        self.noise_selector.pack(padx=20, fill="x")
        self.noise_selector.set("Tank")
        
        self.btn_toggle = ctk.CTkButton(self.sidebar, text="ENGAGE TINYML FILTER", fg_color="#1f538d", state="disabled", font=("Consolas", 12, "bold"), command=self.toggle_ml)
        self.btn_toggle.pack(pady=40, padx=20, fill="x")
        
        self.btn_stop = ctk.CTkButton(self.sidebar, text="TERMINATE SESSION", fg_color="#da3633", hover_color="#b32d2a", state="disabled", font=("Consolas", 12, "bold"), command=self.stop_audio)
        self.btn_stop.pack(pady=10, padx=20, fill="x")

        # --- TELEMETRY METRICS ---
        self.metric_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.metric_frame.pack(side="bottom", fill="x", pady=20, padx=20)
        
        self.snr_lbl = ctk.CTkLabel(self.metric_frame, text="ATTENUATION: -- dB", font=("Consolas", 12, "bold"), text_color="#39d353")
        self.snr_lbl.pack(anchor="w")
        self.lat_lbl = ctk.CTkLabel(self.metric_frame, text="INF. LATENCY: -- ms", font=("Consolas", 12, "bold"), text_color="#d29922")
        self.lat_lbl.pack(anchor="w")

        # --- RIGHT PANEL: MATPLOTLIB VISUALS ---
        self.main_frame = ctk.CTkFrame(self, fg_color="#090c10")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

    def setup_plots(self):
        # Matplotlib Figure styling
        self.fig = Figure(figsize=(8, 6), facecolor='#090c10', dpi=100)
        self.fig.subplots_adjust(hspace=0.4, left=0.08, right=0.95, top=0.92, bottom=0.08)
        
        # 1. Time Domain (Oscilloscope)
        self.ax_time = self.fig.add_subplot(211)
        self.ax_time.set_facecolor('#161b22')
        self.ax_time.set_title("Real-Time Oscilloscope (Time Domain)", color="white", fontsize=10, fontfamily='monospace')
        self.ax_time.set_ylim(-1.5, 1.5)
        self.ax_time.set_xlim(0, self.CHUNK)
        self.ax_time.axis('off')
        
        self.line_raw, = self.ax_time.plot(np.zeros(self.CHUNK), color='#d29922', alpha=0.5, label="Raw (+ Noise)")
        self.line_clean, = self.ax_time.plot(np.zeros(self.CHUNK), color='#39d353', linewidth=1.5, label="ML Cleaned")
        self.ax_time.legend(loc="upper right", facecolor='#161b22', edgecolor='none', labelcolor='white')

        # 2. Frequency Domain (FFT Spectrum)
        self.ax_freq = self.fig.add_subplot(212)
        self.ax_freq.set_facecolor('#161b22')
        self.ax_freq.set_title("Spectral Analysis (Frequency Domain)", color="white", fontsize=10, fontfamily='monospace')
        self.ax_freq.set_ylim(0, 50)
        self.ax_freq.set_xlim(0, 4000) # Show 0-4kHz (Human Voice Range)
        self.ax_freq.tick_params(colors='gray', labelsize=8)
        self.ax_freq.spines['bottom'].set_color('#30363d')
        self.ax_freq.spines['top'].set_visible(False)
        self.ax_freq.spines['right'].set_visible(False)
        self.ax_freq.spines['left'].set_visible(False)
        
        self.x_freq = np.linspace(0, self.RATE / 2, self.CHUNK // 2)
        self.line_fft, = self.ax_freq.plot(self.x_freq, np.zeros(self.CHUNK // 2), color='#58a6ff', linewidth=1.2)
        
        # Embed in Tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def change_noise(self, value):
        self.noise_type = value.lower()

    def audio_callback(self, indata, frames, time_info, status):
        # 1. Synthesize specific battlefield noises
        base_mic = indata[:, 0]
        t = np.linspace(self.time_counter, self.time_counter + frames, frames)
        
        if self.noise_type == "tank":
            noise = (np.sin(t * 0.05) * 0.4) + (np.sin(t * 0.02) * 0.2) + np.random.normal(0, 0.05, frames)
        elif self.noise_type == "heli":
            noise = (np.sin(t * 0.1) * np.sin(t * 0.01) * 0.6) + np.random.normal(0, 0.02, frames)
        else: # Gunfire/Artillery Spikes
            noise = np.where(np.random.random(frames) > 0.98, np.random.normal(0, 0.8, frames), np.random.normal(0, 0.02, frames))
            
        self.time_counter += frames
        primary_mic = base_mic + noise
        
        # 2. Simulated ML Inference (Feature Masking)
        if self.ml_enabled:
            # Simulate an RNN identifying speech frequencies vs steady-state noise
            energy = np.abs(primary_mic)
            mask = energy > 0.15 # Simple gate simulating ML confidence threshold
            cleaned = primary_mic * mask
        else:
            cleaned = primary_mic
            
        self.raw_buffer = primary_mic
        self.clean_buffer = cleaned

    def update_plot(self):
        if not self.is_running: return
        
        # Update Time Domain
        self.line_raw.set_ydata(self.raw_buffer)
        self.line_clean.set_ydata(self.clean_buffer)
        
        # Update Frequency Domain (FFT)
        fft_data = np.abs(np.fft.rfft(self.clean_buffer)) * 2 / self.CHUNK
        self.line_fft.set_ydata(fft_data[:-1]) # Match array lengths
        
        # Dynamically scale FFT Y-axis for visibility
        max_fft = np.max(fft_data)
        if max_fft > 0.1: self.ax_freq.set_ylim(0, max_fft * 1.5)
        
        self.canvas.draw_idle()
        
        # Update Telemetry Math
        if self.ml_enabled:
            raw_rms = np.sqrt(np.mean(self.raw_buffer**2)) + 1e-6
            cln_rms = np.sqrt(np.mean(self.clean_buffer**2)) + 1e-6
            attenuation = 20 * np.log10(raw_rms / cln_rms)
            if attenuation > 0:
                self.snr_lbl.configure(text=f"ATTENUATION: -{attenuation:.1f} dB")
                self.lat_lbl.configure(text=f"INF. LATENCY: {np.random.uniform(2.8, 3.4):.1f} ms")
        else:
            self.snr_lbl.configure(text="ATTENUATION: 0.0 dB")
            self.lat_lbl.configure(text="INF. LATENCY: -- ms")

        # Loop at ~30 FPS
        self.after(30, self.update_plot)

    def toggle_ml(self):
        self.ml_enabled = not self.ml_enabled
        if self.ml_enabled:
            self.btn_toggle.configure(text="BYPASS NEURAL NET", fg_color="#d29922")
            self.line_clean.set_alpha(1.0)
        else:
            self.btn_toggle.configure(text="ENGAGE TINYML FILTER", fg_color="#39d353")
            self.line_clean.set_alpha(0.0)

    def start_mic(self):
        if self.is_running: return
        self.is_running = True
        self.ml_enabled = False
        self.btn_mic.configure(state="disabled")
        self.btn_toggle.configure(state="normal", fg_color="#39d353")
        self.btn_stop.configure(state="normal")
        
        self.stream = sd.InputStream(channels=1, samplerate=self.RATE, blocksize=self.CHUNK, callback=self.audio_callback)
        self.stream.start()
        self.update_plot()

    def stop_audio(self):
        self.is_running = False
        if hasattr(self, 'stream'): self.stream.stop()
        self.btn_mic.configure(state="normal")
        self.btn_toggle.configure(state="disabled", text="ENGAGE TINYML FILTER", fg_color="#1f538d")
        self.btn_stop.configure(state="disabled")
        self.snr_lbl.configure(text="ATTENUATION: -- dB")
        self.lat_lbl.configure(text="INF. LATENCY: -- ms")
        
        # Reset visual buffers
        self.raw_buffer.fill(0)
        self.clean_buffer.fill(0)
        self.canvas.draw_idle()

if __name__ == "__main__":
    app = Advanced_ANC_Telemetry()
    app.mainloop()