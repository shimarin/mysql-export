# mysql-export
MySQL/MariaDBの全データベースと全ユーザーを一括でエクスポートするツール

## このプログラムの紹介

MySQL/MariaDBのデータベースとユーザーを指定のディレクトリにエクスポートするツールです。mysqldumpと違うのは、バージョンの異なるインポート先に対してもユーザー情報まで含めて一括インポートできる構造でデータを出力する点です。

このプログラムを実行すると、データベースはそれぞれ **データベース名**.sql.gz ファイルに、ユーザーはまとめて 00users.sql ファイルにダンプされます。

import.sh というインポート用のスクリプトも同時に生成されます。このスクリプトでは、00users.sqlを実行してまずはユーザーを作成し、その後に各データベースをリストアしています。

## 動作条件

- Python 3.5くらい以上
- [mysqlclient](https://github.com/PyMySQL/mysqlclient/)

## インストール

適当な場所に mysql-export.py をコピーしてください

## 使用方法

必要に応じて下記のオプションを付けて実行してください。

- ```--host HOST``` エクスポートしたいMySQLのホストを指定します。デフォルト=localhost
- ```--user USER```
root権限を持ったMySQLユーザー名を指定します。デフォルト=root
- ```--password PASSWORD``` 上記ユーザーのパスワードを指定します。
- ```--output-dir OUTPUT_DIR``` 出力先ディレクトリを指定します。デフォルト=./mysql-export
- ```--database-exclude DATABASE_EXCLUDE``` エクスポートから除外したいデータベースを指定します。複数回指定可能
- ```--no-content``` データベースの中身をエクスポートしません
- ```--log-level LOG_LEVEL``` ログレベルを指定します。デフォルト=INFO

## 仕様と制約事項

- 本プログラムは ```mysql```,```information_schema```,```performance_schema```,```sys``` および```--database-exclude```オプションで指定したもの以外の全てのデータベースをエクスポート対象とします。
- ユーザーの権限は細かくエクスポートされません。ユーザーはアクセス可能な全てのデータベースに対して ALL PRIVILEGESを GRANTされます。グローバル権限は持ちません。
- userテーブルにpassword列を持っているシステムの場合、passwordカラムの内容がパスワードハッシュとしてエクスポートされます。その際、ハッシュの種別は内容から適当に判断されます。
    - ハッシュ形式は mysql_native_password, caching_sha2_password, mysql_old_password(注意事項あり後述)にだけ対応しています。
- MySQL 8.0以降のようにpasswordカラムのないuserテーブルを持つシステムでは、ユーザーの認証情報をエクスポートするのに plugin列と authentication_string列が使用されます。
- 16進数16桁の古いパスワードハッシュ(mysql_old_password)を使用しているユーザーは MySQL 8.0以降にはインポートできません。インポートしようとしてもエラーになるので、ハッシュ化前のパスワードをなんとか調べて 00users.sqlを適当に直してください。

## 注意事項

これは自分が使うために作成したツールを他の人の参考になるように公開しているものです。個別の環境に合った動作をするかどうかはわかりませんので、十分にバックアップや検証を行ってから実際のデータに対して適用してください。使用した結果については責任を負いかねます。

## ライセンス

MIT License

Copyright (c) 2024 Tomoatsu Shimada

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
