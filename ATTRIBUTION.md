# Data and research attribution

The released speech-presence and neural band-gain models were trained using a
speaker-disjoint subset of **Speech Commands**, made available in TensorFlow's
`mini_speech_commands.zip` archive. Credit: **Pete Warden and the Speech Commands
contributors, Google/TensorFlow**. The dataset is released under **Creative Commons
Attribution 4.0 International (CC BY 4.0)**.

- Dataset announcement and attribution: https://research.google/blog/launching-the-speech-commands-dataset/
- License: https://creativecommons.org/licenses/by/4.0/
- Official archive: https://storage.googleapis.com/download.tensorflow.org/data/mini_speech_commands.zip
- Archive hash, selected speaker IDs and protocol: `models/public_data_sources.json`.

The source recordings were normalized, padded and mixed with generated noises
and simulated microphone paths for this project. No source WAV recordings are
redistributed in the repository. The released model weights and reports are
outputs of that training/evaluation. Generated noises must not be described as
actual classified or operational defence recordings.

The general hybrid DSP / learned-band-gain approach is informed by Jean-Marc
Valin's *A Hybrid DSP/Deep Learning Approach to Real-Time Full-Band Speech
Enhancement*: https://arxiv.org/abs/1709.08243 . This implementation uses its own
small MLP and causal IIR bands; it is not RNNoise and does not claim RNNoise's
architecture or published performance.
