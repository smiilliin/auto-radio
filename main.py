#!/usr/bin/env python
# coding: utf-8

# In[258]:


import dotenv

dotenv.load_dotenv()


# In[259]:


import os

openrouter_key = os.getenv("OPENROUTER_KEY")


# In[260]:


# from openai import OpenAI

# client = OpenAI(
#     base_url="https://openrouter.ai/api/v1",
#     api_key=openrouter_key,
# )

# # First API call with reasoning
# response = client.chat.completions.create(
#     model="openai/gpt-oss-20b:free",
#     messages=[
#         {"role": "user", "content": "How many r's are in the word 'strawberry'?"}
#     ],
#     extra_body={"reasoning": {"enabled": True}},
# )

# # Extract the assistant message with reasoning_details
# response = response.choices[0].message


# In[261]:


# print(response)


# In[262]:


from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_key,
)


# In[ ]:


TOPIC_PROMPT = """
일본어 라디오에서 사용할 주제를 1개 생성하라.

[조건]

- JLPT {LEVEL} 수준.
- 일상적이고 공감 가능한 주제.
- 10~15분 분량의 라디오로 확장 가능해야 한다.
- 설명하기 쉬운 일본어 표현이 최소 2개 이상 떠오르는 주제여야 한다.
- 주제는 반드시 끝에 について가 붙으며, 자연스러운 형태여야 한다.

좋은 예:
- コンビニでよく買うものについて
- 雨の日の過ごし方について
- 好きなおにぎりについて
- 朝のルーティンについて
- カフェで勉強する話について

나쁜 예:
- 宇宙の起源
- 実存主義
- 量子力学
- グローバル経済
- 一番好きな季節

[출력 규칙]

- 주제 한 줄만 출력.
- 따옴표 사용 금지.
- 번호 금지.
- 20자 이내.

[중복 방지]

{PREVIOUS_TOPICS}
"""

