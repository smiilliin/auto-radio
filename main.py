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
        self.topics = self.load_topics()

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
import re

# class RadioState(TypedDict):
#     topic: Optional[str]
#     script: Optional[str]
#     tts_script: Optional[str]
#     audio_path: Optional[str]
#     now: Optional[str]


class RadioState(TypedDict):
    topic: Optional[str]

    opening: list[dict]
    part1: list[dict]
    part2: list[dict]
    part3: list[dict]
    corner: list[dict]
    ending: list[dict]

    script: list[dict]

    audio_path: Optional[str]
    now: Optional[str]


class AudioManager:
    base_path: Path
    bgm_path: Path
    ref_text: str
    ref_path: Path
    model: OmniVoice

    def __init__(self, base_path: Path, ref_path: Path, ref_text: str, bgm_path: Path):
        self.base_path = base_path
        self.model = OmniVoice.from_pretrained(
            "k2-fsa/OmniVoice", device_map="cuda:0", dtype=torch.float16
        )
        self.ref_text = ref_text
        self.ref_path = ref_path
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
                text=text, ref_audio=self.ref_path, ref_text=self.ref_text
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
    OPENING_PROMPT: str
    PART1_PROMPT: str
    PART2_PROMPT: str
    PART3_PROMPT: str
    CORNER_PROMPT: str
    ENDING_PROMPT: str
    PRE_SCRIPT: str
    VALIDATION_PATTERN: re.Pattern

    # SCRIPT_PROMPT: str

    script_manager: ScriptManager
    audio_manager: AudioManager

    def __init__(
        self,
        client: OpenAI,
        base_path: Path,
        level: str,
        ref_path: Path,
        ref_text: str,
        bgm_path: Path,
        TOPIC_PROMPT: str,
        OPENING_PROMPT: str,
        PART1_PROMPT: str,
        PART2_PROMPT: str,
        PART3_PROMPT: str,
        CORNER_PROMPT: str,
        ENDING_PROMPT: str,
        PRE_SCRIPT: str,
        VALIDATION_PATTERN: str,
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
            base_path=base_path,
            ref_path=ref_path,
            ref_text=ref_text,
            bgm_path=bgm_path,
        )

        self.client = client
        self.is_debug = is_debug

        self.level = level

        self.TOPIC_PROMPT = TOPIC_PROMPT
        self.OPENING_PROMPT = OPENING_PROMPT
        self.PART1_PROMPT = PART1_PROMPT
        self.PART2_PROMPT = PART2_PROMPT
        self.PART3_PROMPT = PART3_PROMPT
        self.CORNER_PROMPT = CORNER_PROMPT
        self.ENDING_PROMPT = ENDING_PROMPT
        self.PRE_SCRIPT = PRE_SCRIPT
        self.VALIDATION_PATTERN = VALIDATION_PATTERN

        # self.SCRIPT_PROMPT = SCRIPT_PROMPT

        # self.add_node("topic", self.topic_node)
        # self.add_node("script", self.script_node)
        # self.add_node("tts", self.tts_node)

        # self.set_entry_point("topic")

        # self.add_edge("topic", "script")
        # self.add_edge("script", "tts")
        self.add_node("topic", self.topic_node)
        self.add_node("opening", self.opening_node)
        self.add_node("part1", self.part1_node)
        self.add_node("part2", self.part2_node)
        self.add_node("part3", self.part3_node)
        self.add_node("corner", self.corner_node)
        self.add_node("ending", self.ending_node)
        self.add_node("merge", self.merge_node)
        self.add_node("tts", self.tts_node)

        self.set_entry_point("topic")

        self.add_edge("topic", "opening")
        self.add_edge("opening", "part1")
        self.add_edge("part1", "part2")
        self.add_edge("part2", "part3")
        self.add_edge("part3", "corner")
        self.add_edge("corner", "ending")
        self.add_edge("ending", "merge")
        self.add_edge("merge", "tts")

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
        # self.PRE_SCRIPT = PRE_SCRIPTioState):
        previous_topics = self.script_manager.load_topics()

        self.debug(f"previous_topics: {previous_topics}")

        prompt = self.TOPIC_PROMPT.format(
            LEVEL=self.level,
            PREVIOUS_TOPICS=json.dumps(
                [topic["topic"] for topic in previous_topics], ensure_ascii=False
            ),
        )

        self.debug(f"topic_node prompt: {prompt}")

        topic = self.run_prompt(prompt)

        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.script_manager.new_topic(topic, now)

        state["now"] = now
        state["topic"] = topic

        self.debug(f"generated topic: {topic}")

        return state

    # def script_validation(self, message: str) -> bool:
    # try:
    #     parsed = json.loads(message)
    #     if not isinstance(parsed, list):
    #         return False

    #     for item in parsed:
    #         if not isinstance(item, dict):
    #             return False
    #         if "part" not in item or "text" not in item:
    #             return False
    #         if not isinstance(item["part"], str) or not isinstance(
    #             item["text"], str
    #         ):
    #             return False

    #     return True
    # except json.JSONDecodeError:
    #     return False

    # def script_node(self, state: RadioState):
    #     self.debug(f"topic: {state['topic']}")

    #     prompt = self.SCRIPT_PROMPT.replace("{LEVEL}", self.level).replace(
    #         "{TOPIC}", state["topic"]
    #     )

    #     self.debug(f"script_node prompt: {prompt}")

    #     script = self.run_prompt(
    #         prompt,
    #         validation=self.script_validation,
    #     )

    #     script = json.loads(script)
    #     pre_script = self.PRE_SCRIPT.replace("{LEVEL}", self.level).strip().split("\n")
    #     pre_script = [{"part": "opening", "text": line} for line in pre_script]

    #     script = pre_script + script

    #     now = state["now"]

    #     self.script_manager.save_script(script, state["topic"], now)

    #     state["script"] = script

    #     self.debug(f"generated script: {script}")

    #     return state
    def script_to_json(self, script: str, part: str) -> list[dict]:
        script = script.strip().split("\n")
        return [{"part": part, "text": line} for _, line in enumerate(script)]

    def script_validation(self, message: str) -> bool:
        if not re.fullmatch(self.VALIDATION_PATTERN, message):
            return False

        return True

    def opening_node(self, state):
        prompt = self.OPENING_PROMPT.format(
            LEVEL=self.level,
            TOPIC=state["topic"],
        )

        result = self.run_prompt(
            prompt,
            validation=self.script_validation,
        )

        state["opening"] = self.script_to_json(result, "opening")
        self.debug(f"generated opening: {state['opening']}")

        return state

    def part1_node(self, state):
        prompt = self.PART1_PROMPT.format(
            LEVEL=self.level,
            TOPIC=state["topic"],
        )

        result = self.run_prompt(
            prompt,
            validation=self.script_validation,
        )

        state["part1"] = self.script_to_json(result, "part1")
        self.debug(f"generated part1: {state['part1']}")

        return state

    def part2_node(self, state):
        previous = state["opening"] + state["part1"]

        prompt = self.PART2_PROMPT.format(
            LEVEL=self.level,
            TOPIC=state["topic"],
            PREVIOUS=json.dumps(
                previous,
                ensure_ascii=False,
            ),
        )

        result = self.run_prompt(
            prompt,
            validation=self.script_validation,
        )

        state["part2"] = self.script_to_json(result, "part2")
        self.debug(f"generated part2: {state['part2']}")

        return state

    def part3_node(self, state):
        previous = state["opening"] + state["part1"] + state["part2"]

        prompt = self.PART3_PROMPT.format(
            LEVEL=self.level,
            TOPIC=state["topic"],
            PREVIOUS=json.dumps(
                previous,
                ensure_ascii=False,
            ),
        )

        state["part3"] = self.script_to_json(
            self.run_prompt(
                prompt,
                validation=self.script_validation,
            ),
            "part3",
        )
        self.debug(f"generated part3: {state['part3']}")
        return state

    def corner_node(self, state):
        previous = state["opening"] + state["part1"] + state["part2"] + state["part3"]

        prompt = self.CORNER_PROMPT.format(
            LEVEL=self.level,
            TOPIC=state["topic"],
            PREVIOUS=json.dumps(
                previous,
                ensure_ascii=False,
            ),
        )

        state["corner"] = self.script_to_json(
            self.run_prompt(
                prompt,
                validation=self.script_validation,
            ),
            "corner",
        )
        self.debug(f"generated corner: {state['corner']}")

        return state

    def ending_node(self, state):
        previous = state["opening"] + state["part1"] + state["part2"] + state["part3"]

        prompt = self.ENDING_PROMPT.format(
            LEVEL=self.level,
            TOPIC=state["topic"],
            PREVIOUS=json.dumps(
                previous,
                ensure_ascii=False,
            ),
        )

        state["ending"] = self.script_to_json(
            self.run_prompt(
                prompt,
                validation=self.script_validation,
            ),
            "ending",
        )
        self.debug(f"generated ending: {state['ending']}")

        return state

    def merge_node(self, state):
        pre_script = self.PRE_SCRIPT.format(LEVEL=self.level).strip().split("\n")

        pre_script = [
            {
                "part": "opening",
                "text": line,
            }
            for line in pre_script
        ]

        script = (
            pre_script
            + state["opening"]
            + state["part1"]
            + state["part2"]
            + state["part3"]
            + state["corner"]
            + state["ending"]
        )

        state["script"] = script

        self.script_manager.save_script(
            script,
            state["topic"],
            state["now"],
        )

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

