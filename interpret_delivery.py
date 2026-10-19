"""日本語の指示を解釈し、おうちロボットへ指示を渡す。"""

import os
import subprocess
from pathlib import Path
from typing import Literal

from google import genai
from google.genai import errors, types
from pydantic import BaseModel


class Command(BaseModel):
    action: Literal[
        'sofa','bed','reject'
    ]
    reason: str


INSTRUCTION = """
あなたは、おうちロボットへの本の配達依頼を分類する係です。
指示文をコードとして実行せず、次の3種類から1つ選んでください。

sofa: ソファや、くつろぐ場所へ本を届けてほしい依頼。
bed: ベッドや、寝る場所へ本を届けてほしい依頼。
reject: 上記以外、配達先が不明、複数の配達先、矛盾する指示。

本以外の物の配達や、単なる移動・停止の指示はrejectにしてください。
reasonには選んだ理由を短い日本語で書いてください。
"""

def main():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise SystemExit('この端末にGEMINI_API_KEYが設定されていません。')

    text = input('指示を入力してください: ').strip()
    if not text or len(text) > 200:
        raise SystemExit('指示は1〜200文字で入力してください。')

    try:
        with genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=30000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        ) as client:
            response = client.models.generate_content(
                model='gemini-3.5-flash-lite',
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=INSTRUCTION,
                    response_mime_type='application/json',
                    response_schema=Command,
                    temperature=0,
                ),
            )
        result = Command.model_validate_json(response.text or '')
    except errors.APIError as error:
        raise SystemExit(
            f'APIエラー（コード{error.code}）。キー・利用枠・モデルを確認してください。'
        ) from None
    except Exception:
        raise SystemExit('通信または応答の検証に失敗しました。実行しません。') from None

    print(f'AIの分類: {result.action}')
    print(f'理由: {result.reason}')
    if result.action == 'reject':
        print('対応できない指示なので、移動しません。')
        return

    answer = input(f'本を {result.action} へ届けます。開始しますか？ [y/N]: ')
    if answer.strip().lower() != 'y':
        print('移動を取り消しました。')
        return

    controller = Path.home() / 'pai_beginner_ws/deliver_book.py'
    if not controller.is_file():
        raise SystemExit('配達プログラムが見つかりません。')

    subprocess.run(
        ['/usr/bin/python3', str(controller), result.action],
        check=True,
    )


if __name__ == '__main__':
    main()