SCRIPT_PROMPT = """
주제:
{TOPIC}

이 주제를 기반으로 JLPT {LEVEL} 수준 청취자를 위한 일본어 라디오 스크립트를 작성하라.

다음 문장은 이미 방송에서 읽혔다.
절대 다시 생성하지 마라.

- みなさん、こんにちは！
- 「ゆるっと電波 {LEVEL}」へようこそ！
- 私はハヤトです。

당신은 이제 방송을 이어서 진행한다.

프로그램 정보:
- 프로그램명: ゆるっと電波 {LEVEL}
- 진행자: ハヤト

언어 수준:
- JLPT {LEVEL} 수준의 어휘와 문법을 우선 사용
- 불가피하게 어려운 표현이 포함될 경우 최대 5개 이하로 제한
- 어려운 단어는 가능한 쉬운 표현으로 바꿈

스타일:
- 캐주얼하고 부드러운 말투 사용 (친근한 라디오 진행자 느낌)
- 청자에게 말을 거는 표현 포함 (예: みなさん、どうですか？)
- 딱딱한 설명체 금지

문장 구조:
- 문장은 짧고 유기적으로 작성
- 문장을 과도하게 길게 작성하지 않음(한 문장 35자 이내)
- 자연스러운 호흡을 위해 「、」「。」 적절히 사용

청해 최적화:
- 발음하기 어려운 한자, 언어 수준에 맞지 않은 한자, 외래어, 숫자는 필요할 때만 풀어서 표현
- 의미 단위로 끊어 읽기 쉽게 구성

재미 요소:
- 가벼운 감정 표현 또는 공감 요소 포함
- 청취자가 상황을 상상할 수 있도록 묘사 추가

규칙:
- JLPT {LEVEL} 수준의 일본어를 사용한다.
- 진행자는 오래 알고 지낸 라디오 DJ처럼 이야기한다.
- 모든 문장은 TTS에 적합해야 한다.
- 일본어만 사용한다.
- 영어, 한국어, 독일어 및 기타 언어를 사용하지 않는다.
- 「ふふっ」「まあ」「ああ」와 같은 가벼운 감탄 표현은 허용한다.
- 각 text는 하나의 문장만 가진다.
- 하나의 text에 두 개 이상의 문장을 넣는 것을 금지한다.

반드시 다음 구성을 따른다.

[オープニング]
- 2~3개의 문장.
- 주제와 관련된 시작 멘트 포함.
- 첫 문장은 반드시:
  「今日は、{TOPIC}お話しします」
- 이후 1~2개의 문장으로 오프닝 멘트 이어 적기.:
  청취자를 편하게 만드는 한 문장
  예:
  - ふふっ、ゆっくり聞いてくださいね。
  - 今日はのんびりお付き合いください。
  - 一緒に楽しい時間を過ごしましょう。

[セグメント1]
- 5~8개의 문장.
- 주제에 대한 이야기.
- 마지막 문장은 청취자에게 질문한다.

[セグメント2]
- 5~8개의 문장.
- 주제에 대한 이야기.
- 마지막 문장은 청취자에게 질문한다.

[セグメント3]
- 5~8개의 문장.
- 주제를 마무리한다.
- 마지막 문장은 청취자가 자신의 경험을 떠올리게 한다.

[コーナー]
- 6~10개의 문장.
- 첫 문장은 반드시:
  「ここで、今日の日本語の表現を紹介します。」
- 핵심 표현 2개를 소개한다.
- 비슷한 표현 1개를 소개한다.
- 예문 1개를 제시한다.
- 마지막 문장은 반드시:
  「では、言ってみましょう。」

[エンディング]
- 5~7개의 문장.
- 첫 문장은 청취자에게 마지막 질문을 한다.
- 마지막 문장은 따뜻한 인사로 마무리한다.

출력은 반드시 아래 JSON 형식을 따른다.

[
    {"part":"...","text":"..."},
    ...
]

추가 규칙:
- JSON 배열만 출력한다.
- code block을 사용하지 않는다.
- 설명을 출력하지 않는다.
- JSON 배열의 각 원소는 라디오 진행자가 한 번 숨을 쉬기 전에 말하는 하나의 발화이다.
- part는 opening, part1, part2, part3, corner, ending 중 하나만 사용한다.

출력 결과는 반드시 유효한 JSON 배열이 되도록 점검한다.
"""
PRE_SCRIPT = """
みなさん、こんにちは！
「ゆるっと電波 {LEVEL}」へようこそ！
私はハヤトです。
"""

REF_TEXT = "こんにちは、みなさん！「ゆるっと電波 Nご」にようこそ！私はハヤトです。今日は楽しいお話をたくさんしますよ。よろしくお願いしますね！"


# In[ ]:


import json
from pathlib import Path


class ScriptManager:
    base_path: Path
    topics: list[str]

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.topics = self.load_topics()

    def load_topics(self):
        topics_file = self.base_path / "topics.json"

        if topics_file.exists():
            with open(topics_file, "r", encoding="utf-8") as f:
                return json.load(f)

        return []

    def save_topics(self):
        topics_file = self.base_path / "topics.json"

        with open(topics_file, "w", encoding="utf-8") as f:
            json.dump(self.topics, f, indent=2, ensure_ascii=False)

    def new_topic(self, topic: str, now: str):
        self.topics.append(
            {
                "time": now,
                "topic": topic,
            }
        )
        self.save_topics()

    def save_script(self, script, topic, now):
        scripts_dir = self.base_path / "scripts"
        if not scripts_dir.exists():
            scripts_dir.mkdir(parents=True)

        data = {"time": now, "topic": topic, "script": script}

        filename = os.path.join(scripts_dir, f"{now}.json")

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# In[ ]:


from langgraph.graph import StateGraph
from typing import TypedDict, Optional, Callable
from pathlib import Path
import json
from datetime import datetime
from pydub import AudioSegment
import time

from omnivoice import OmniVoice
import soundfile as sf
import torch
import numpy as np


class RadioState(TypedDict):
    topic: Optional[str]
    script: Optional[str]
    tts_script: Optional[str]
    audio_path: Optional[str]
    now: Optional[str]


