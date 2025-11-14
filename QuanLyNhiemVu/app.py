from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import re

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'
db = SQLAlchemy(app)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ngay_van_ban = db.Column(db.String(20))
    so_ky_hieu = db.Column(db.String(50))
    cq_ban_hanh = db.Column(db.String(200))
    trich_yeu = db.Column(db.String(500))
    han_xu_ly = db.Column(db.Date)
    ghi_chu = db.Column(db.String(500))
    hashtag = db.Column(db.String(200))
    hoan_thanh = db.Column(db.Boolean, default=False)
    ngay_hoan_thanh = db.Column(db.Date)


with app.app_context():
    db.create_all()


def extract_data(text):
    ngay_match = re.search(r'Ngày văn bản:\s*(\d{2}/\d{2}/\d{4})', text, re.I)
    so_match   = re.search(r'Số/Ký hiệu:\s*([^ \n]+)', text, re.I)
    cq_match   = re.search(r'Tác giả:\s*(.+?)\s*Trích yếu:', text, re.I | re.S)
    trich_match= re.search(r'Trích yếu:\s*(.+)', text, re.I | re.S)

    return {
        'ngay_van_ban': ngay_match.group(1) if ngay_match else '',
        'so_ky_hieu'  : so_match.group(1)   if so_match   else '',
        'cq_ban_hanh' : cq_match.group(1).strip() if cq_match else '',
        'trich_yeu'   : trich_match.group(1).strip() if trich_match else ''
    }