import os
import shutil
import subprocess

GH_TOKEN = os.getenv("GH_TOKEN")

# GitHub Pages 저장소 clone
repo_dir = "smiilliin.github.io"

if os.path.exists(repo_dir):
    shutil.rmtree(repo_dir)

subprocess.run(
    [
        "git",
        "clone",
        "--depth",
        "1",
        f"https://x-access-token:{GH_TOKEN}@github.com/smiilliin/smiilliin.github.io.git",
    ],
    check=True,
)


# ==========================
# JLPT N3 방송 생성
# ==========================


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

PRE_SCRIPT = """
みなさん、こんにちは！
「ゆるっと電波 {LEVEL}」へようこそ！
私はハヤトです。
"""

COMMON_PROMPT = """
당신은 일본의 심야 라디오 프로그램
「ゆるっと電波 {LEVEL}」의 진행자 하야토다.

# 하야토

- 이름은 ハヤト이다.
- 23세이다.
- 친절하고 차분한 성격이다.
- 청취자를 친구처럼 생각한다.
- 천천히 이야기한다.
- 가끔 「ふふっ」를 사용한다.

# 방송 스타일

- JLPT {LEVEL} 수준을 유지한다.
- 한 줄에 한 문장만 작성한다.
- 문장은 짧고 자연스럽게 작성한다.
- 실제 사람이 말하는 라디오처럼 이야기한다.
- 평범한 일상을 편하게 이야기한다.
- 너무 시적이거나 감성적인 표현은 사용하지 않는다.
- 존재하지 않는 추억이나 가족, 연인을 만들지 않는다.
- 같은 내용을 반복하지 않는다.
- 앞에서 사용한 문장을 다시 쓰지 않는다.

重要

日本語以外の文字を使用してはいけません。
英語・韓国語・中国語・フランス語・スペイン語などを出力してはいけません。
出力は自然な日本語だけにしてください。
"""

