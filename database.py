# database.py

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()

# --- データベースモデルの定義 ---

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    # Eventが削除されたら、関連するParticipantも削除されるように設定
    participants = db.relationship('Participant', backref='event', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Event {self.name}>'

class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    is_paid = db.Column(db.Boolean, default=False)
    paid_reported_at = db.Column(db.DateTime, nullable=True) # 振り込み報告日時
    is_confirmed = db.Column(db.Boolean, default=False) # 管理者による確認
    irregular_request = db.Column(db.Text, nullable=True) # イレギュラー相談内容
    is_irregular_resolved = db.Column(db.Boolean, default=False) # イレギュラー相談解決済み

    def __repr__(self):
        return f'<Participant {self.name} for Event {self.event_id}>'