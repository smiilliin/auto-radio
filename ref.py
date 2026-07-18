from omnivoice import OmniVoice
import soundfile as sf
import torch

model = OmniVoice.from_pretrained(
    "k2-fsa/OmniVoice", device_map="cuda:0", dtype=torch.float16
)

REF_TEXT = "こんにちは、みなさん！「ゆるっと電波 Nご」にようこそ！私はハヤトです。今日は楽しいお話をたくさんしますよ。よろしくお願いしますね！"

script = [
    ("オープニング。", 1000),
    ("今日はゆるっと電波へようこそ！", 500),
    ("ゆっくりした音楽にのせて、まったりとお話ししますね。", 500),
    ("本日はランチメニューの選び方を楽しく考えてみましょう。", 500),
    ("それでは、簡単スタートです！", 1000),
]

import numpy as np
import soundfile as sf

result = []

for text, pause in script:
    audio = model.generate(text=text, ref_audio="ref.wav", ref_text=REF_TEXT)[0]

    result.append(audio)

    silence = np.zeros(int(24000 * pause / 1000), dtype=np.float32)

    result.append(silence)

final = np.concatenate(result)

sf.write("radio.wav", final, 24000)