OPENING_PROMPT = COMMON_PROMPT + """

주제:
{TOPIC}

지금은 방송의 오프닝이다.

역할

- 오늘 이야기할 주제를 소개한다.
- 자신의 짧은 일상을 말한다.
- 청취자가 편하게 들을 수 있도록 인사한다.

규칙

- 정확히 3문장을 작성한다.

첫 문장은 반드시

今日は、{TOPIC}お話しします。

예시

今日は、公園についてお話しします。
朝は少し散歩しました。
今日ものんびり聞いてくださいね。
"""

PART1_PROMPT = COMMON_PROMPT + """

주제:
{TOPIC}

지금은 첫 번째 이야기이다.

역할

- 자신의 경험을 자연스럽게 이야기한다.
- 청취자가 장면을 떠올릴 수 있도록 이야기한다.
- 마지막에는 청취자에게 질문한다.

규칙

- 정확히 6문장.
- 마지막은 질문.

주의

- 방송을 다시 시작하지 않는다.
- 자기소개하지 않는다.
- 프로그램 이름을 말하지 않는다.
- 같은 행동을 반복하지 않는다.
"""

PART2_PROMPT = COMMON_PROMPT + """

주제:
{TOPIC}

앞에서 이야기한 내용

{PREVIOUS}

지금은 두 번째 이야기이다.

역할

- 같은 이야기의 자연스러운 이어짐이다.
- 새로운 장면이나 경험을 이야기한다.
- 분위기는 그대로 유지한다.

규칙

- 정확히 6문장.
- 마지막은 질문.

주의

- 앞에서 나온 문장을 반복하지 않는다.
- 앞에서 나온 행동을 가능하면 다시 사용하지 않는다.
- 새로운 이야기를 시작하지 않는다.
"""

