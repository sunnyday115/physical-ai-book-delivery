# 出典・第三者コンポーネント

## Gazebo Fortressのロボットモデル

`pai_step1_edit.sdf`は、Gazebo Fortress（gz-simのign-gazebo6系）の
`examples/worlds/diff_drive.sdf`を基にした学習用の派生ファイル。

- 公式リポジトリ：https://github.com/gazebosim/gz-sim
- 元ファイル：https://github.com/gazebosim/gz-sim/blob/ign-gazebo6/examples/worlds/diff_drive.sdf
- ライセンス：Apache License 2.0。原文を[third_party/LICENSE.gz-sim](third_party/LICENSE.gz-sim)に同梱。
- ライセンス確認時のign-gazebo6コミット：`728569bc66e2f64f8c1ac36758a276a10f9ba6e6`。
- このコミットは出典確認用。講座イメージに組み込まれた元ファイルの厳密な版と同一と検証したものではない。
- 元の2台構成から1台へ変更し、モデル名・本体色・速度指令とオドメトリの宛先・配信頻度を変更。キー入力の設定を追加した。

派生元の著作権は、元プロジェクトの各権利者に帰属する。

## 参考教材

- N622「gazeboとROS2を連携してロボットを操作する」
  https://qiita.com/N622/items/9d89f77d85d9da0af29e
- 本作品は操作・通信の学習に参考にしたもの。記事本文・画像・動画は収録していない。

## 実行時に使用するソフトウェア

ROS 2 Humble、Gazebo Fortress、ros_gz_bridge、Google Gen AI SDK、Pydanticを利用する。
これらの本体や講座資料、Dockerイメージはこのリポジトリに再配布していない。
各ソフトウェアの条件はそれぞれの配布元に従う。

## 制作支援

Codexによる提案・コード生成・確認の支援を受け、受講者が編集・実行して制作した。
個人の実名・所属・メールアドレスは制作クレジットに記載していない。
このリポジトリ全体に適用する追加のライセンスは設定していない。
