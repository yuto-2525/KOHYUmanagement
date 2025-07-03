# app.py

from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime
import os 
import hashlib # パスワードのハッシュ化に使う

# 設定とデータベースのインポート
from config import Config
from database import db, Event, Participant, init_db

app = Flask(__name__)
app.config.from_object(Config) 

# データベースの初期化
init_db(app)

# =========================================================
# ログイン関連のヘルパー
# =========================================================

# 簡単な管理者パスワードのハッシュ化
# これを一度だけ実行して、ハッシュ値を取得し、config.pyに設定します
# 例: python -c "import hashlib; print(hashlib.sha256(b'your_admin_password').hexdigest())"
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# ログインチェックデコレータ
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            flash('管理者ページにアクセスするにはログインしてください。', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# =========================================================
# 参加者用サイトのルーティング (変更なし)
# =========================================================

# 参加者用トップページ: 参加できるイベント一覧を表示
@app.route('/')
def participant_index():
    events = Event.query.all()
    return render_template('participant/event_list.html', events=events)

# 参加者用イベント詳細ページ: 参加申請、振り込み報告、イレギュラー相談フォーム
@app.route('/event/<int:event_id>')
def participant_event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    return render_template('participant/event_detail.html', event=event)

# 参加者による参加申請
@app.route('/event/<int:event_id>/apply', methods=['POST'])
def participant_apply(event_id):
    event = Event.query.get_or_404(event_id)
    participant_name = request.form['participant_name'].strip()
    
    if not participant_name:
        flash('名前を入力してください。', 'error')
        return redirect(url_for('participant_event_detail', event_id=event.id))

    existing_participant = Participant.query.filter_by(name=participant_name, event_id=event.id).first()
    if existing_participant:
        flash('この名前は既に登録されています。', 'error')
        return redirect(url_for('participant_event_detail', event_id=event.id))

    new_participant = Participant(name=participant_name, event_id=event.id)
    db.session.add(new_participant)
    db.session.commit()
    flash(f'{participant_name}様、{event.name}への参加申請が完了しました！', 'success')
    return redirect(url_for('participant_event_detail', event_id=event.id))

# 参加者による振り込み報告
@app.route('/event/<int:event_id>/report_payment', methods=['POST'])
def participant_report_payment(event_id):
    event = Event.query.get_or_404(event_id)
    participant_name = request.form['participant_name_for_report'].strip()
    
    if not participant_name:
        flash('報告したい参加者の名前を入力してください。', 'error')
        return redirect(url_for('participant_event_detail', event_id=event.id))

    participant = Participant.query.filter_by(name=participant_name, event_id=event.id).first()

    if participant:
        if not participant.is_paid:
            participant.is_paid = True
            participant.paid_reported_at = datetime.now()
            db.session.commit()
            flash(f'{participant_name}様の振り込み報告を受け付けました！', 'success')
        else:
            flash(f'{participant_name}様は既に振り込み報告済みです。', 'info')
    else:
        flash('お名前が見つかりませんでした。正確な名前を入力してください。', 'error')
        
    return redirect(url_for('participant_event_detail', event_id=event.id))

# 参加者によるイレギュラー相談申請
@app.route('/event/<int:event_id>/irregular_request', methods=['POST'])
def participant_irregular_request(event_id):
    event = Event.query.get_or_404(event_id)
    participant_name = request.form['participant_name_for_irregular'].strip()
    request_content = request.form['request_content'].strip()
    
    if not participant_name or not request_content:
        flash('名前と相談内容の両方を入力してください。', 'error')
        return redirect(url_for('participant_event_detail', event_id=event.id))

    participant = Participant.query.filter_by(name=participant_name, event_id=event.id).first()

    if participant:
        participant.irregular_request = request_content
        participant.is_irregular_resolved = False # 新しい相談なので未解決にする
        db.session.commit()
        flash(f'{participant_name}様のイレギュラー相談を送信しました。管理者が確認します。', 'success')
    else:
        flash('お名前が見つかりませんでした。正確な名前を入力してください。', 'error')
    
    return redirect(url_for('participant_event_detail', event_id=event.id))

# 参加者による自身のステータス確認ページ
@app.route('/event/<int:event_id>/my_status', methods=['GET', 'POST'])
def participant_my_status(event_id):
    event = Event.query.get_or_404(event_id)
    participant_info = None
    
    if request.method == 'POST':
        query_name = request.form['query_name'].strip()
        if not query_name:
            flash('確認したい名前を入力してください。', 'error')
            return render_template('participant/my_status.html', event=event, participant_info=None)

        found_participant = Participant.query.filter_by(name=query_name, event_id=event.id).first()
        
        if found_participant:
            participant_info = found_participant
            flash(f'「{query_name}」様の情報を表示しました。', 'success')
        else:
            flash(f'「{query_name}」様は見つかりませんでした。名前をもう一度確認してください。', 'error')

    return render_template('participant/my_status.html', event=event, participant_info=participant_info)

# =========================================================
# 管理者用サイトのルーティング
# =========================================================

# 管理者ログインページ
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        if hash_password(password) == app.config['ADMIN_PASSWORD_HASH']: # config.pyで定義
            session['logged_in'] = True
            flash('ログインしました。', 'success')
            return redirect(url_for('admin_index'))
        else:
            flash('パスワードが間違っています。', 'error')
    return render_template('admin/login.html')

# 管理者ログアウト
@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    flash('ログアウトしました。', 'info')
    return redirect(url_for('admin_login'))

# 管理者用トップページ: イベント一覧とイベント作成
@app.route('/admin/')
@admin_required # アクセス制限を適用
def admin_index():
    events = Event.query.all()
    return render_template('admin/event_list.html', events=events)

# 管理者による新しいイベント作成
@app.route('/admin/create_event', methods=['POST']) # GETはadmin_indexでフォームを表示
@admin_required # アクセス制限を適用
def admin_create_event():
    event_name = request.form['event_name'].strip()
    event_description = request.form.get('event_description', '').strip()
    
    if not event_name:
        flash('イベント名を入力してください。', 'error')
        return redirect(url_for('admin_index')) 

    new_event = Event(name=event_name, description=event_description)
    db.session.add(new_event)
    db.session.commit()
    flash(f'イベント「{event_name}」を作成しました！', 'success')
    return redirect(url_for('admin_index'))

# 管理者によるイベント編集ページ
@app.route('/admin/edit_event/<int:event_id>', methods=['GET', 'POST'])
@admin_required # アクセス制限を適用
def admin_edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    if request.method == 'POST':
        event.name = request.form['event_name'].strip()
        event.description = request.form.get('event_description', '').strip()
        if not event.name:
            flash('イベント名を入力してください。', 'error')
            return render_template('admin/edit_event.html', event=event)
        db.session.commit()
        flash(f'イベント「{event.name}」を更新しました。', 'success')
        return redirect(url_for('admin_index'))
    return render_template('admin/edit_event.html', event=event)


# 管理者用イベント詳細ページ: 参加者リストと管理機能
@app.route('/admin/event/<int:event_id>')
@admin_required # アクセス制限を適用
def admin_event_detail(event_id):
    event = Event.query.get_or_404(event_id)

    # 参加者リストのソートロジックは変更なし (前回定義した複雑なソート)
    all_participants = Participant.query.filter_by(event_id=event.id).all()

    paid_reported_unconfirmed_and_irregular_unresolved = []
    paid_reported_unconfirmed = []
    irregular_unresolved = []
    not_paid = []
    confirmed = []

    for p in all_participants:
        is_unconfirmed_paid = p.is_paid and not p.is_confirmed
        is_unresolved_irregular = p.irregular_request and not p.is_irregular_resolved

        if is_unconfirmed_paid and is_unresolved_irregular:
            paid_reported_unconfirmed_and_irregular_unresolved.append(p)
        elif is_unconfirmed_paid:
            paid_reported_unconfirmed.append(p)
        elif is_unresolved_irregular:
            irregular_unresolved.append(p)
        elif p.is_confirmed:
            confirmed.append(p)
        else:
            not_paid.append(p)

    paid_reported_unconfirmed_and_irregular_unresolved.sort(key=lambda p: p.paid_reported_at or datetime.min, reverse=True)
    paid_reported_unconfirmed.sort(key=lambda p: p.paid_reported_at or datetime.min, reverse=True)
    irregular_unresolved.sort(key=lambda p: p.name)
    not_paid.sort(key=lambda p: p.name)
    confirmed.sort(key=lambda p: p.name)

    ordered_participant_ids = set()
    ordered_participants = []

    def add_unique_participants(plist):
        nonlocal ordered_participant_ids, ordered_participants
        for p in plist:
            if p.id not in ordered_participant_ids:
                ordered_participants.append(p)
                ordered_participant_ids.add(p.id)

    add_unique_participants(paid_reported_unconfirmed_and_irregular_unresolved)
    add_unique_participants(paid_reported_unconfirmed)
    add_unique_participants(irregular_unresolved)
    add_unique_participants(not_paid)
    add_unique_participants(confirmed)

    return render_template('admin/event_detail.html', event=event, participants=ordered_participants)


# 管理者による振り込み確認の処理
@app.route('/admin/confirm_payment/<int:participant_id>', methods=['POST'])
@admin_required # アクセス制限を適用
def admin_confirm_payment(participant_id):
    participant = Participant.query.get_or_404(participant_id)
    
    is_checked = 'is_confirmed' in request.form
    
    participant.is_confirmed = is_checked
    if participant.is_confirmed:
        participant.is_paid = True
        if participant.paid_reported_at is None:
             participant.paid_reported_at = datetime.now()
        flash(f'✔ {participant.name}様の振り込みを確認済みにしました。', 'success')
    else:
        participant.is_paid = False
        participant.paid_reported_at = None
        flash(f'✖ {participant.name}様の振り込み確認を解除しました。', 'info')
    
    db.session.commit()
    return redirect(url_for('admin_event_detail', event_id=participant.event_id))

# 管理者によるイレギュラー相談解決の処理
@app.route('/admin/resolve_irregular/<int:participant_id>', methods=['POST'])
@admin_required # アクセス制限を適用
def admin_resolve_irregular(participant_id):
    participant = Participant.query.get_or_404(participant_id)
    
    is_checked = 'is_irregular_resolved' in request.form

    participant.is_irregular_resolved = is_checked
    db.session.commit()
    if participant.is_irregular_resolved:
        flash(f'✔ {participant.name}様のイレギュラー相談を解決済みにしました。', 'success')
    else:
        flash(f'✖ {participant.name}様のイレギュラー相談を未解決に戻しました。', 'info')
    return redirect(url_for('admin_event_detail', event_id=participant.event_id))

# 管理者による参加者編集ページ
@app.route('/admin/edit_participant/<int:participant_id>', methods=['GET', 'POST'])
@admin_required # アクセス制限を適用
def admin_edit_participant(participant_id):
    participant = Participant.query.get_or_404(participant_id)
    if request.method == 'POST':
        participant.name = request.form['participant_name'].strip()
        participant.is_paid = 'is_paid' in request.form # 手動で支払済みを設定できる
        participant.is_confirmed = 'is_confirmed' in request.form # 手動で確認済みを設定できる
        participant.irregular_request = request.form['irregular_request'].strip()
        participant.is_irregular_resolved = 'is_irregular_resolved' in request.form

        # is_paid が True で paid_reported_at がない場合、現在時刻を設定
        if participant.is_paid and participant.paid_reported_at is None:
            participant.paid_reported_at = datetime.now()
        # is_paid が False になった場合、paid_reported_at をクリア
        elif not participant.is_paid and participant.paid_reported_at is not None:
            participant.paid_reported_at = None

        db.session.commit()
        flash(f'{participant.name}様の情報を更新しました。', 'success')
        return redirect(url_for('admin_event_detail', event_id=participant.event_id))
    return render_template('admin/edit_participant.html', participant=participant)

# 管理者による参加者削除
@app.route('/admin/delete_participant/<int:participant_id>', methods=['POST'])
@admin_required # アクセス制限を適用
def admin_delete_participant(participant_id):
    participant = Participant.query.get_or_404(participant_id)
    event_id = participant.event_id # 削除前にイベントIDを保存
    db.session.delete(participant)
    db.session.commit()
    flash(f'{participant.name}様の参加情報を削除しました。', 'info')
    return redirect(url_for('admin_event_detail', event_id=event_id))


# 管理者によるイベント削除
@app.route('/admin/delete_event/<int:event_id>', methods=['POST'])
@admin_required # アクセス制限を適用
def admin_delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash(f'イベント「{event.name}」とその全ての参加者を削除しました。', 'success')
    return redirect(url_for('admin_index'))

if __name__ == '__main__':
    app.run(debug=True)