class AudioManager:
    base_path: Path
    bgm_path: Path
    ref_text: str
    model: OmniVoice

    def __init__(self, base_path: Path, ref_text: str, bgm_path: Path):
        self.base_path = base_path
        self.model = OmniVoice.from_pretrained(
            "k2-fsa/OmniVoice", device_map="cuda:0", dtype=torch.float16
        )
        self.ref_text = ref_text
        self.bgm_path = bgm_path

    def preprocess_for_tts(self, script):
        processed_script = []

        for i, item in enumerate(script):
            if i == len(script) - 1:
                pause = 500
            else:
                next_item = script[i + 1]
                if item["part"] == next_item["part"]:
                    pause = 200
                else:
                    pause = 500

            processed_script.append((item["text"], pause))

        return processed_script

    def save_tts(self, script, now):
        if not self.base_path.joinpath("tts").exists():
            self.base_path.joinpath("tts").mkdir(parents=True)

        output_path = self.base_path / "tts" / f"{now}.mp3"

        result = []

        for text, pause in script:
            audio = self.model.generate(
                text=text, ref_audio="ref.wav", ref_text=self.ref_text
            )[0]

            result.append(audio)

            silence = np.zeros(int(24000 * pause / 1000), dtype=np.float32)

            result.append(silence)

        final = np.concatenate(result)

        sf.write(output_path, final, 24000)

        # print(f"🎧 audio file saved: {output_path}")

        return output_path

    def mix_bgm(self, now):
        if not self.base_path.joinpath("audio").exists():
            self.base_path.joinpath("audio").mkdir(parents=True)

        tts_path = self.base_path / "tts" / f"{now}.mp3"
        # bgm_path = self.base_path / "bgm.mp3"
        output_path = self.base_path / "audio" / f"{now}.mp3"

        voice = AudioSegment.from_file(tts_path)
        bgm = AudioSegment.from_file(self.bgm_path)

        # BGM 길이를 음성에 맞춤 (loop)
        if len(bgm) < len(voice):
            times = len(voice) // len(bgm) + 1
            bgm = bgm * times

        bgm = bgm[: len(voice)]

        bgm = bgm - 20  # dB 줄임

        # 합치기
        mixed = voice.overlay(bgm)

        mixed.export(output_path, format="mp3")

        # print(f"🎶 bgm is mixed: {output_path}")
        return output_path


