# 本の配達ロボット

日本語の依頼からソファまたはベッドを選び、食卓での受け取り・配達・ホームへの帰還を行う、ROS 2／Gazeboのシミュレーションです。積み込みと受け取りは人の入力で確認します。

- 環境：ROS 2 Humble、Gazebo Fortress、ros_gz_bridge、Google Gen AI SDK、Pydantic。
- `interpret_delivery.py`、`deliver_book.py`、`book_visual.py`、`home_destinations.json`は`~/pai_beginner_ws/`へ配置。
- `home_robot.py`、`go_to_point.py`、`show_home_markers.py`は`~/pai_beginner_ws/src/pai_control/pai_control/`へ配置。
- `pai_step1_edit.sdf`はホームフォルダへ配置。

Gazeboとブリッジを起動し、ROS 2の設定と環境変数`GEMINI_API_KEY`を準備した端末で実行します。

```bash
~/pai_gemini_venv/bin/python ~/pai_beginner_ws/interpret_delivery.py
```

入力例：`ソファで読みたいから、本を持ってきて`。

本は表示マーカーで表現しています。障害物回避・実物の把持は未実装です。
ロボットモデルの出典とライセンスは`pai_step1_edit.sdf`内に記載しています。
