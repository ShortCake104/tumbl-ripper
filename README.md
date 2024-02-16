# Tumbl-Ripper
Tumblrダウンローダー

## How to Use
1. ```pip install -r reuquirements.txt```を実行
2. [ここ](https://www.tumblr.com/oauth/apps)でアプリを登録
3. 登録したアプリの詳細画面でconsumer_keyとconsumer_secretを取得
4. [Console](https://api.tumblr.com/console/calls/user/info)で取得したキーを貼り付けて認証しoauth_tokenとoauth_secretを取得する
5. setting.tomlに全てのキーを入力してmain.pyを起動

## Feature
- ダウンロード
  - ユーザーがポスト･リブログした画像を全てダウンロード
- 通知
  - デスクトップ通知
  - Discord Webhookによる通知
    - 自分にメンションさせることが出来ます
- 追跡
  - ユーザーがブログ名やユーザー名を変えてもidから判別
  - 変更されていた場合､フォルダ名が変わります