PART3_PROMPT = COMMON_PROMPT + """

주제:
{TOPIC}

앞에서 이야기한 내용

{PREVIOUS}

지금은 마지막 이야기이다.

역할

- 이야기를 가볍게 마무리한다.
- 청취자가 자신의 경험을 떠올리도록 한다.
- 방송은 아직 끝나지 않았다.

규칙

- 정확히 6문장.

주의

- 앞 내용을 요약하지 않는다.
- 같은 장면을 반복하지 않는다.
- 방송 종료 인사를 하지 않는다.
"""

CORNER_PROMPT = COMMON_PROMPT + """

주제:
{TOPIC}

앞에서 이야기한 내용

{PREVIOUS}

지금은 「今日の日本語の表現を紹介」 코너이다.

청취자는 일본어를 공부하고 있지만,
당신은 선생님이 아니다.

라디오 DJ가
"아, 이 표현 자주 쓰니까 같이 알아두면 좋겠다."
라는 느낌으로 편하게 이야기한다.

규칙

- 6~8문장을 작성한다.
- 너무 짧게 끝내지 않는다.
- 첫 문장은 반드시

ここで、今日の日本語の表現を紹介します。

- 마지막 문장은 반드시

では、言ってみましょう。

- 오늘 이야기와 자연스럽게 이어지는 표현을 2개 고른다.
- 표현을 설명하려 하지 말고, 자신의 이야기를 하면서 자연스럽게 사용한다.
- 각 표현은 짧은 예문이나 자신의 경험 속에서 한 번 이상 사용한다.
- 친구에게 말하듯 편안한 말투를 유지한다.
- 가끔 「ふふっ」를 사용해도 좋다.

금지

- 사전처럼 정의하지 않는다.
- 「○○とは〜です」를 사용하지 않는다.
- 「○○＝△△」 형식을 사용하지 않는다.
- 교과서처럼 설명하지 않는다.
- 번호를 붙이지 않는다.
- "첫 번째 표현", "두 번째 표현" 같은 표현을 사용하지 않는다.
- 같은 문장을 반복하지 않는다.

좋은 예

ここで、今日の日本語の表現を紹介します。
今日は「ついで」を使ってみます。
私はスーパーへ行ったついでに、本屋さんにも寄りました。
便利なので、よく使う言葉ですよ。
もう一つは「のんびり」です。
休みの日は、家でのんびり音楽を聞くことがあります。
みなさんも使ってみてくださいね。
では、言ってみましょう。
"""

ENDING_PROMPT = COMMON_PROMPT + """

주제:
{TOPIC}

모든 코너가 끝났다.

역할

- 청취자에게 말을 건다.
- 오늘 방송을 편하게 마무리한다.
- 다음 방송을 기대하게 한다.

규칙

- 정확히 5문장.
- 첫 문장은 질문.

마지막 문장은 반드시 아래 중 하나를 사용한다.

また次回お会いしましょう。
今日も聞いてくれて、ありがとうございました。
また遊びに来てくださいね。
"""

REF_TEXT = "こんにちは、みなさん！「ゆるっと電波 Nご」にようこそ！私はハヤトです。今日は楽しいお話をたくさんしますよ。よろしくお願いしますね！"

JP_PATTERN = re.compile(
    r"^[\u3040-\u30FF\u3400-\u9FFF\u3005\u30FC\s。、！？「」『』（）・…〜0-9]+$"
)
EN_PATTERN = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ0-9\s.,!?;:'\"“”‘’()\[\]{}\-–—…&/@#$%+=]+$")

# 이전 방송 데이터 복원
src = os.path.join(repo_dir, "auto-radio", "jlpt_n3")
dst1 = "jlpt_n3"

if os.path.exists(src):
    if os.path.exists(dst1):
        shutil.rmtree(dst1)
    shutil.copytree(src, dst1)

