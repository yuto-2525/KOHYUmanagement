# config.py

import os
import hashlib # hashlib をインポート

class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///events.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_super_secret_key_here_please_change'
    
    # 管理者パスワードのハッシュ値 (重要: 実際のパスワードはここに直接書かない！)
    # 上記のコマンドで生成したハッシュ値をここに貼り付けてください
    ADMIN_PASSWORD_HASH = '09fdf816f2fcac78793e6d54fcc732d9c947e01a665f143bc8ee0bf1b6c43f91' # 例: 'password'をハッシュ化したもの