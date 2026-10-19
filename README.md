# ことばで頼める 本の配達ロボット

Physical AI講座の最終課題として制作したシミュレーション作品。
受講者が2026年10月19日に保存した動作版を基に、提出用コードを整理した。

## 何をする作品か

「ソファで読みたいから、本を持ってきて」と依頼すると、AIが配達先を選ぶ。
人が開始を確認した後、食卓での本の受け取り、配達先への移動、受け渡し、ホームへの帰還を順番に実行する。

```text
日本語の依頼 → AIがsofaまたはbedを選択 → 人が開始を確認
  → 食卓へ移動 → 積み込み確認 → 青い本を表示
  → 配達先へ移動 → 受け取り確認 → 本を消去 → ホームへ帰還
```

AIは言葉から配達先を選び、Pythonが仕事の順番と条件を管理する。
ROS 2とGazeboをブリッジでつなぎ、位置情報を受け取りながら速度を指令する。
AIが車輪速度や自由なコードを生成して実行する構成ではない。

積み込み・受け取りは人の入力で模擬する。センサーで本を検知したり、アームでつかんだりする機能はない。
本はロボットに追従する表示マーカーで、荷物の重量や接触物理は再現していない。
障害物回避は未実装。障害物のない空間で使う。

## ファイルと実行時の配置

既存コードはUbuntu内の次の配置を前提とする。
Windowsのフォルダから直接実行するものではない。

| 保存したファイル | 役割 | Ubuntu内の配置先 |
|---|---|---|
| interpret_delivery.py | AI分類・人の開始確認 | ~/pai_beginner_ws/interpret_delivery.py |
| deliver_book.py | 受け取り・配達・帰還の順序 | ~/pai_beginner_ws/deliver_book.py |
| book_visual.py | 本の表示・消去 | ~/pai_beginner_ws/book_visual.py |
| home_destinations.json | 4地点の座標 | ~/pai_beginner_ws/home_destinations.json |
| home_robot.py | 名前を座標へ変換 | ~/pai_beginner_ws/src/pai_control/pai_control/home_robot.py |
| go_to_point.py | 旋回・前進・到着判定 | ~/pai_beginner_ws/src/pai_control/pai_control/go_to_point.py |
| show_home_markers.py | 地点の円と英字ラベル | ~/pai_beginner_ws/src/pai_control/pai_control/show_home_markers.py |
| pai_step1_edit.sdf | 仮想空間とロボット | ~/pai_step1_edit.sdf |

`~`はUbuntuユーザーのホーム、現在は`/home/ubuntu`。
復元する場合は、現行の編集内容を別に保存してから、上記の配置へ戻す。
Docker経由で配置すると所有者がrootになる場合があるため、編集前に`ls -l`で所有者を確認する。

講座環境へ新しく配置する例（Ubuntuの一般ユーザーで、取得したリポジトリのフォルダ内から実行）：

```bash
mkdir -p ~/pai_beginner_ws/src/pai_control/pai_control
cp -n interpret_delivery.py deliver_book.py book_visual.py home_destinations.json ~/pai_beginner_ws/
cp -n home_robot.py go_to_point.py show_home_markers.py ~/pai_beginner_ws/src/pai_control/pai_control/
cp -n pai_step1_edit.sdf ~/
```

`cp -n`は既存ファイルを上書きしない。既存版がある場合は、どちらを使うか確認してから配置する。

## 前提環境

既存の講座用Dockerコンテナ`pai_ros2`、ROS 2 Humble、Gazebo Fortressを使用する。
Gemini用のPythonは`~/pai_gemini_venv/bin/python`。
`google-genai`と`pydantic`が必要で、ROS 2のノードはシステムの`/usr/bin/python3`で動かす。
この版の指定モデルは`gemini-3.5-flash-lite`。利用可否・利用枠は利用時に確認する。
このREADMEは構築済み環境の起動手順であり、新しいPCへの環境構築一式は含めない。
Docker Desktopが手動で一時停止中の場合は、利用者が再開してから起動手順を行う。

Gemini用の仮想環境を新たに作る必要がある場合は、講座Ubuntu環境の`python3-venv`を準備した上で、
リポジトリのフォルダ内から以下を使う。依存版は固定していないため、導入先で動作を確認する。

```bash
python3 -m venv ~/pai_gemini_venv
~/pai_gemini_venv/bin/python -m pip install -r requirements.txt
```

## 起動手順

### 1. WindowsのPowerShell

```powershell
docker ps -a
```

`ps -a`は停止中も含めた一覧表示。`pai_ros2`が停止中の場合だけ、次で起動する。

```powershell
docker start pai_ros2
```

ブラウザで`http://localhost:6080/`を開き、UbuntuのTerminatorを起動する。
以降のコマンドは、明記した場合以外はUbuntu用。

### 2. 端末A：Gazebo

```bash
ign gazebo -r ~/pai_step1_edit.sdf
```

`-r`は再生状態で開始する指定。起動済みなら重ねて実行しない。
この端末はGazeboの処理中のまま残す。

### 3. 端末B：ブリッジ

```bash
source /opt/ros/humble/setup.bash
ros2 run ros_gz_bridge parameter_bridge '/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist' '/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry'
```

`source`はこの端末にROS 2の設定を読み込む。
`/cmd_vel`はROS 2からGazeboへの速度指令、`/odom`はGazeboからROS 2への推定位置・向き・速度。
この端末も処理中のまま残す。起動済みなら重ねて実行しない。

### 4. 端末C：操作と確認