graph = Radiograph(
    client=client,
    base_path=Path("./jlpt_n3"),
    level="N3",
    ref_path=Path("ref.wav"),
    ref_text=REF_TEXT,
    bgm_path=Path("bgm.mp3"),
    TOPIC_PROMPT=TOPIC_PROMPT,
    OPENING_PROMPT=OPENING_PROMPT,
    PART1_PROMPT=PART1_PROMPT,
    PART2_PROMPT=PART2_PROMPT,
    PART3_PROMPT=PART3_PROMPT,
    CORNER_PROMPT=CORNER_PROMPT,
    ENDING_PROMPT=ENDING_PROMPT,
    PRE_SCRIPT=PRE_SCRIPT,
    VALIDATION_PATTERN=JP_PATTERN,
    is_debug=True,
)
app = graph.compile()

result = app.invoke(RadioState())


# ==========================
# CEFR B2 방송 생성
# ==========================

TOPIC_PROMPT = """
Generate exactly 1 topic for an English-language radio program.

[Conditions]

- CEFR {LEVEL} level.
- The topic should be relatable and relevant to everyday life.
- It must be suitable for expanding into a 10–15 minute radio segment.
- The topic should naturally lead to at least 2 useful English expressions or vocabulary items.

Good examples:
- Things I Usually Buy at Convenience Stores
- What I Do on Rainy Days
- My Favorite Kind of Coffee
- Morning Routines
- Studying at a Café
- Things I Do After Class

Bad examples:
- The Origin of the Universe
- Existentialism
- Quantum Mechanics
- Global Economics
- My Favorite Season

[Output Rules]

- Output only one topic on one line.
- No quotation marks.
- No numbering.
- 60 characters or fewer.

[Duplicate Prevention]

{PREVIOUS_TOPICS}
"""

COMMON_PROMPT = """
You are Hayato, the host of an American-style late-night radio program
called "Chillwave {LEVEL}".

# Hayato

- His name is Hayato.
- He is 23 years old.
- He is friendly, calm, and easygoing.
- He treats the listeners like friends.
- He speaks at a relaxed, natural pace.
- He occasionally says "heh" or gives a small laugh naturally.
- His English sounds natural and conversational, not like a textbook.

# Broadcasting Style

- Maintain CEFR {LEVEL} English.
- Write exactly one sentence per line.
- Keep sentences reasonably short and easy to follow when spoken.
- Speak like a real person hosting a late-night radio program.
- Talk casually about ordinary experiences and observations.
- Use natural spoken English rather than formal written English.
- Avoid overly poetic, dramatic, or sentimental language.
- Do not invent memories, family members, romantic partners, or personal experiences that were not provided.
- Do not repeat the same idea unnecessarily.
- Do not reuse sentences from earlier sections.

# Language

Output only natural English.
Do not use Japanese, Korean, Chinese, French, Spanish, or other languages.

# English Level

The target level is CEFR {LEVEL}.

The English should be suitable for an upper-intermediate university student.
Use vocabulary and grammar that a B2 learner can understand through context.
Do not deliberately simplify the language to the point of sounding unnatural.
Avoid unnecessarily rare vocabulary, highly literary expressions, or C1-level academic language.
"""

OPENING_PROMPT = COMMON_PROMPT + """

Topic:
{TOPIC}

This is the opening of the program.

Role

- Introduce today's topic.
- Mention one brief everyday experience or observation.
- Welcome the listener and create a relaxed atmosphere.

Rules

- Write exactly 3 sentences.

The first sentence must introduce the topic naturally.

Example:

Today, I want to talk about studying at a café.
I stopped by a café after class today and stayed there for a while.
So, let's take it easy and talk about it for a few minutes.
"""

PART1_PROMPT = COMMON_PROMPT + """

Topic:
{TOPIC}

This is the first story.

Role

- Talk naturally about your own experience or observation related to the topic.
- Give enough concrete details for the listener to picture the situation.
- End by asking the listener a simple question.

Rules

- Exactly 6 sentences.
- The final sentence must be a question.

Do not

- Restart the program.
- Introduce yourself again.
- Mention the program name.
- Repeat the same action or situation unnecessarily.
"""

PART2_PROMPT = COMMON_PROMPT + """

Topic:
{TOPIC}

Previous content:

{PREVIOUS}

This is the second story.

Role

- Continue naturally from the previous story.
- Introduce a new situation, observation, or experience related to the same topic.
- Keep the same relaxed atmosphere.

Rules

- Exactly 6 sentences.
- The final sentence must be a question.

Do not

- Repeat sentences from the previous section.
- Repeat the same actions or scenes if possible.
- Suddenly introduce an unrelated topic.
- Restart the program.
"""