class Radiograph(StateGraph[RadioState]):
    client: OpenAI
    is_debug: bool

    level: str

    TOPIC_PROMPT: str
    SCRIPT_PROMPT: str
    PRE_SCRIPT: str

    script_manager: ScriptManager
    audio_manager: AudioManager

    def __init__(
        self,
        client: OpenAI,
        base_path: Path,
        level: str,
        REF_TEXT: str,
        TOPIC_PROMPT: str,
        SCRIPT_PROMPT: str,
        PRE_SCRIPT: str,
        is_debug: bool = False,
    ):
        super().__init__(
            state_schema=RadioState,
            name="Radiograph",
        )

        if not base_path.exists():
            base_path.mkdir(parents=True)

        self.script_manager = ScriptManager(base_path=base_path)
        self.audio_manager = AudioManager(
            base_path=base_path, ref_text=REF_TEXT, bgm_path=Path(".") / "bgm.mp3"
        )

        self.client = client
        self.is_debug = is_debug

        self.level = level

        self.TOPIC_PROMPT = TOPIC_PROMPT
        self.SCRIPT_PROMPT = SCRIPT_PROMPT
        self.PRE_SCRIPT = PRE_SCRIPT

        self.add_node("topic", self.topic_node)
        self.add_node("script", self.script_node)
        self.add_node("tts", self.tts_node)

        self.set_entry_point("topic")

        self.add_edge("topic", "script")
        self.add_edge("script", "tts")

    def debug(self, message: str):
        if self.is_debug:
            print(message)

    def run_prompt(
        self,
        prompt: str,
        model: str = "openai/gpt-oss-20b:free",
        reasoning: bool = True,
        validation: Callable[[str], bool] = None,
        max_retries: int = 3,
    ):
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    extra_body={"reasoning": {"enabled": reasoning}},
                )

            except Exception as e:
                self.debug(f"OpenRouter Error: {e}")

                time.sleep(5)
                continue

            self.debug(f"response: {response}")

            message = response.choices[0].message.content

            if not message:
                self.debug(f"Validation failed for attempt {attempt + 1}. Retrying...")
                continue
            else:
                if validation and not validation(message):
                    self.debug(
                        f"Validation failed for attempt {attempt + 1}. Retrying..."
                    )
                    continue

                return message.strip()

        raise ValueError("Max retries exceeded")

    def topic_node(self, state: RadioState):
        previous_topics = self.script_manager.load_topics()

        self.debug(f"previous_topics: {previous_topics}")

        prompt = self.TOPIC_PROMPT.replace("{LEVEL}", self.level).replace(
            "{PREVIOUS_TOPICS}",
            json.dumps(
                [topic["topic"] for topic in previous_topics], ensure_ascii=False
            ),
        )

        self.debug(f"topic_node prompt: {prompt}")

        topic = self.run_prompt(
            prompt, model="google/gemma-4-26b-a4b-it:free", reasoning=False
        )

        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.script_manager.new_topic(topic, now)

        state["now"] = now
        state["topic"] = topic

        self.debug(f"generated topic: {topic}")

        return state

    def script_validation(self, message: str) -> bool:
        try:
            parsed = json.loads(message)
            if not isinstance(parsed, list):
                return False

            for item in parsed:
                if not isinstance(item, dict):
                    return False
                if "part" not in item or "text" not in item:
                    return False
                if not isinstance(item["part"], str) or not isinstance(
                    item["text"], str
                ):
                    return False

            return True
        except json.JSONDecodeError:
            return False

    def script_node(self, state: RadioState):
        self.debug(f"topic: {state['topic']}")

        prompt = self.SCRIPT_PROMPT.replace("{LEVEL}", self.level).replace(
            "{TOPIC}", state["topic"]
        )

        self.debug(f"script_node prompt: {prompt}")

        script = self.run_prompt(
            prompt,
            validation=self.script_validation,
        )

        script = json.loads(script)
        pre_script = self.PRE_SCRIPT.replace("{LEVEL}", self.level).strip().split("\n")
        pre_script = [{"part": "opening", "text": line} for line in pre_script]

        script = pre_script + script

        now = state["now"]

        self.script_manager.save_script(script, state["topic"], now)

        state["script"] = script

        self.debug(f"generated script: {script}")

        return state

    # def rewrite_tts_node(self, state: RadioState):
    #     self.debug(f"script: {state['script']}")

    #     prompt = self.REWRITE_TTS_PROMPT.replace("{LEVEL}", self.level).replace(
    #         "{SCRIPT}", state["script"]
    #     )

    #     self.debug(f"rewrite_tts_node prompt: {prompt}")

    #     tts_script = self.run_prompt(prompt, self.test_sectors)
    #     tts_script = self.replace_sectors(tts_script)

    #     state["tts_script"] = tts_script

    #     self.debug(f"generated tts_script: {tts_script}")

    #     return state

    def tts_node(self, state: RadioState):
        # # Save the TTS script to a file
        now = state["now"]
        topic = state["topic"]
        script = state["script"]

        tts_script = self.audio_manager.preprocess_for_tts(script)

        self.script_manager.save_script(tts_script, topic, now)

        tts_path = self.audio_manager.save_tts(tts_script, now)
        self.debug(f"🎧 TTS audio saved for topic '{topic}' at {tts_path}")

        audio_path = self.audio_manager.mix_bgm(now)
        self.debug(f"🎶 BGM mixed for topic '{topic}' at {audio_path}")

        state["audio_path"] = audio_path

        return state


# In[ ]:


graph = Radiograph(
    client=client,
    base_path=Path("./jlpt_n4"),
    level="N4",
    REF_TEXT=REF_TEXT,
    TOPIC_PROMPT=TOPIC_PROMPT,
    SCRIPT_PROMPT=SCRIPT_PROMPT,
    PRE_SCRIPT=PRE_SCRIPT,
    is_debug=True,
)
app = graph.compile()


# In[267]:


result = app.invoke(RadioState())


# In[ ]:


print(result)