```bash
source /opt/ros/humble/setup.bash
python3 ~/pai_beginner_ws/src/pai_control/pai_control/home_robot.py list
```

`list`は設定を表示するだけで移動しない。この版の座標は以下。

| 名前 | x（m） | y（m） |
|---|---:|---:|
| home | 0.0 | 0.0 |
| table | 2.4 | 0.0 |
| sofa | 0.0 | 2.4 |
| bed | 0.0 | -2.4 |

Gazeboを再起動した場合は、移動前に座標の基準も確認する。

```bash
ros2 topic echo /odom --once --field pose.pose.position
```

起動直後の想定はx・yがほぼ0。既に移動済みなら現在位置が表示される。
情報が出ない場合はGazeboの再生とブリッジを確認し、移動を始めない。

ロボットが停止中、かつGazeboが再生状態で目印を表示する。

```bash
python3 ~/pai_beginner_ws/src/pai_control/pai_control/show_home_markers.py
```

HOMEは青、TABLEは黄、SOFAは緑、BEDは紫。
表示の対応付けには左右輪の中点を使うため、本体中心が円の中心に一致する仕様ではない。

### 5. 同じ端末C：APIキーと配達開始

```bash
read -r -s -p "Gemini APIキーを貼り付けてEnter: " GEMINI_API_KEY
export GEMINI_API_KEY
printf '\n'
```

`read -r -s`はキーを画面に表示せず入力し、`export`で子のPythonへ渡す。
キーをコードへ記載しない。別の端末や再起動後には、この環境変数がない場合がある。

```bash
~/pai_gemini_venv/bin/python ~/pai_beginner_ws/interpret_delivery.py
```

入力例：`ソファで読みたいから、本を持ってきて`。
AIの分類が`sofa`であることを確認して開始に`y`を入力する。
積み込み確認で`y`を入力すると本を表示して配達を開始する。
受け取り確認で`y`を入力すると本を消してホームへ戻る。
ベッド宛ての入力例：`ベッドで読みたいから、本を持ってきて`。

## 確認すべき結果

- 食卓に到着してから積み込み確認が出る。
- 積み込み確認前は配達先へ出発しない。
- 青い本が移動中もロボットに追従する。
- 配達先に到着してから受け取り確認が出る。
- 受け取り後に本が消え、ホームへ戻る。
- 最後に`COMPLETED`が表示される。

AIを使わずに順序だけ試す場合は、端末Cで以下を使う。

```bash
python3 ~/pai_beginner_ws/deliver_book.py sofa
```

`sofa`を`bed`へ変更すると配達先が変わる。
終了コードだけで完了と判断せず、最後の状態と到着・停止のログを確認する。
現在の配達プログラムは取り消しや移動失敗の一部でも通常の`return`で終了する。

## 制限と中断

- 各移動の目標が現在位置から5mを超えると実行しない。この配置の最遠区間は4.8m。
- 到着判定は残り5cm以内で停止へ切替後、推定距離7cm以内と速度を確認する。
- 移動中の位置情報が1秒途絶える、または90秒以内に到着しない場合は停止指令を送る。
- これらは/odomによる確認で、実世界の位置精度や停止保証ではない。
- 操作用端末のCtrl+Cで中断する。停止とログを確認し、自動再開はしない。
- 積載後の取り消し・中断・移動失敗では本の表示が残る場合がある。人が状態を確認する。
- `home_robot.py register`は初期学習時の3地点用処理が残っているため、この4地点版では使わない。同梱のJSONを配置して使う。
- `state`は現在の段階を表示・記録する変数。再起動後の復帰や永続化は実装していない。

本の表示を手動で消す場合：

```bash
python3 ~/pai_beginner_ws/book_visual.py hide
```

一時停止中は位置更新が止まる。Gazeboのスペースキーはシミュレーション全体の一時停止に使われるため、ロボットの停止指令と混同しない。

## 確認範囲と個人情報

学習中に、受講者が分類・移動・配達・表示を段階的に試した。
リポジトリへ整理した際はソースの文法・JSON/SDFの形式を検査し、コード8ファイルが保存版と同じであることをハッシュで照合する。
Gitへ登録する際の改行はLFに統一する。コードの処理や設定値は変更していない。
学習時のコードにある行末空白等は、動作を変更しない保存版として残している。
新しい環境へ再配置した試験と、整理後の走行試験は未実施。

APIキーは`GEMINI_API_KEY`から取得する。キーをファイルやGit履歴に保存しない。
`.env`、認証ファイル、仮想環境、実行ログ、動画・画像は公開対象から除く設定を同梱した。
この設定だけで機密情報の流出を防げるわけではないため、追加するファイルはその都度確認する。
公開対象の検査結果は[PRIVACY_REVIEW.md](PRIVACY_REVIEW.md)に記載する。
動画・PDFレポートの公開と講座への最終提出は別途行う。

## 出典と制作過程

- 基礎教材：N622「gazeboとROS2を連携してロボットを操作する」
  https://qiita.com/N622/items/9d89f77d85d9da0af29e
- ロボットの元：Gazebo Fortress付属の`diff_drive.sdf`。
- Codexの支援を受け、受講者が座標・行き先・AIの分類候補・配達の順序・本の表示を編集して試した。
- 工夫：日本語による配達先選択、開始・積載・受取の人による確認、配達後の帰還、積載中の可視化。
- 未実装：実物の把持、積載センサー、障害物回避、移動中の自然言語による割り込み。

派生元のライセンス・変更内容は[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)を参照。