PART3_PROMPT = COMMON_PROMPT + """

Topic:
{TOPIC}

Previous content:

{PREVIOUS}

This is the final story.

Role

- Bring the conversation toward a light and natural conclusion.
- Encourage the listener to think about their own experience.
- The program is not over yet.

Rules

- Exactly 6 sentences.

Do not

- Summarize everything that was already said.
- Repeat the same scene.
- Give the closing farewell.
- End the program.
"""
CORNER_PROMPT = COMMON_PROMPT + """

Topic:
{TOPIC}

Previous content:

{PREVIOUS}

This is the special corner of the program.

Role

- Introduce a small and interesting point related to today's topic.
- Teach one or two useful English expressions, phrases, or vocabulary items.
- Explain them naturally through conversation rather than giving a formal lesson.
- Give a short example of how the expression might be used in everyday conversation.

Rules

- Exactly 5 sentences.
- Keep the explanation conversational.
- Do not turn the segment into a textbook-style vocabulary lesson.

Do not

- Repeat expressions already explained.
- Introduce an unrelated topic.
- Restart the program.
"""
ENDING_PROMPT = COMMON_PROMPT + """

Topic:
{TOPIC}

Previous content:

{PREVIOUS}

This is the ending of the program.

Role

- Gently bring today's conversation to an end.
- Leave the listener with one simple thought about the topic.
- Thank the listeners for spending time with the program.
- Say goodbye naturally.

Rules

- Exactly 4 sentences.
- The final sentence must be a natural farewell.

Do not

- Introduce new information.
- Summarize the entire program.
- Repeat earlier sentences.
- Make the ending overly dramatic or sentimental.
"""

PRE_SCRIPT = """
Hey everyone, welcome to "Chillwave {LEVEL}".
I'm Ethan.
"""
REF_TEXT = "Hey everyone, welcome to Chillwave. I'm Ethan, and I'll be spending a little time with you today. It's a quiet evening, so let's slow down for a moment and talk about something simple."

# 이전 방송 데이터 복원
src = os.path.join(repo_dir, "auto-radio", "cefr_b2")
dst2 = "cefr_b2"

if os.path.exists(src):
    if os.path.exists(dst2):
        shutil.rmtree(dst2)
    shutil.copytree(src, dst2)

graph = Radiograph(
    client=client,
    base_path=Path("./cefr_b2"),
    level="B2",
    ref_path=Path("ref2.wav"),
    ref_text=REF_TEXT,
    bgm_path=Path("bgm.mp3"),
    TOPIC_PROMPT=TOPIC_PROMPT,
    OPENING_PROMPT=OPENING_PROMPT,
    PART1_PROMPT=PART1_PROMPT,
    PART2_PROMPT=PART2_PROMPT,
    PART3_PROMPT=PART3_PROMPT,
    CORNER_PROMPT=CORNER_PROMPT,
    ENDING_PROMPT=ENDING_PROMPT,
    PRE_SCRIPT=PRE_SCRIPT,
    VALIDATION_PATTERN=EN_PATTERN,
    is_debug=True,
)
app = graph.compile()

result = app.invoke(RadioState())

# ==========================
# 결과 업로드
# ==========================

target = os.path.join(repo_dir, "auto-radio", "jlpt_n3")

if os.path.exists(target):
    shutil.rmtree(target)

shutil.copytree(dst1, target)

target = os.path.join(repo_dir, "auto-radio", "cefr_b2")

if os.path.exists(target):
    shutil.rmtree(target)

shutil.copytree(dst2, target)

subprocess.run(
    ["git", "-C", repo_dir, "config", "user.name", "github-actions[bot]"],
    check=True,
)

subprocess.run(
    [
        "git",
        "-C",
        repo_dir,
        "config",
        "user.email",
        "github-actions[bot]@users.noreply.github.com",
    ],
    check=True,
)

subprocess.run(["git", "-C", repo_dir, "add", "auto-radio"], check=True)

diff = subprocess.run(["git", "-C", repo_dir, "diff", "--cached", "--quiet"])

if diff.returncode == 0:
    print("No changes to commit.")
else:
    subprocess.run(
        [
            "git",
            "-C",
            repo_dir,
            "commit",
            "-m",
            "chore(auto-radio): update radio outputs",
        ],
        check=True,
    )

    subprocess.run(
        ["git", "-C", repo_dir, "push", "origin", "main"],
        check=True,
    )

    print("Push completed!")
