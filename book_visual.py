"""ロボット上に本を表す箱を表示・消去する。"""

import argparse
import subprocess


def set_book_visible(visible):
    if visible:
        marker = """
        ns: "pai_book", id: 1, action: ADD_MODIFY, type: BOX,
        parent: "beginner_robot::chassis",
        pose: {
            position: {x: 0, y: 0, z: 0.35},
            orientation: {w: 1}
        },
        scale: {x: 0.6, y: 0.4, z: 0.1},
        material: {
            ambient: {r: 0.1, g: 0.5, b: 1, a: 1},
            diffuse: {r: 0.1, g: 0.5, b: 1, a: 1}
        }
        """
    else:
        marker = 'ns: "pai_book", id: 1, action: DELETE_MARKER'

    result = subprocess.run(
        [
            'ign', 'service', '-s', '/marker_array',
            '--reqtype', 'ignition.msgs.Marker_V',
            '--reptype', 'ignition.msgs.Boolean',
            '--timeout', '3000',
            '--req', f'marker: {{{marker}}}',
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )
    if 'data: true' not in result.stdout:
        raise RuntimeError('本の表示変更をGazeboが受け付けませんでした')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['show', 'hide'])
    args = parser.parse_args()
    set_book_visible(args.action == 'show')
