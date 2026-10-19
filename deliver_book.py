"""食卓へ移動し、本の積み込み確認を待つ練習。"""

import subprocess
import argparse
from book_visual import set_book_visible
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', choices=['sofa', 'bed'])
    args = parser.parse_args()
    
    controller = (
        Path.home() / 'pai_beginner_ws/src/pai_control/pai_control/home_robot.py'
    )

    state = 'GO_TO_TABLE'
    print(f'状態：{state}／本を受け取りに食卓へ向かいます', flush=True)

    try:
        subprocess.run(
            ['/usr/bin/python3', str(controller), 'go', 'table'],
            check=True,
        )
    except subprocess.CalledProcessError:
        print('移動が正常に完了しなかったため、処理を終了します。')
        return

    state = 'WAIT_FOR_LOADING'
    print(f'状態：{state}／食卓に到着しました。')
    answer = input('本を載せましたか？ [y/N]: ')

    if answer.strip().lower() != 'y':
        print('積み込みを確認できないため、ここで終了します。')
        return

    state = 'LOADED'
    set_book_visible(True)
    print(f'状態：{state}／積み込みを確認しました。')
    
    state = 'GO_TO_DESTINATION'
    print(f'状態：{state}／本を {args.destination} へ届けます', flush=True)

    try:
        subprocess.run(
            ['/usr/bin/python3', str(controller), 'go', args.destination],
            check=True,
        )
    except subprocess.CalledProcessError:
        print('配達先への移動が正常に完了しなかったため、終了します。')
        return

    state = 'WAIT_FOR_UNLOADING'
    print(f'状態：{state}／配達先に到着しました。')
    answer = input('本を受け取りましたか？ [y/N]: ')

    if answer.strip().lower() != 'y':
        print('受け取りを確認できないため、ここで終了します。')
        return

    state = 'DELIVERED'
    set_book_visible(False)
    print(f'状態：{state}／本の受け渡しが完了しました。')
   
    state = 'RETURN_HOME'
    print(f'状態：{state}／ホームへ戻ります', flush=True)

    try:
        subprocess.run(
            ['/usr/bin/python3', str(controller), 'go', 'home'],
            check=True,
        )
    except subprocess.CalledProcessError:
        print('ホームへの移動が正常に完了しなかったため、終了します。')
        return

    state = 'COMPLETED'
    print(f'状態：{state}／配達を終え、ホームに戻りました。')

if __name__ == '__main__':
    main()