@app.route('/', methods=['GET', 'POST'])
def index():
    # Lọc
    search       = request.args.get('search', '')
    from_month   = request.args.get('from_month')
    from_year    = request.args.get('from_year')
    to_month     = request.args.get('to_month')
    to_year      = request.args.get('to_year')
    stat_month   = request.args.get('stat_month')
    stat_year    = request.args.get('stat_year')

    # Xử lý POST
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            text = request.form.get('van_ban')
            han_str = request.form.get('han_xu_ly')
            ghi_chu = request.form.get('ghi_chu')
            hashtag = request.form.get('hashtag')
            try:
                han_xu_ly = datetime.strptime(han_str, '%d/%m/%Y').date() if han_str else None
            except ValueError:
                flash('Hạn xử lý không đúng định dạng dd/mm/yyyy!', 'danger')
                return redirect(url_for('index'))

            extracted = extract_data(text)
            task = Task(
                ngay_van_ban=extracted['ngay_van_ban'],
                so_ky_hieu=extracted['so_ky_hieu'],
                cq_ban_hanh=extracted['cq_ban_hanh'],
                trich_yeu=extracted['trich_yeu'],
                han_xu_ly=han_xu_ly,
                ghi_chu=ghi_chu,
                hashtag=hashtag
            )
            db.session.add(task)
            db.session.commit()
            flash('Nhiệm vụ đã thêm!', 'success')

        elif action == 'edit':
            task_id = int(request.form.get('task_id'))
            task = Task.query.get(task_id)
            if task:
                han_str = request.form.get('han_xu_ly')
                try:
                    task.han_xu_ly = datetime.strptime(han_str, '%d/%m/%Y').date() if han_str else None
                except ValueError:
                    flash('Hạn xử lý không đúng định dạng!', 'danger')
                    return redirect(url_for('index'))
                task.ngay_van_ban = request.form.get('ngay_van_ban')
                task.so_ky_hieu = request.form.get('so_ky_hieu')
                task.cq_ban_hanh = request.form.get('cq_ban_hanh')
                task.trich_yeu = request.form.get('trich_yeu')
                task.ghi_chu = request.form.get('ghi_chu')
                task.hashtag = request.form.get('hashtag')
                db.session.commit()
                flash('Nhiệm vụ đã chỉnh sửa!', 'success')

        elif action in ('complete', 'undo_complete', 'delete'):
            task_id = int(request.form.get('task_id'))
            task = Task.query.get(task_id)
            if task:
                if action == 'complete':
                    task.hoan_thanh = True
                    task.ngay_hoan_thanh = datetime.now().date()
                    flash('Đã hoàn thành!', 'success')
                elif action == 'undo_complete':
                    task.hoan_thanh = False
                    task.ngay_hoan_thanh = None
                    flash('Đã hoàn tác!', 'success')
                elif action == 'delete':
                    db.session.delete(task)
                    flash('Đã xóa!', 'success')
                db.session.commit()
        return redirect(url_for('index'))

    # Lấy dữ liệu
    query = Task.query
    if search:
        query = query.filter(
            db.or_(
                Task.trich_yeu.ilike(f'%{search}%'),
                Task.ghi_chu.ilike(f'%{search}%'),
                Task.hashtag.ilike(f'%{search}%')
            )
        )
    if from_month and from_year:
        start = datetime(int(from_year), int(from_month), 1).date()
        query = query.filter(Task.ngay_van_ban >= start.strftime('%d/%m/%Y'))
    if to_month and to_year:
        end_day = (datetime(int(to_year), int(to_month)+1, 1) - timedelta(days=1)).date()
        query = query.filter(Task.ngay_van_ban <= end_day.strftime('%d/%m/%Y'))

    tasks = query.order_by(Task.id.desc()).all()
    today = datetime(2025, 11, 13).date()

    for t in tasks:
        if t.hoan_thanh:
            t.color = 'success'
            t.status = 'Hoàn thành'
            t.status_icon = 'check-circle-fill'
        elif t.han_xu_ly is None:
            t.color = 'purple'
            t.status = 'Không có hạn'
            t.status_icon = 'question-circle'
        else:
            days = (t.han_xu_ly - today).days
            if days < 0:
                t.color = 'danger'
                t.status = 'Quá hạn'
                t.status_icon = 'exclamation-triangle-fill'
            elif days <= 2:
                t.color = 'warning'
                t.status = f'Sắp hết hạn ({days} ngày)'
                t.status_icon = 'clock-fill'
            else:
                t.color = 'info'
                t.status = f'Còn {days} ngày'
                t.status_icon = 'hourglass-split'

    # Báo cáo
    total_all = Task.query.count()
    completed_all = Task.query.filter_by(hoan_thanh=True).count()
    overdue_all = len([t for t in Task.query.all() if not t.hoan_thanh and t.han_xu_ly and (t.han_xu_ly - today).days < 0])

    stat_q = Task.query
    if stat_month and stat_year:
        stat_q = stat_q.filter(
            db.extract('month', Task.ngay_hoan_thanh) == int(stat_month),
            db.extract('year',  Task.ngay_hoan_thanh) == int(stat_year)
        )
        total_stat = Task.query.filter(
            db.extract('month', db.func.coalesce(Task.ngay_hoan_thanh, Task.han_xu_ly)) == int(stat_month),
            db.extract('year',  db.func.coalesce(Task.ngay_hoan_thanh, Task.han_xu_ly)) == int(stat_year)
        ).count()
    else:
        total_stat = total_all

    completed_stat = stat_q.filter_by(hoan_thanh=True).count()
    overdue_stat = len([t for t in stat_q.all() if not t.hoan_thanh and t.han_xu_ly and (t.han_xu_ly - today).days < 0])

    stats = {
        'total_all'        : total_all,
        'total_completed'  : completed_all,
        'overdue_all'      : overdue_all,
        'total_stat'       : total_stat,
        'completed_stat'   : completed_stat,
        'overdue_stat'     : overdue_stat,
        'stat_month'       : stat_month,
        'stat_year'        : stat_year
    }

    return render_template(
        'index.html',
        tasks=tasks, stats=stats,
        search=search,
        from_month=from_month, from_year=from_year,
        to_month=to_month,     to_year=to_year,
        stat_month=stat_month, stat_year=stat_year
    )


if __name__ == '__main__':
    app.run(debug=True)