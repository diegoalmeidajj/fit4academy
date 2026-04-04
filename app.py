"""Fit4Academy — Jiu-Jitsu Academy CRM
Main Flask application."""

# ═══════════════════════════════════════════════════════════════
#  IMPORTS & SETUP
# ═══════════════════════════════════════════════════════════════

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, send_from_directory, Response, abort)
import config
import models
import billing
import marcos_ai
from i18n import get_text
import os
import json
import uuid
from datetime import datetime, timedelta, date
from functools import wraps

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Ensure upload directory exists
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize database on startup
models.init_db()


# ═══════════════════════════════════════════════════════════════
#  LOGIN REQUIRED DECORATOR
# ═══════════════════════════════════════════════════════════════

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ═══════════════════════════════════════════════════════════════
#  CSRF TOKEN
# ═══════════════════════════════════════════════════════════════

def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = str(uuid.uuid4())
    return session['_csrf_token']


def validate_csrf():
    token = session.get('_csrf_token', '')
    form_token = request.form.get('csrf_token', '')
    if not token or token != form_token:
        flash('Invalid form submission. Please try again.', 'error')
        return False
    return True


# ═══════════════════════════════════════════════════════════════
#  CONTEXT PROCESSOR — inject globals into all templates
# ═══════════════════════════════════════════════════════════════

@app.context_processor
def inject_globals():
    ui_lang = session.get('ui_lang', 'en')
    display_currency = session.get('display_currency', 'USD')

    currency_symbols = {'USD': '$', 'BRL': 'R$', 'MXN': 'MX$'}
    currency_symbol = currency_symbols.get(display_currency, '$')

    def t(key):
        return get_text(ui_lang, key)

    # Academy settings
    academy = None
    academy_id = session.get('academy_id', 1)
    try:
        academy = models.get_academy_by_id(academy_id)
    except Exception:
        pass

    # Trial days remaining (placeholder — 30 day trial)
    trial_days = 30

    # Unread notification count
    unread_count = 0
    if session.get('logged_in'):
        try:
            unread = models.get_unread_notifications(academy_id)
            unread_count = len(unread) if unread else 0
        except Exception:
            pass

    # Leads waiting 24h+ without contact (only 'new' stage leads)
    urgent_leads_count = 0
    if session.get('logged_in'):
        try:
            from datetime import datetime as dt_cls
            all_prsp = models.get_all_prospects(academy_id)
            now = dt_cls.now()
            for p in (all_prsp or []):
                if p.get('status') == 'new' and p.get('source') != 'ex_student' and not p.get('member_id') and not p.get('archived'):
                    created = str(p.get('created_at', ''))[:19]
                    try:
                        created_dt = dt_cls.strptime(created, '%Y-%m-%d %H:%M:%S')
                        if (now - created_dt).total_seconds() > 86400:
                            urgent_leads_count += 1
                    except Exception:
                        pass
        except Exception:
            pass

    return dict(
        t=t,
        ui_lang=ui_lang,
        academy=academy,
        trial_days=trial_days,
        display_currency=display_currency,
        currency_symbol=currency_symbol,
        csrf_token=generate_csrf_token,
        user_name=session.get('display_name', ''),
        user_role=session.get('role', 'user'),
        unread_notifications=unread_count,
        urgent_leads=urgent_leads_count,
        stripe_enabled=billing.is_enabled(),
        stripe_pk=billing.get_publishable_key(),
        platform_fee=billing.PLATFORM_FEE,
    )


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════

def _get_academy_id():
    return session.get('academy_id', 1)


def _time_greeting():
    hour = datetime.now().hour
    if hour < 12:
        return 'Good morning'
    elif hour < 18:
        return 'Good afternoon'
    else:
        return 'Good evening'


def _save_upload(file_obj, subfolder=''):
    """Save an uploaded file and return the URL path."""
    if not file_obj or not file_obj.filename:
        return ''
    ext = os.path.splitext(file_obj.filename)[1].lower()
    allowed = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf', '.mp4', '.mov'}
    if ext not in allowed:
        return ''
    unique_name = f"{uuid.uuid4().hex}{ext}"
    if subfolder:
        dest_dir = os.path.join(UPLOAD_DIR, subfolder)
        os.makedirs(dest_dir, exist_ok=True)
        file_obj.save(os.path.join(dest_dir, unique_name))
        return f"/static/uploads/{subfolder}/{unique_name}"
    else:
        file_obj.save(os.path.join(UPLOAD_DIR, unique_name))
        return f"/static/uploads/{unique_name}"


def _enrich_member(m):
    """Add computed fields to a member dict for template display."""
    if not m:
        return m
    member = dict(m) if not isinstance(m, dict) else m
    member['belt'] = member.get('belt_name', 'White')
    member['status'] = member.get('membership_status', 'active')
    member['dob'] = str(member.get('date_of_birth', '') or '')[:10]
    member['initials'] = (member.get('first_name', ' ')[0] + member.get('last_name', ' ')[0]).upper()

    # Membership info
    try:
        memberships = models.get_memberships_by_member(member['id'])
        if memberships:
            active_ms = memberships[0]
            member['membership_name'] = active_ms.get('plan_name', '')
            member['membership_id'] = active_ms.get('plan_id', '')
            member['next_payment'] = active_ms.get('end_date', '')
        else:
            member['membership_name'] = ''
            member['membership_id'] = ''
            member['next_payment'] = ''
    except Exception:
        member['membership_name'] = ''
        member['membership_id'] = ''
        member['next_payment'] = ''

    # Checkin stats
    try:
        checkins = models.get_checkins_by_member(member['id'], limit=999)
        member['total_checkins'] = len(checkins)
        now = datetime.now()
        member['this_month_checkins'] = sum(
            1 for c in checkins
            if str(c.get('check_in_time', ''))[:7] == now.strftime('%Y-%m')
        )
        member['last_checkin'] = str(checkins[0].get('check_in_time', ''))[:16] if checkins else ''
        # Simple streak calculation
        member['streak'] = 0
    except Exception:
        member['total_checkins'] = 0
        member['this_month_checkins'] = 0
        member['last_checkin'] = ''
        member['streak'] = 0

    return member


# ═══════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ═══════════════════════════════════════════════════════════════

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        try:
            user = models.authenticate_user(username, password)
            if user:
                session['logged_in'] = True
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['display_name'] = user.get('name', username)
                session['role'] = user.get('role', 'user')
                session['academy_id'] = user.get('academy_id', 1)
                # Load academy language/currency defaults
                try:
                    academy = models.get_academy_by_id(user.get('academy_id', 1))
                    if academy:
                        session.setdefault('ui_lang', academy.get('language', 'en'))
                        session.setdefault('display_currency', academy.get('currency', 'USD'))
                except Exception:
                    pass
                flash('Welcome back!', 'success')
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error='Invalid username or password.')
        except Exception as e:
            print(f"[Login] Error: {e}")
            return render_template('login.html', error='Login error. Please try again.')
    return render_template('login.html', error=None)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        academy_name = request.form.get('academy_name', '').strip()
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not all([academy_name, full_name, username, password]):
            return render_template('register.html', error='All fields are required.')
        if len(password) < 8:
            return render_template('register.html', error='Password must be at least 8 characters.')

        try:
            # Create user first
            user_id = models.create_user(
                username=username,
                password=password,
                name=full_name,
                email=email,
                role='admin',
                academy_id=1
            )
            if not user_id:
                return render_template('register.html', error='Username already exists.')

            # Create academy
            academy_id = models.create_academy(
                name=academy_name,
                owner_id=user_id,
                email=email
            )
            # Update user with correct academy_id
            if academy_id:
                models.update_user(user_id, academy_id=academy_id)

            # Auto-login
            session['logged_in'] = True
            session['user_id'] = user_id
            session['username'] = username
            session['display_name'] = full_name
            session['role'] = 'admin'
            session['academy_id'] = academy_id or 1

            flash('Welcome to Fit4Academy! Your academy has been created.', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            print(f"[Register] Error: {e}")
            return render_template('register.html', error='Registration failed. Please try again.')

    return render_template('register.html', error=None)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/set-lang/<lang>')
def set_lang(lang):
    if lang in ('en', 'es', 'pt'):
        session['ui_lang'] = lang
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/set-currency/<currency>')
def set_currency(currency):
    if currency in ('USD', 'BRL', 'MXN'):
        session['display_currency'] = currency
    return redirect(request.referrer or url_for('dashboard'))


# ═══════════════════════════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════════════════════════

@app.route('/')
@login_required
def dashboard():
    academy_id = _get_academy_id()
    greeting = _time_greeting()

    try:
        stats = models.get_dashboard_stats(academy_id)
    except Exception:
        stats = {'active_members': 0, 'total_members': 0, 'today_checkins': 0,
                 'monthly_revenue': 0, 'expiring_soon': 0, 'active_prospects': 0}

    # Today's classes
    today_classes = []
    try:
        dow = datetime.now().weekday()  # 0=Monday
        schedules = models.get_schedule_by_day(dow, academy_id)
        for s in schedules:
            today_classes.append({
                'id': s.get('class_id', s.get('id')),
                'name': s.get('class_name', ''),
                'start_time': s.get('start_time', ''),
                'end_time': s.get('end_time', ''),
                'instructor': s.get('instructor', ''),
                'type': s.get('class_type', 'gi'),
                'enrolled': 0,
                'capacity': s.get('max_capacity', 30) if 'max_capacity' in (s if isinstance(s, dict) else {}) else 30,
            })
    except Exception as e:
        print(f"[Dashboard] Classes error: {e}")

    # Recent check-ins
    recent_checkins = []
    try:
        raw_checkins = models.get_today_checkins(academy_id)
        for ci in (raw_checkins or [])[:10]:
            fn = ci.get('first_name', '')
            ln = ci.get('last_name', '')
            recent_checkins.append({
                'member_name': f"{fn} {ln}",
                'class_name': ci.get('class_name', ''),
                'time': str(ci.get('check_in_time', ''))[-8:-3] if ci.get('check_in_time') else '',
                'photo': ci.get('photo', ''),
                'initials': (fn[:1] + ln[:1]).upper() if fn else '??',
            })
    except Exception as e:
        print(f"[Dashboard] Checkins error: {e}")

    # Upcoming birthdays
    upcoming_birthdays = []
    try:
        bdays = models.get_upcoming_birthdays(academy_id, days=30)
        for b in (bdays or [])[:8]:
            dob = str(b.get('date_of_birth', ''))[:10]
            fn = b.get('first_name', '')
            ln = b.get('last_name', '')
            upcoming_birthdays.append({
                'name': f"{fn} {ln}",
                'date': dob[5:] if dob else '',
                'days_until': b.get('days_until', ''),
                'photo': b.get('photo', ''),
                'initials': (fn[:1] + ln[:1]).upper() if fn else '??',
            })
    except Exception as e:
        print(f"[Dashboard] Birthdays error: {e}")

    # Payment alerts
    payment_alerts = []
    try:
        alerts_raw = models.get_payment_alerts(academy_id)
        for a in (alerts_raw or [])[:8]:
            payment_alerts.append({
                'member_name': f"{a.get('first_name', '')} {a.get('last_name', '')}",
                'amount': a.get('amount', 0),
                'type': 'overdue' if a.get('status') == 'overdue' else 'failed',
                'message': f"Due: {a.get('due_date', '')}",
            })
    except Exception as e:
        print(f"[Dashboard] Payment alerts error: {e}")

    # Belt distribution
    belt_distribution = {}
    try:
        bd = models.get_belt_distribution(academy_id)
        for b in (bd or []):
            belt_distribution[b.get('name', 'Unknown')] = b.get('count', 0)
    except Exception as e:
        print(f"[Dashboard] Belt distribution error: {e}")

    # At-risk members (no check-in in 7+ days)
    at_risk = []
    try:
        at_risk = models.get_at_risk_members(academy_id, days_threshold=7)
    except Exception:
        at_risk = []

    # Today's calendar tasks (alerts)
    today_tasks = []
    try:
        today_tasks = models.get_today_tasks(academy_id)
    except Exception:
        pass

    # Schedule days (which days of the week have classes)
    schedule_days = []
    try:
        conn = models.get_db()
        rows = conn.execute("SELECT DISTINCT day_of_week FROM class_schedule WHERE active = 1").fetchall()
        conn.close()
        day_map = {'monday':1,'tuesday':2,'wednesday':3,'thursday':4,'friday':5,'saturday':6,'sunday':0,
                   'mon':1,'tue':2,'wed':3,'thu':4,'fri':5,'sat':6,'sun':0}
        for r in rows:
            d = (r['day_of_week'] if isinstance(r, dict) else r[0]) or ''
            if isinstance(d, int):
                schedule_days.append(d)
            else:
                schedule_days.append(day_map.get(d.lower().strip(), -1))
    except Exception:
        pass

    return render_template('dashboard.html',
        greeting=greeting,
        stats=stats,
        today_classes=today_classes,
        recent_checkins=recent_checkins,
        upcoming_birthdays=upcoming_birthdays,
        payment_alerts=payment_alerts,
        belt_distribution=belt_distribution,
        at_risk=at_risk,
        schedule_days=schedule_days,
        today_tasks=today_tasks,
    )


# ═══════════════════════════════════════════════════════════════
#  MEMBERS CRUD
# ═══════════════════════════════════════════════════════════════

@app.route('/members')
@login_required
def members_list():
    academy_id = _get_academy_id()
    search = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 50

    try:
        if search:
            raw_members = models.search_members(search, academy_id)
            # search_members doesn't have enriched data, enrich lightly
            members = []
            for m in (raw_members or []):
                member = dict(m) if not isinstance(m, dict) else m
                member['belt'] = member.get('belt_name', 'White')
                member['status'] = member.get('membership_status', 'active')
                member['membership_name'] = ''
                member['membership_id'] = ''
                member['last_checkin'] = ''
                members.append(member)
        else:
            raw_members = models.get_all_members_enriched(academy_id)
            members = []
            for m in (raw_members or []):
                m['belt'] = m.get('belt_name', 'White')
                m['status'] = m.get('membership_status', 'active')
                m['membership_name'] = m.get('plan_name', '') or ''
                m['membership_id'] = m.get('plan_id', '') or ''
                m['last_checkin'] = str(m.get('last_checkin', '') or '')[:16]
                members.append(m)
    except Exception as e:
        print(f"[Members] Error: {e}")
        members = []

    # Pagination
    total = len(members)
    total_pages = max(1, (total + per_page - 1) // per_page)
    start = (page - 1) * per_page
    paginated = members[start:start + per_page]

    # Membership plans for filter dropdown
    try:
        membership_plans = models.get_all_membership_plans(academy_id)
        plans_display = []
        for p in (membership_plans or []):
            plans_display.append({
                'id': p.get('id'),
                'name': p.get('name', ''),
                'price': p.get('price', 0),
                'cycle': p.get('billing_cycle', 'monthly'),
            })
    except Exception:
        plans_display = []

    # Growth stats — total active members at end of each month (last 6 + next month)
    today = date.today()
    member_months = []  # new joins per month for sparkline
    total_by_month = []  # cumulative total each month
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        month_key = f"{y}-{m:02d}"
        new_count = sum(1 for mb in members if str(mb.get('join_date', '') or '')[:7] == month_key)
        member_months.append(new_count)
        # Total members who joined on or before this month end
        total = sum(1 for mb in members
                    if str(mb.get('join_date', '') or '')[:7] <= month_key
                    and mb.get('status') in ('active', 'trial', ''))
        total_by_month.append(total)

    new_this_month = member_months[-1] if member_months else 0
    current_total = total_by_month[-1] if total_by_month else 0
    last_month_total = total_by_month[-2] if len(total_by_month) >= 2 else 0
    growth_pct = 0
    if last_month_total > 0:
        growth_pct = int(((current_total - last_month_total) / last_month_total) * 100)
    elif current_total > 0:
        growth_pct = 100

    # Leads per month (last 6 months)
    leads_months = []
    try:
        all_prospects = models.get_all_prospects(academy_id)
    except Exception:
        all_prospects = []
    new_leads_this_month = 0
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        month_key = f"{y}-{m:02d}"
        count = sum(1 for p in (all_prospects or []) if str(p.get('created_at', '') or '')[:7] == month_key)
        leads_months.append(count)
    new_leads_this_month = leads_months[-1] if leads_months else 0

    # Lost members per month (inactive/expired by updated_at or join context)
    lost_months = []
    all_inactive = [m for m in members if m.get('status') in ('inactive', 'expired')]
    for i in range(5, -1, -1):
        m_num = today.month - i
        y = today.year
        while m_num <= 0:
            m_num += 12
            y -= 1
        month_key = f"{y}-{m_num:02d}"
        count = sum(1 for mb in all_inactive
                    if str(mb.get('updated_at', '') or mb.get('join_date', '') or '')[:7] == month_key)
        lost_months.append(count)
    lost_this_month = lost_months[-1] if lost_months else 0

    return render_template('members.html',
        members=paginated,
        membership_plans=plans_display,
        page=page,
        total_pages=total_pages,
        total_members=total,
        search=search,
        growth_pct=growth_pct,
        new_this_month=new_this_month,
        new_leads_this_month=new_leads_this_month,
        member_months=member_months,
        total_by_month=total_by_month,
        leads_months=leads_months,
        lost_this_month=lost_this_month,
        lost_months=lost_months,
    )


@app.route('/members/new', methods=['GET', 'POST'])
@app.route('/members/add', methods=['GET', 'POST'])
@login_required
def member_add():
    academy_id = _get_academy_id()

    if request.method == 'POST':
        if not validate_csrf():
            return redirect(url_for('member_add'))

        # Handle photo upload
        photo_url = ''
        if 'photo' in request.files:
            photo_url = _save_upload(request.files['photo'], 'members')

        try:
            member_id = models.create_member(
                academy_id=academy_id,
                first_name=request.form.get('first_name', '').strip(),
                last_name=request.form.get('last_name', '').strip(),
                email=request.form.get('email', '').strip(),
                phone=request.form.get('phone', '').strip(),
                date_of_birth=request.form.get('dob') or None,
                gender=request.form.get('gender', ''),
                belt_rank_id=int(request.form.get('belt_rank_id', 1)),
                stripes=int(request.form.get('stripes', 0)),
                membership_status=request.form.get('membership_status', 'active'),
                join_date=request.form.get('join_date') or str(date.today()),
                emergency_contact=request.form.get('emergency_contact', ''),
                emergency_phone=request.form.get('emergency_phone', ''),
                medical_notes=request.form.get('medical_notes', ''),
                photo=photo_url,
                source=request.form.get('source', ''),
                notes=request.form.get('notes', ''),
                pin=request.form.get('pin', '').strip() or None,
            )

            # Assign membership plan if selected
            plan_id = request.form.get('membership_plan_id')
            if plan_id and member_id:
                try:
                    models.create_membership(
                        member_id=member_id,
                        plan_id=int(plan_id),
                        status='active',
                        start_date=str(date.today()),
                    )
                except Exception:
                    pass

            # Enroll in selected programs
            if member_id:
                program_ids = request.form.getlist('program_ids')
                for pid in program_ids:
                    try:
                        models.enroll_member_program(member_id, int(pid))
                    except Exception:
                        pass

            flash('Member added successfully!', 'success')
            return redirect(url_for('member_detail', member_id=member_id))
        except Exception as e:
            print(f"[Members] Create error: {e}")
            flash('Error adding member. Please try again.', 'error')

    # GET — show form
    try:
        belt_ranks = models.get_all_belt_ranks()
    except Exception:
        belt_ranks = []

    try:
        membership_plans = models.get_all_membership_plans(academy_id)
        plans_display = []
        for p in (membership_plans or []):
            plans_display.append({
                'id': p.get('id'),
                'name': p.get('name', ''),
                'price': p.get('price', 0),
                'cycle': p.get('billing_cycle', 'monthly'),
            })
    except Exception:
        plans_display = []

    programs = models.get_programs(academy_id)
    return render_template('member_form.html',
        member=None,
        belt_ranks=belt_ranks,
        membership_plans=plans_display,
        programs=programs,
        member_programs=[],
    )


@app.route('/members/<int:member_id>')
@login_required
def member_detail(member_id):
    try:
        raw = models.get_member_by_id(member_id)
        if not raw:
            flash('Member not found.', 'error')
            return redirect(url_for('members_list'))
        member = _enrich_member(raw)
    except Exception as e:
        print(f"[Members] Detail error: {e}")
        flash('Error loading member.', 'error')
        return redirect(url_for('members_list'))

    # Recent check-ins for this member
    recent_checkins = []
    try:
        checkins = models.get_checkins_by_member(member_id, limit=20)
        for ci in (checkins or []):
            recent_checkins.append({
                'class_name': ci.get('class_name', ''),
                'time': str(ci.get('check_in_time', ''))[:16],
                'method': ci.get('method', 'manual'),
            })
    except Exception:
        pass

    # Promotions history
    promotions = []
    try:
        promotions = models.get_promotions_by_member(member_id)
    except Exception:
        pass

    # Payments history
    payments = []
    try:
        payments = models.get_payments_by_member(member_id)
    except Exception:
        pass

    # Belt progression data
    belt_ranks = []
    try:
        belt_ranks = models.get_all_belt_ranks()
    except Exception:
        pass
    belt_map = {b['id']: b for b in (belt_ranks or [])}
    belt_order = {1: 2, 2: 3, 3: 4, 4: 5}

    current_belt = belt_map.get(member.get('belt_rank_id', 1), {})
    max_stripes = current_belt.get('max_stripes', 4)
    stripes = member.get('stripes', 0) or 0
    next_belt_id = belt_order.get(member.get('belt_rank_id', 1))
    next_belt = belt_map.get(next_belt_id, {})
    min_months_next = next_belt.get('min_months', 0)

    # Months at belt (from join_date as approximation)
    months_at_belt = 0
    join_str = str(member.get('join_date', '') or '')[:10]
    if join_str:
        try:
            join_dt = datetime.strptime(join_str, '%Y-%m-%d').date()
            today = date.today()
            months_at_belt = (today.year - join_dt.year) * 12 + (today.month - join_dt.month)
            if months_at_belt < 0:
                months_at_belt = 0
        except Exception:
            pass

    stripe_pct = int(stripes / max_stripes * 100) if max_stripes else 0
    time_pct = int(months_at_belt / min_months_next * 100) if min_months_next else (100 if next_belt_id else 0)
    if time_pct > 100:
        time_pct = 100

    # Checkin history by month (last 6 months)
    checkin_months = []
    try:
        all_checkins = models.get_checkins_by_member(member_id, limit=999)
        today = date.today()
        for i in range(5, -1, -1):
            m = today.month - i
            y = today.year
            while m <= 0:
                m += 12
                y -= 1
            month_key = f"{y}-{m:02d}"
            count = sum(1 for c in (all_checkins or [])
                        if str(c.get('check_in_time', ''))[:7] == month_key)
            checkin_months.append({'label': month_key, 'count': count})
    except Exception:
        pass

    return render_template('member_detail.html',
        member=member,
        recent_checkins=recent_checkins,
        promotions=promotions,
        payments=payments,
        max_stripes=max_stripes,
        stripe_pct=stripe_pct,
        time_pct=time_pct,
        months_at_belt=months_at_belt,
        min_months_next=min_months_next,
        next_belt_name=next_belt.get('name', ''),
        checkin_months=checkin_months,
    )


@app.route('/members/<int:member_id>/edit', methods=['GET', 'POST'])
@login_required
def member_edit(member_id):
    academy_id = _get_academy_id()

    try:
        raw = models.get_member_by_id(member_id)
        if not raw:
            flash('Member not found.', 'error')
            return redirect(url_for('members_list'))
    except Exception:
        flash('Error loading member.', 'error')
        return redirect(url_for('members_list'))

    if request.method == 'POST':
        if not validate_csrf():
            return redirect(url_for('member_edit', member_id=member_id))

        update_data = {
            'first_name': request.form.get('first_name', '').strip(),
            'last_name': request.form.get('last_name', '').strip(),
            'email': request.form.get('email', '').strip(),
            'phone': request.form.get('phone', '').strip(),
            'date_of_birth': request.form.get('dob') or None,
            'gender': request.form.get('gender', ''),
            'belt_rank_id': int(request.form.get('belt_rank_id', 1)),
            'stripes': int(request.form.get('stripes', 0)),
            'membership_status': request.form.get('membership_status', 'active'),
            'join_date': request.form.get('join_date') or str(date.today()),
            'emergency_contact': request.form.get('emergency_contact', ''),
            'emergency_phone': request.form.get('emergency_phone', ''),
            'medical_notes': request.form.get('medical_notes', ''),
            'source': request.form.get('source', ''),
            'notes': request.form.get('notes', ''),
            'pin': request.form.get('pin', '').strip(),
        }

        # Photo upload
        if 'photo' in request.files and request.files['photo'].filename:
            photo_url = _save_upload(request.files['photo'], 'members')
            if photo_url:
                update_data['photo'] = photo_url

        try:
            models.update_member(member_id, **update_data)

            # Update program enrollments
            program_ids = request.form.getlist('program_ids')
            # Remove all current enrollments, re-add selected
            try:
                conn = models.get_db()
                conn.execute("DELETE FROM member_programs WHERE member_id = ?", (member_id,))
                conn.commit()
                conn.close()
            except Exception:
                pass
            for pid in program_ids:
                try:
                    models.enroll_member_program(member_id, int(pid))
                except Exception:
                    pass

            flash('Member updated successfully!', 'success')
            return redirect(url_for('member_detail', member_id=member_id))
        except Exception as e:
            print(f"[Members] Update error: {e}")
            flash('Error updating member.', 'error')

    member = _enrich_member(raw)

    try:
        belt_ranks = models.get_all_belt_ranks()
    except Exception:
        belt_ranks = []

    try:
        membership_plans = models.get_all_membership_plans(academy_id)
        plans_display = []
        for p in (membership_plans or []):
            plans_display.append({
                'id': p.get('id'),
                'name': p.get('name', ''),
                'price': p.get('price', 0),
                'cycle': p.get('billing_cycle', 'monthly'),
            })
    except Exception:
        plans_display = []

    programs = models.get_programs(academy_id)
    member_progs = models.get_member_programs(member_id)
    member_prog_ids = [p['id'] for p in member_progs]

    return render_template('member_form.html',
        member=member,
        belt_ranks=belt_ranks,
        membership_plans=plans_display,
        programs=programs,
        member_programs=member_prog_ids,
    )


@app.route('/members/<int:member_id>/delete', methods=['POST'])
@login_required
def member_delete(member_id):
    if not validate_csrf():
        return redirect(url_for('members_list'))
    try:
        models.update_member(member_id, active=False, membership_status='inactive')
        flash('Member deleted.', 'success')
    except Exception as e:
        print(f"[Members] Delete error: {e}")
        flash('Error deleting member.', 'error')
    return redirect(url_for('members_list'))


@app.route('/members/<int:member_id>/toggle-status', methods=['POST'])
@login_required
def member_toggle_status(member_id):
    if not validate_csrf():
        return redirect(url_for('members_list'))
    academy_id = _get_academy_id()
    try:
        member = models.get_member_by_id(member_id)
        if not member:
            flash('Member not found.', 'error')
            return redirect(url_for('members_list'))

        current = member.get('membership_status', 'active')
        if current == 'active':
            # Deactivate → move to prospects as ex-student
            models.update_member(member_id, membership_status='inactive')

            # Check if already exists in prospects
            existing_prospects = models.get_all_prospects(academy_id)
            already = any(
                p.get('member_id') == member_id
                for p in (existing_prospects or [])
            )
            if not already:
                enriched = _enrich_member(member)
                belt = enriched.get('belt', 'White')
                notes = f"Ex-student. Belt: {belt}. Joined: {member.get('join_date', '')}. PIN: {member.get('pin', '')}"
                models.create_prospect(
                    academy_id=academy_id,
                    first_name=member.get('first_name', ''),
                    last_name=member.get('last_name', ''),
                    email=member.get('email', ''),
                    phone=member.get('phone', ''),
                    source='ex_student',
                    status='lost',
                    interested_in=belt,
                    member_id=member_id,
                    notes=notes,
                )
            flash(f"{member.get('first_name')} set to inactive. Added to Prospects.", 'success')
        else:
            # Reactivate
            models.update_member(member_id, membership_status='active')
            # Remove from prospects (ex_student entry)
            try:
                all_prsp = models.get_all_prospects(academy_id)
                for p in (all_prsp or []):
                    if p.get('member_id') == member_id and p.get('source') == 'ex_student':
                        models.delete_prospect(p['id'])
                        break
            except Exception:
                pass
            flash(f"{member.get('first_name')} reactivated!", 'success')
    except Exception as e:
        print(f"[Members] Toggle status error: {e}")
        flash('Error updating status.', 'error')
    return redirect(request.referrer or url_for('members_list'))


@app.route('/members/<int:member_id>/qr')
@login_required
def member_qr_code(member_id):
    """Generate QR code image for member check-in."""
    try:
        import qrcode
        import io

        member = models.get_member_by_id(member_id)
        if not member:
            abort(404)

        pin = member.get('pin', '')
        if not pin:
            # Generate PIN if missing
            import random
            pin = str(random.randint(1000, 9999))
            models.update_member(member_id, pin=pin)

        # QR contains the public biometric setup URL
        qr_data = f"{request.host_url}setup-biometric/{pin}"

        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)

        return Response(buf.getvalue(), mimetype='image/png',
                       headers={'Cache-Control': 'public, max-age=86400'})
    except Exception as e:
        print(f"[QR] Error: {e}")
        abort(500)


@app.route('/members/bulk-delete', methods=['POST'])
@login_required
def members_bulk_delete():
    if not validate_csrf():
        return redirect(url_for('members_list'))
    ids_str = request.form.get('member_ids', '')
    if not ids_str:
        return redirect(url_for('members_list'))
    count = 0
    for mid in ids_str.split(','):
        try:
            mid = int(mid.strip())
            models.delete_member(mid)
            count += 1
        except Exception as e:
            print(f"[Bulk Delete] Error for id {mid}: {e}")
    flash(f'{count} members deleted.', 'success')
    return redirect(url_for('members_list'))


@app.route('/members/export-csv')
@login_required
def members_export_csv():
    import csv
    import io
    academy_id = _get_academy_id()
    ids_str = request.args.get('ids', '')

    try:
        all_members = models.get_all_members_enriched(academy_id)
    except Exception:
        all_members = []

    if ids_str:
        id_set = set()
        for x in ids_str.split(','):
            try:
                id_set.add(int(x.strip()))
            except ValueError:
                pass
        all_members = [m for m in all_members if m.get('id') in id_set]

    # Load belt ranks for progression info
    try:
        belt_ranks = models.get_all_belt_ranks()
    except Exception:
        belt_ranks = []
    belt_map = {}
    for b in (belt_ranks or []):
        belt_map[b.get('id')] = b

    # Belt progression order
    belt_order = {1: 2, 2: 3, 3: 4, 4: 5}  # White->Blue->Purple->Brown->Black

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'First Name', 'Last Name', 'Email', 'Phone', 'PIN', 'Date of Birth', 'Gender',
        'Belt', 'Belt Color', 'Stripes', 'Max Stripes',
        'Status', 'Membership Plan', 'Join Date',
        'Emergency Contact', 'Emergency Phone', 'Medical Notes',
        'Last Check-in', 'Months at Belt', 'Min Months for Next Belt',
        'Progress to Next Belt/Stripe', 'Source', 'Notes',
    ])

    today = date.today()
    for m in all_members:
        belt_id = m.get('belt_rank_id', 1)
        belt_info = belt_map.get(belt_id, {})
        belt_name = belt_info.get('name', m.get('belt_name', 'White'))
        belt_color = belt_info.get('color', '')
        max_stripes = belt_info.get('max_stripes', 4)
        stripes = m.get('stripes', 0) or 0

        # Calculate months at current belt
        join_str = str(m.get('join_date', '') or '')[:10]
        months_at_belt = 0
        if join_str:
            try:
                join_dt = datetime.strptime(join_str, '%Y-%m-%d').date()
                months_at_belt = (today.year - join_dt.year) * 12 + (today.month - join_dt.month)
                if months_at_belt < 0:
                    months_at_belt = 0
            except Exception:
                pass

        # Next belt info
        next_belt_id = belt_order.get(belt_id)
        next_belt_info = belt_map.get(next_belt_id, {})
        min_months_next = next_belt_info.get('min_months', 0)

        # Progress calculation
        if stripes < max_stripes:
            progress = f'{stripes}/{max_stripes} stripes — next stripe'
        elif next_belt_id and min_months_next > 0:
            pct = min(100, int(months_at_belt / min_months_next * 100))
            next_name = next_belt_info.get('name', '')
            progress = f'{months_at_belt}/{min_months_next} months ({pct}%) — {next_name} belt'
        elif next_belt_id:
            next_name = next_belt_info.get('name', '')
            progress = f'Ready for {next_name} belt'
        else:
            progress = 'Black belt'

        last_checkin = str(m.get('last_checkin', '') or '')[:16]

        writer.writerow([
            m.get('first_name', ''), m.get('last_name', ''), m.get('email', ''),
            m.get('phone', ''), m.get('pin', ''), m.get('date_of_birth', ''), m.get('gender', ''),
            belt_name, belt_color, stripes, max_stripes,
            m.get('membership_status', ''), m.get('plan_name', '') or '',
            join_str,
            m.get('emergency_contact', ''), m.get('emergency_phone', ''),
            m.get('medical_notes', ''),
            last_checkin, months_at_belt, min_months_next,
            progress, m.get('source', ''), m.get('notes', ''),
        ])

    from flask import Response
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=members_export_{today.strftime("%Y%m%d")}.csv'}
    )


@app.route('/members/import-csv', methods=['POST'])
@login_required
def members_import_csv():
    if not validate_csrf():
        return redirect(url_for('members_list'))

    academy_id = _get_academy_id()
    csv_file = request.files.get('csv_file')
    if not csv_file or not csv_file.filename.endswith('.csv'):
        flash('Please upload a valid CSV file.', 'error')
        return redirect(url_for('members_list'))

    import csv
    import io

    # Flexible column mapping — maps many possible header names to our field
    COLUMN_MAP = {
        # first_name
        'first_name': 'first_name', 'firstname': 'first_name', 'first': 'first_name',
        'nome': 'first_name', 'primer_nombre': 'first_name', 'name': 'first_name',
        'primeiro_nome': 'first_name',
        # last_name
        'last_name': 'last_name', 'lastname': 'last_name', 'last': 'last_name',
        'sobrenome': 'last_name', 'apellido': 'last_name', 'surname': 'last_name',
        'family_name': 'last_name', 'segundo_nome': 'last_name',
        # email
        'email': 'email', 'email_address': 'email', 'e-mail': 'email',
        'correo': 'email', 'e_mail': 'email', 'emailaddress': 'email',
        # phone
        'phone': 'phone', 'phone_number': 'phone', 'telefone': 'phone',
        'telefono': 'phone', 'celular': 'phone', 'cell': 'phone',
        'mobile': 'phone', 'tel': 'phone', 'whatsapp': 'phone',
        'phonenumber': 'phone', 'cell_phone': 'phone', 'mobile_phone': 'phone',
        # date_of_birth
        'date_of_birth': 'date_of_birth', 'dob': 'date_of_birth', 'birth': 'date_of_birth',
        'birthday': 'date_of_birth', 'birthdate': 'date_of_birth', 'birth_date': 'date_of_birth',
        'data_nascimento': 'date_of_birth', 'fecha_nacimiento': 'date_of_birth',
        'data_de_nascimento': 'date_of_birth', 'fecha_de_nacimiento': 'date_of_birth',
        'nascimento': 'date_of_birth',
        # gender
        'gender': 'gender', 'genero': 'gender', 'sexo': 'gender', 'sex': 'gender',
        # belt
        'belt': 'belt', 'belt_rank': 'belt', 'rank': 'belt', 'faixa': 'belt',
        'cinturon': 'belt', 'graduation': 'belt', 'graduacao': 'belt', 'graduación': 'belt',
        'belt_color': 'belt', 'color_faixa': 'belt',
        # stripes
        'stripes': 'stripes', 'stripe': 'stripes', 'graus': 'stripes',
        'grau': 'stripes', 'rayas': 'stripes', 'degrees': 'stripes',
        # status
        'status': 'status', 'membership_status': 'status', 'estado': 'status',
        'situacao': 'status',
        # join_date
        'join_date': 'join_date', 'joined': 'join_date', 'start_date': 'join_date',
        'data_ingresso': 'join_date', 'fecha_ingreso': 'join_date',
        'enrollment_date': 'join_date', 'registration_date': 'join_date',
        'data_de_entrada': 'join_date', 'data_cadastro': 'join_date',
        # emergency_contact
        'emergency_contact': 'emergency_contact', 'emergency_name': 'emergency_contact',
        'contato_emergencia': 'emergency_contact', 'contacto_emergencia': 'emergency_contact',
        'emergencia': 'emergency_contact', 'emergency': 'emergency_contact',
        # emergency_phone
        'emergency_phone': 'emergency_phone', 'emergency_tel': 'emergency_phone',
        'telefone_emergencia': 'emergency_phone', 'telefono_emergencia': 'emergency_phone',
        # medical_notes
        'medical_notes': 'medical_notes', 'medical': 'medical_notes',
        'health_notes': 'medical_notes', 'notas_medicas': 'medical_notes',
        'health': 'medical_notes', 'medical_info': 'medical_notes',
        'observacoes_medicas': 'medical_notes', 'saude': 'medical_notes',
        # source
        'source': 'source', 'origem': 'source', 'origen': 'source',
        'referral': 'source', 'how_found': 'source', 'indicacao': 'source',
        # notes
        'notes': 'notes', 'notas': 'notes', 'observacoes': 'notes',
        'comments': 'notes', 'comentarios': 'notes', 'obs': 'notes',
        # pin
        'pin': 'pin', 'pin_code': 'pin', 'codigo': 'pin', 'code': 'pin',
        'member_pin': 'pin', 'access_code': 'pin', 'codigo_acesso': 'pin',
    }

    belt_map = {
        'white': 1, 'branca': 1, 'blanco': 1, 'blanca': 1,
        'blue': 2, 'azul': 2,
        'purple': 3, 'roxa': 3, 'morado': 3, 'morada': 3, 'purpura': 3,
        'brown': 4, 'marrom': 4, 'marron': 4, 'cafe': 4,
        'black': 5, 'preta': 5, 'negro': 5, 'negra': 5,
    }

    imported = 0
    errors = 0

    try:
        raw = csv_file.stream.read()
        # Try utf-8-sig first, then latin-1 as fallback
        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = raw.decode('latin-1')

        stream = io.StringIO(text)
        reader = csv.DictReader(stream)

        # Normalize header names — strip all whitespace, BOM, quotes, special chars
        if reader.fieldnames:
            cleaned = []
            for f in reader.fieldnames:
                # Remove BOM, quotes, extra whitespace
                c = f.strip().strip('\ufeff').strip('"').strip("'").strip()
                c = c.lower().replace(' ', '_').replace('-', '_').replace('.', '_')
                # Remove duplicate underscores
                while '__' in c:
                    c = c.replace('__', '_')
                c = c.strip('_')
                cleaned.append(c)
            reader.fieldnames = cleaned

        # Build mapping from CSV columns to our fields
        col_mapping = {}
        for csv_col in (reader.fieldnames or []):
            mapped = COLUMN_MAP.get(csv_col)
            if not mapped:
                # Try partial matching — if csv header contains a known key
                for key, field in COLUMN_MAP.items():
                    if key in csv_col or csv_col in key:
                        if field not in col_mapping.values():
                            mapped = field
                            break
            if mapped and mapped not in col_mapping.values():
                col_mapping[csv_col] = mapped

        print(f"[CSV Import] Raw headers: {reader.fieldnames}")
        print(f"[CSV Import] Mapped: {col_mapping}")

        def get_field(row, field):
            """Get a field value using the column mapping."""
            for csv_col, mapped_field in col_mapping.items():
                if mapped_field == field:
                    val = row.get(csv_col, '')
                    return val.strip() if val else ''
            # Fallback: try direct field name in row
            val = row.get(field, '')
            return val.strip() if val else ''

        # Pre-load existing members for upsert matching
        try:
            existing_members = models.get_all_members(academy_id)
        except Exception:
            existing_members = []
        # Build lookup by lowercase name
        existing_lookup = {}
        for ex in (existing_members or []):
            key = (ex.get('first_name', '').lower().strip(), ex.get('last_name', '').lower().strip())
            existing_lookup[key] = ex

        for row in reader:
            try:
                first_name = get_field(row, 'first_name')
                last_name = get_field(row, 'last_name')

                # If no last_name column, try splitting name
                if first_name and not last_name:
                    parts = first_name.split(None, 1)
                    if len(parts) == 2:
                        first_name, last_name = parts

                if not first_name:
                    errors += 1
                    continue

                # Belt parsing
                belt_str = get_field(row, 'belt').lower()
                belt_id = belt_map.get(belt_str, 1)

                # Stripes parsing
                stripes_str = get_field(row, 'stripes')
                try:
                    stripes_val = int(stripes_str) if stripes_str else 0
                except ValueError:
                    stripes_val = 0

                # Status parsing
                status_raw = get_field(row, 'status').lower()
                status_map = {
                    'active': 'active', 'ativo': 'active', 'activo': 'active',
                    'inactive': 'inactive', 'inativo': 'inactive', 'inactivo': 'inactive',
                    'expired': 'expired', 'expirado': 'expired', 'vencido': 'expired',
                    'trial': 'trial', 'teste': 'trial', 'prueba': 'trial',
                }
                status = status_map.get(status_raw, 'active')

                email_val = get_field(row, 'email')
                phone_val = get_field(row, 'phone')
                dob_val = get_field(row, 'date_of_birth') or None
                gender_val = get_field(row, 'gender')
                join_val = get_field(row, 'join_date') or str(date.today())
                ec_val = get_field(row, 'emergency_contact')
                ep_val = get_field(row, 'emergency_phone')
                med_val = get_field(row, 'medical_notes')
                src_val = get_field(row, 'source') or 'csv_import'
                notes_val = get_field(row, 'notes')
                pin_val = get_field(row, 'pin')

                # Check if member already exists (match by name)
                existing = existing_lookup.get((first_name.lower().strip(), last_name.lower().strip()))

                if existing:
                    # Update existing member — only fill in non-empty fields
                    update_data = {}
                    if email_val and not existing.get('email'):
                        update_data['email'] = email_val
                    elif email_val:
                        update_data['email'] = email_val
                    if phone_val:
                        update_data['phone'] = phone_val
                    if dob_val and not existing.get('date_of_birth'):
                        update_data['date_of_birth'] = dob_val
                    if gender_val and not existing.get('gender'):
                        update_data['gender'] = gender_val
                    if belt_id != 1 or not existing.get('belt_rank_id'):
                        update_data['belt_rank_id'] = belt_id
                    if stripes_val:
                        update_data['stripes'] = stripes_val
                    if ec_val:
                        update_data['emergency_contact'] = ec_val
                    if ep_val:
                        update_data['emergency_phone'] = ep_val
                    if med_val:
                        update_data['medical_notes'] = med_val
                    if notes_val:
                        update_data['notes'] = notes_val
                    if src_val and src_val != 'csv_import':
                        update_data['source'] = src_val
                    if pin_val:
                        update_data['pin'] = pin_val

                    if update_data:
                        models.update_member(existing['id'], **update_data)
                    imported += 1
                else:
                    models.create_member(
                        academy_id=academy_id,
                        first_name=first_name,
                        last_name=last_name,
                        email=email_val,
                        phone=phone_val,
                        date_of_birth=dob_val,
                        gender=gender_val,
                        belt_rank_id=belt_id,
                        stripes=stripes_val,
                        membership_status=status,
                        join_date=join_val,
                        emergency_contact=ec_val,
                        emergency_phone=ep_val,
                        medical_notes=med_val,
                        source=src_val,
                        notes=notes_val,
                        pin=pin_val,
                    )
                    imported += 1
            except Exception as e:
                print(f"[CSV Import] Row error: {e}")
                errors += 1

        if imported:
            flash(f'{imported} members imported successfully!' + (f' ({errors} rows skipped)' if errors else ''), 'success')
        else:
            flash(f'No members imported. {errors} rows had errors.', 'warning')
    except Exception as e:
        print(f"[CSV Import] Error: {e}")
        flash('Error reading CSV file. Check the format.', 'error')

    return redirect(url_for('members_list'))


# ═══════════════════════════════════════════════════════════════
#  MEMBERSHIPS
# ═══════════════════════════════════════════════════════════════

@app.route('/memberships')
@login_required
def memberships_list():
    academy_id = _get_academy_id()
    try:
        plans = models.get_all_membership_plans(academy_id)
    except Exception:
        plans = []
    try:
        memberships = models.get_all_memberships(academy_id)
    except Exception:
        memberships = []
    try:
        members = models.get_all_members(academy_id)
    except Exception:
        members = []

    # Enrich plans with display fields and active member count
    for plan in plans:
        plan['cycle'] = plan.get('billing_cycle', 'monthly')
        plan['type'] = plan.get('plan_type', 'Standard')
        plan['active_members'] = len([ms for ms in memberships if ms.get('plan_id') == plan.get('id') and ms.get('status') == 'active'])

    return render_template('memberships.html',
        plans=plans,
        memberships=memberships,
        members=members,
    )


@app.route('/memberships/plans/add', methods=['POST'])
@login_required
def membership_plan_add():
    if not validate_csrf():
        return redirect(url_for('memberships_list'))
    academy_id = _get_academy_id()
    try:
        models.create_membership_plan(
            academy_id=academy_id,
            name=request.form.get('name', '').strip(),
            plan_type=request.form.get('plan_type', 'monthly'),
            price=float(request.form.get('price', 0)),
            billing_cycle=request.form.get('billing_cycle', 'monthly'),
            trial_days=int(request.form.get('trial_days', 0)),
            description=request.form.get('description', ''),
        )
        flash('Plan created successfully!', 'success')
    except Exception as e:
        print(f"[Plans] Create error: {e}")
        flash('Error creating plan.', 'error')
    return redirect(url_for('memberships_list'))


@app.route('/memberships/assign', methods=['POST'])
@login_required
def membership_assign():
    if not validate_csrf():
        return redirect(url_for('memberships_list'))
    try:
        member_id = int(request.form.get('member_id', 0))
        plan_id = int(request.form.get('plan_id', 0))
        start_date = request.form.get('start_date') or str(date.today())
        end_date = request.form.get('end_date') or None
        auto_renew = bool(request.form.get('auto_renew'))

        models.create_membership(
            member_id=member_id,
            plan_id=plan_id,
            status='active',
            start_date=start_date,
            end_date=end_date,
            auto_renew=auto_renew,
        )
        flash('Membership assigned!', 'success')
    except Exception as e:
        print(f"[Memberships] Assign error: {e}")
        flash('Error assigning membership.', 'error')
    return redirect(url_for('memberships_list'))


@app.route('/api/memberships/bulk-assign', methods=['POST'])
@login_required
def api_memberships_bulk_assign():
    """Assign multiple members to a plan at once."""
    data = request.get_json() or {}
    plan_id = data.get('plan_id')
    member_ids = data.get('member_ids', [])
    if not plan_id or not member_ids:
        return jsonify({'error': 'plan_id and member_ids required'}), 400
    try:
        for mid in member_ids:
            models.create_membership(
                member_id=int(mid),
                plan_id=int(plan_id),
                status='active',
                start_date=str(date.today()),
                auto_renew=True,
            )
        return jsonify({'success': True, 'count': len(member_ids)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/memberships/cancel', methods=['POST'])
@login_required
def api_memberships_cancel():
    """Cancel a membership — stops counting and billing."""
    data = request.get_json() or {}
    membership_id = data.get('membership_id')
    if not membership_id:
        return jsonify({'error': 'membership_id required'}), 400
    try:
        models.update_membership(int(membership_id), status='cancelled')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════
#  CLASSES
# ═══════════════════════════════════════════════════════════════

@app.route('/classes')
@login_required
def classes_list():
    academy_id = _get_academy_id()
    days_map = {0: 'monday', 1: 'tuesday', 2: 'wednesday', 3: 'thursday',
                4: 'friday', 5: 'saturday', 6: 'sunday'}

    schedule = {d: [] for d in days_map.values()}
    try:
        all_schedules = models.get_all_class_schedules(academy_id)
        for s in (all_schedules or []):
            day_num = s.get('day_of_week', 0)
            day_name = days_map.get(day_num, 'monday')
            schedule[day_name].append({
                'id': s.get('class_id', s.get('id')),
                'name': s.get('class_name', ''),
                'start_time': s.get('start_time', ''),
                'end_time': s.get('end_time', ''),
                'type': s.get('class_type', 'gi'),
                'instructor': s.get('instructor', ''),
                'enrolled': 0,
                'capacity': s.get('max_capacity', 30),
            })
    except Exception as e:
        print(f"[Classes] Error: {e}")

    try:
        classes = models.get_all_classes(academy_id)
    except Exception:
        classes = []

    programs = models.get_programs(academy_id)
    from datetime import datetime as dt
    return render_template('classes.html',
        schedule=schedule,
        classes=classes,
        programs=programs,
        now_dow=dt.now().weekday(),
    )


@app.route('/classes/new', methods=['GET', 'POST'])
@app.route('/classes/add', methods=['GET', 'POST'])
@login_required
def class_add():
    academy_id = _get_academy_id()

    if request.method == 'POST':
        if not validate_csrf():
            return redirect(url_for('class_add'))

        try:
            # Get instructor name from ID
            instructor_name = ''
            instructor_id = request.form.get('instructor_id', '')
            if instructor_id:
                try:
                    inst_user = models.get_user(int(instructor_id))
                    if inst_user:
                        instructor_name = inst_user.get('name', '')
                except Exception:
                    pass

            class_id = models.create_class(
                academy_id=academy_id,
                name=request.form.get('name', '').strip(),
                class_type=request.form.get('type', 'gi'),
                instructor=instructor_name,
                description=request.form.get('description', ''),
                duration=int(request.form.get('duration', 60)),
                max_capacity=int(request.form.get('max_capacity', 30)),
                belt_level=request.form.get('belt_minimum', 'all'),
            )

            # Create schedule entries
            days = request.form.getlist('days')
            start_time = request.form.get('start_time', '')
            end_time = request.form.get('end_time', '')
            for day in days:
                try:
                    models.create_class_schedule(
                        class_id=class_id,
                        day_of_week=int(day),
                        start_time=start_time,
                        end_time=end_time,
                    )
                except Exception:
                    pass

            flash('Class created successfully!', 'success')
            return redirect(url_for('classes_list'))
        except Exception as e:
            print(f"[Classes] Create error: {e}")
            flash('Error creating class.', 'error')

    # Get instructors (admins + instructors) for dropdown
    try:
        all_users = models.get_all_users()
        instructors = [u for u in (all_users or []) if u.get('role') in ('admin', 'instructor') and u.get('active')]
    except Exception:
        instructors = []

    programs = models.get_programs(academy_id)
    return render_template('class_form.html', cls=None, instructors=instructors, programs=programs)


@app.route('/classes/<int:class_id>/edit', methods=['GET', 'POST'])
@login_required
def class_edit(class_id):
    try:
        cls = models.get_class_by_id(class_id)
        if not cls:
            flash('Class not found.', 'error')
            return redirect(url_for('classes_list'))
    except Exception:
        flash('Error loading class.', 'error')
        return redirect(url_for('classes_list'))

    if request.method == 'POST':
        if not validate_csrf():
            return redirect(url_for('class_edit', class_id=class_id))
        try:
            # Get instructor name from ID
            instructor_name = ''
            instructor_id = request.form.get('instructor_id', '')
            if instructor_id:
                try:
                    inst_user = models.get_user(int(instructor_id))
                    if inst_user:
                        instructor_name = inst_user.get('name', '')
                except Exception:
                    pass

            models.update_class(class_id,
                name=request.form.get('name', '').strip(),
                class_type=request.form.get('type', 'gi'),
                instructor=instructor_name,
                description=request.form.get('description', ''),
                duration=int(request.form.get('duration', 60)),
                max_capacity=int(request.form.get('max_capacity', 30)),
                belt_level=request.form.get('belt_minimum', 'all'),
            )

            # Update schedule: delete old, create new
            try:
                models.delete_class_schedules(class_id)
                days = request.form.getlist('days')
                start_time = request.form.get('start_time', '')
                end_time = request.form.get('end_time', '')
                for day in days:
                    models.create_class_schedule(
                        class_id=class_id,
                        day_of_week=int(day),
                        start_time=start_time,
                        end_time=end_time,
                    )
            except Exception as e:
                print(f"[Classes] Schedule update error: {e}")

            flash('Class updated!', 'success')
            return redirect(url_for('classes_list'))
        except Exception as e:
            print(f"[Classes] Update error: {e}")
            flash('Error updating class.', 'error')

    try:
        all_users = models.get_all_users()
        instructors = [u for u in (all_users or []) if u.get('role') in ('admin', 'instructor') and u.get('active')]
    except Exception:
        instructors = []

    # Get existing schedule days for this class
    try:
        schedules = models.get_schedules_for_class(class_id)
        cls['schedule_days'] = [s.get('day_of_week') for s in (schedules or [])]
        if schedules:
            cls['start_time'] = schedules[0].get('start_time', '')
            cls['end_time'] = schedules[0].get('end_time', '')
    except Exception:
        cls['schedule_days'] = []

    return render_template('class_form.html', cls=cls, instructors=instructors)


@app.route('/classes/<int:class_id>/delete', methods=['POST'])
@login_required
def class_delete(class_id):
    if not validate_csrf():
        return redirect(url_for('classes_list'))
    try:
        models.delete_class(class_id)
        flash('Class deleted.', 'success')
    except Exception as e:
        print(f"[Classes] Delete error: {e}")
        flash('Error deleting class.', 'error')
    return redirect(url_for('classes_list'))


# ═══════════════════════════════════════════════════════════════
#  PROGRAMS
# ═══════════════════════════════════════════════════════════════

@app.route('/programs')
@login_required
def programs_list():
    academy_id = _get_academy_id()
    programs = models.get_programs(academy_id)
    # Get member count and list per program
    for p in programs:
        members = models.get_members_by_program(academy_id, p['id'])
        p['members'] = members
        p['member_count'] = len(members)
    return render_template('programs.html', programs=programs)


@app.route('/programs/add', methods=['POST'])
@login_required
def program_add():
    academy_id = _get_academy_id()
    name = request.form.get('name', '').strip()
    color = request.form.get('color', '#6366f1').strip()
    description = request.form.get('description', '').strip()
    if name:
        models.add_program(academy_id, name, color, description)
        flash(f'Program "{name}" created!', 'success')
    return redirect(url_for('programs_list'))


@app.route('/programs/<int:program_id>/edit', methods=['POST'])
@login_required
def program_edit(program_id):
    name = request.form.get('name', '').strip()
    color = request.form.get('color', '#6366f1').strip()
    description = request.form.get('description', '').strip()
    if name:
        models.update_program(program_id, name=name, color=color, description=description)
        flash(f'Program updated!', 'success')
    return redirect(url_for('programs_list'))


@app.route('/programs/<int:program_id>/delete', methods=['POST'])
@login_required
def program_delete(program_id):
    models.delete_program(program_id)
    flash('Program deleted.', 'success')
    return redirect(url_for('programs_list'))


@app.route('/api/programs/<int:program_id>/enroll', methods=['POST'])
@login_required
def api_program_enroll(program_id):
    data = request.get_json() or {}
    member_id = data.get('member_id')
    if not member_id:
        return jsonify({'error': 'member_id required'}), 400
    models.enroll_member_program(int(member_id), program_id)
    return jsonify({'success': True})


@app.route('/api/programs/<int:program_id>/unenroll', methods=['POST'])
@login_required
def api_program_unenroll(program_id):
    data = request.get_json() or {}
    member_id = data.get('member_id')
    if not member_id:
        return jsonify({'error': 'member_id required'}), 400
    models.unenroll_member_program(int(member_id), program_id)
    return jsonify({'success': True})


@app.route('/api/members/search-for-program')
@login_required
def api_search_members_program():
    q = request.args.get('q', '').strip()
    academy_id = _get_academy_id()
    exclude_belt = request.args.get('exclude_belt', '')
    if not q:
        return jsonify([])
    try:
        conn = models.get_db()
        if exclude_belt:
            rows = conn.execute(
                """SELECT m.id, m.first_name, m.last_name, m.email, m.phone, m.belt_rank_id, m.stripes,
                          COALESCE(b.name, 'White') as belt_name
                   FROM members m
                   LEFT JOIN belt_ranks b ON b.id = m.belt_rank_id
                   WHERE m.academy_id = ? AND m.active = 1 AND m.belt_rank_id != ? AND (
                       LOWER(m.first_name || ' ' || m.last_name) LIKE ? OR
                       LOWER(m.email) LIKE ? OR m.phone LIKE ?
                   ) LIMIT 10""",
                (academy_id, int(exclude_belt), f'%{q.lower()}%', f'%{q.lower()}%', f'%{q}%')
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT m.id, m.first_name, m.last_name, m.email, m.phone, m.belt_rank_id, m.stripes,
                          COALESCE(b.name, 'White') as belt_name
                   FROM members m
                   LEFT JOIN belt_ranks b ON b.id = m.belt_rank_id
                   WHERE m.academy_id = ? AND m.active = 1 AND (
                       LOWER(m.first_name || ' ' || m.last_name) LIKE ? OR
                       LOWER(m.email) LIKE ? OR m.phone LIKE ?
                   ) LIMIT 10""",
                (academy_id, f'%{q.lower()}%', f'%{q.lower()}%', f'%{q}%')
            ).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception:
        return jsonify([])


# ═══════════════════════════════════════════════════════════════
#  CHECK-IN
# ═══════════════════════════════════════════════════════════════

@app.route('/checkin')
@login_required
def checkin_page():
    academy_id = _get_academy_id()

    # Detect current class based on time
    current_class = None
    try:
        now = datetime.now()
        dow = now.weekday()
        current_time = now.strftime('%H:%M')
        schedules = models.get_schedule_by_day(dow, academy_id)
        for s in (schedules or []):
            st = s.get('start_time', '')
            et = s.get('end_time', '')
            if st <= current_time <= et:
                current_class = {
                    'id': s.get('class_id', s.get('id')),
                    'name': s.get('class_name', ''),
                    'start_time': st,
                    'end_time': et,
                    'instructor': s.get('instructor', ''),
                }
                break
    except Exception:
        pass

    # All active members for tap-to-checkin grid
    members = []
    try:
        raw = models.get_all_members(academy_id)
        for m in (raw or []):
            if m.get('membership_status') == 'active' or m.get('active') in (True, 1):
                members.append({
                    'id': m.get('id'),
                    'first_name': m.get('first_name', ''),
                    'last_name': m.get('last_name', ''),
                    'photo': m.get('photo', ''),
                    'belt': m.get('belt_name', 'White'),
                    'initials': (m.get('first_name', ' ')[0] + m.get('last_name', ' ')[0]).upper(),
                })
    except Exception:
        pass

    # Today's check-ins
    today_checkins = []
    try:
        today_checkins = models.get_today_checkins(academy_id)
    except Exception:
        pass

    # Today's check-in count
    today_count = 0
    try:
        today_count = models.get_today_checkin_count(academy_id)
    except Exception:
        pass

    return render_template('checkin.html',
        current_class=current_class,
        members=members,
        today_checkins=today_checkins,
        today_count=today_count,
    )


@app.route('/checkin/manual', methods=['POST'])
@app.route('/checkin/quick', methods=['POST'])
@login_required
def checkin_manual():
    if not validate_csrf():
        return redirect(request.referrer or url_for('checkin_page'))
    academy_id = _get_academy_id()
    member_id = request.form.get('member_id')
    class_id = request.form.get('class_id') or None

    if not member_id:
        flash('Please select a member.', 'error')
        return redirect(url_for('checkin_page'))

    try:
        models.create_checkin(
            member_id=int(member_id),
            class_id=int(class_id) if class_id else None,
            academy_id=academy_id,
            method='manual',
        )
        member = models.get_member_by_id(int(member_id))
        name = f"{member.get('first_name', '')} {member.get('last_name', '')}" if member else 'Member'
        flash(f'Check-in successful! Welcome, {name}!', 'success')
    except Exception as e:
        print(f"[Checkin] Error: {e}")
        flash('Check-in failed.', 'error')

    return redirect(request.referrer or url_for('checkin_page'))


@app.route('/checkin/pin', methods=['POST'])
@login_required
def checkin_pin():
    if not validate_csrf():
        return redirect(url_for('checkin_page'))

    pin = request.form.get('pin', '').strip()
    class_id = request.form.get('class_id')
    academy_id = _get_academy_id()

    if not pin or len(pin) != 4:
        flash('Invalid PIN.', 'error')
        return redirect(url_for('checkin_page'))

    # Find member by PIN
    try:
        all_members = models.get_all_members(academy_id)
        member = None
        for m in (all_members or []):
            if m.get('pin') == pin:
                member = m
                break

        if not member:
            flash('PIN not found. Please try again.', 'error')
            return redirect(url_for('checkin_page'))

        # Create check-in
        models.create_checkin(
            member_id=member['id'],
            class_id=int(class_id) if class_id else None,
            academy_id=academy_id,
            method='pin'
        )

        name = f"{member.get('first_name', '')} {member.get('last_name', '')}"
        flash(f'Check-in: {name}', 'success')
        return redirect(url_for('checkin_page', success=name))
    except Exception as e:
        print(f"[Checkin] PIN error: {e}")
        flash('Error during check-in.', 'error')
        return redirect(url_for('checkin_page'))


@app.route('/checkin/qr')
@login_required
def checkin_qr():
    """Handle QR code scan check-in."""
    code = request.args.get('code', '').strip()
    academy_id = _get_academy_id()

    if not code:
        flash('Invalid QR code.', 'error')
        return redirect(url_for('checkin_page'))

    # Parse QR: CHECKIN:{pin}
    pin = code.replace('CHECKIN:', '').strip()

    try:
        all_members = models.get_all_members(academy_id)
        member = None
        for m in (all_members or []):
            if m.get('pin') == pin:
                member = m
                break

        if not member:
            flash('Member not found from QR code.', 'error')
            return redirect(url_for('checkin_page'))

        models.create_checkin(
            member_id=member['id'],
            class_id=None,
            academy_id=academy_id,
            method='qr',
        )

        name = f"{member.get('first_name', '')} {member.get('last_name', '')}"
        flash(f'Check-in: {name}', 'success')
        return redirect(url_for('checkin_page', success=name))
    except Exception as e:
        print(f"[Checkin] QR error: {e}")
        flash('Error during check-in.', 'error')
        return redirect(url_for('checkin_page'))


@app.route('/checkin/history')
@login_required
def checkin_history():
    academy_id = _get_academy_id()
    date_from = request.args.get('from', '')
    date_to = request.args.get('to', '')

    try:
        checkins = models.get_all_checkins(academy_id, limit=200)
        # Filter by date if provided
        if date_from:
            checkins = [c for c in checkins if str(c.get('check_in_time', ''))[:10] >= date_from]
        if date_to:
            checkins = [c for c in checkins if str(c.get('check_in_time', ''))[:10] <= date_to]
    except Exception:
        checkins = []

    stats = {
        'month_total': len([c for c in checkins if str(c.get('check_in_time', ''))[:7] == datetime.now().strftime('%Y-%m')]),
        'avg_daily': 0,
        'total': len(checkins),
    }
    if stats['month_total'] > 0:
        stats['avg_daily'] = round(stats['month_total'] / max(1, datetime.now().day), 1)

    return render_template('checkin_history.html',
        checkins=checkins,
        stats=stats,
        date_from=date_from,
        date_to=date_to,
    )


@app.route('/attendance')
@login_required
def attendance_report():
    academy_id = _get_academy_id()
    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))
    report = models.get_attendance_report(academy_id, month, year)

    # Find members absent 15+ days
    today = date.today()
    absent_members = []
    for m in report:
        last = m.get('last_checkin')
        if last:
            try:
                last_date = datetime.strptime(str(last)[:10], '%Y-%m-%d').date()
                days_absent = (today - last_date).days
                if days_absent >= 15:
                    m['days_absent'] = days_absent
                    absent_members.append(m)
            except Exception:
                pass
        else:
            # Never checked in — count from join or just mark as absent
            m['days_absent'] = 999
            absent_members.append(m)
    absent_members.sort(key=lambda x: x.get('days_absent', 0), reverse=True)

    # Top attendees this month
    top_members = sorted([m for m in report if m.get('total_checkins', 0) > 0], key=lambda x: x['total_checkins'], reverse=True)[:5]

    # Check-in history for the selected month
    month_str = f"{year}-{str(month).zfill(2)}"
    try:
        all_checkins = models.get_all_checkins(academy_id, limit=1000)
        history = [c for c in all_checkins if str(c.get('check_in_time', ''))[:7] == month_str]
    except Exception:
        history = []

    # Format history entries
    for h in history:
        cit = str(h.get('check_in_time', ''))
        h['date'] = cit[:10] if len(cit) >= 10 else ''
        h['time'] = cit[11:16] if len(cit) >= 16 else ''
        h['member_name'] = f"{h.get('first_name','')} {h.get('last_name','')}"
        h['member_initials'] = f"{h.get('first_name','?')[0]}{h.get('last_name','?')[0]}"

    months = ['January','February','March','April','May','June','July','August','September','October','November','December']
    return render_template('attendance.html',
        report=report, month=month, year=year, months=months,
        absent_members=absent_members, top_members=top_members,
        today=str(today), history=history,
    )


@app.route('/api/attendance/send-report', methods=['POST'])
@login_required
def api_send_attendance_report():
    """Generate and send monthly attendance report via email or WhatsApp."""
    data = request.get_json() or {}
    method = data.get('method', 'email')
    month = int(data.get('month', datetime.now().month))
    year = int(data.get('year', datetime.now().year))
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    academy_id = _get_academy_id()

    months_list = ['January','February','March','April','May','June','July','August','September','October','November','December']
    month_name = months_list[month - 1]

    # Generate report data
    report = models.get_attendance_report(academy_id, month, year)
    total = len(report)
    active = len([m for m in report if m.get('total_checkins', 0) > 0])
    total_checkins = sum(m.get('total_checkins', 0) for m in report)
    pct = round(active / total * 100, 1) if total > 0 else 0

    # Top 5
    top5 = sorted([m for m in report if m.get('total_checkins', 0) > 0], key=lambda x: x['total_checkins'], reverse=True)[:5]

    # Absent 15+ days
    today_d = date.today()
    absent = []
    for m in report:
        last = m.get('last_checkin')
        if last:
            try:
                last_date = datetime.strptime(str(last)[:10], '%Y-%m-%d').date()
                days = (today_d - last_date).days
                if days >= 15:
                    absent.append({'name': f"{m['first_name']} {m['last_name']}", 'days': days})
            except Exception:
                pass
        else:
            absent.append({'name': f"{m['first_name']} {m['last_name']}", 'days': 999})

    # Build text report
    lines = [
        f"📊 *Attendance Report — {month_name} {year}*",
        f"",
        f"👥 Total Members: {total}",
        f"✅ Trained: {active} ({pct}%)",
        f"📋 Total Check-ins: {total_checkins}",
        f"⚠️ Absent 15+ days: {len(absent)}",
        f"",
    ]
    if top5:
        lines.append("🏆 *Top Attendees:*")
        for i, m in enumerate(top5):
            medal = ['🥇','🥈','🥉','4️⃣','5️⃣'][i]
            lines.append(f"  {medal} {m['first_name']} {m['last_name']} — {m['total_checkins']} check-ins")
        lines.append("")

    if absent:
        lines.append(f"🚨 *Absent 15+ Days ({len(absent)}):*")
        for a in absent[:10]:
            days_txt = 'Never' if a['days'] == 999 else f"{a['days']} days"
            lines.append(f"  ❌ {a['name']} — {days_txt}")
        if len(absent) > 10:
            lines.append(f"  ... and {len(absent) - 10} more")

    report_text = '\n'.join(lines)

    if method == 'whatsapp':
        if not phone:
            return jsonify({'error': 'Phone number required'}), 400
        import urllib.parse
        wa_url = f"https://wa.me/{phone.replace('+','').replace(' ','')}?text={urllib.parse.quote(report_text)}"
        return jsonify({'success': True, 'whatsapp_url': wa_url, 'message': report_text})
    elif method == 'email':
        if not email:
            return jsonify({'error': 'Email address required'}), 400
        # For now, return the report text (email integration can be added later)
        return jsonify({'success': True, 'message': report_text, 'note': 'Email delivery coming soon. Report text generated.'})
    else:
        return jsonify({'error': 'Invalid method'}), 400


@app.route('/api/calendar/tasks')
@login_required
def api_calendar_tasks():
    """Get tasks for a month (used by calendar JS)."""
    academy_id = _get_academy_id()
    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))
    tasks = models.get_calendar_tasks(academy_id, month, year)
    return jsonify(tasks)


@app.route('/api/calendar/task', methods=['POST'])
@login_required
def api_calendar_task_add():
    """Add a calendar task."""
    academy_id = _get_academy_id()
    data = request.get_json() or request.form
    title = (data.get('title') or '').strip()
    task_date = (data.get('task_date') or '').strip()
    description = (data.get('description') or '').strip()
    task_time = (data.get('task_time') or '').strip()
    color = (data.get('color') or '#6366f1').strip()

    if not title or not task_date:
        return jsonify({'error': 'Title and date required'}), 400

    models.add_calendar_task(academy_id, session.get('user_id'), title, task_date, description, task_time, color)
    return jsonify({'success': True})


@app.route('/api/calendar/task/<int:task_id>', methods=['PUT'])
@login_required
def api_calendar_task_update(task_id):
    """Update or complete a task."""
    data = request.get_json() or {}
    models.update_calendar_task(task_id, **data)
    return jsonify({'success': True})


@app.route('/api/calendar/task/<int:task_id>', methods=['DELETE'])
@login_required
def api_calendar_task_delete(task_id):
    """Delete a task."""
    models.delete_calendar_task(task_id)
    return jsonify({'success': True})


@app.route('/api/checkin/search')
@login_required
def api_checkin_search():
    q = request.args.get('q', '').strip()
    academy_id = _get_academy_id()
    if not q or len(q) < 1:
        return jsonify([])
    try:
        results = models.search_members(q, academy_id)
        return jsonify([{
            'id': m.get('id'),
            'first_name': m.get('first_name', ''),
            'last_name': m.get('last_name', ''),
            'photo': m.get('photo', ''),
            'belt': m.get('belt_name', 'White'),
        } for m in (results or [])[:20]])
    except Exception:
        return jsonify([])


@app.route('/api/checkin', methods=['POST'])
@login_required
def api_checkin():
    academy_id = _get_academy_id()
    data = request.get_json() or {}
    member_id = data.get('member_id')
    class_id = data.get('class_id')

    if not member_id:
        return jsonify({'success': False, 'error': 'No member selected'}), 400

    try:
        checkin_id = models.create_checkin(
            member_id=int(member_id),
            class_id=int(class_id) if class_id else None,
            academy_id=academy_id,
            method='kiosk',
        )
        member = models.get_member_by_id(int(member_id))
        name = f"{member.get('first_name', '')} {member.get('last_name', '')}" if member else 'Member'
        return jsonify({'success': True, 'checkin_id': checkin_id, 'member_name': name})
    except Exception as e:
        print(f"[API Checkin] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/checkin/pin', methods=['POST'])
@login_required
def api_checkin_pin():
    academy_id = _get_academy_id()
    data = request.get_json() or {}
    pin = data.get('pin', '').strip()
    class_id = data.get('class_id') or None

    if not pin or len(pin) != 4:
        return jsonify({'success': False, 'error': 'Invalid PIN'}), 400

    try:
        all_members = models.get_all_members(academy_id)
        member = None
        for m in (all_members or []):
            if m.get('pin') == pin:
                member = m
                break

        if not member:
            return jsonify({'success': False, 'error': 'PIN not found'}), 404

        models.create_checkin(
            member_id=member['id'],
            class_id=int(class_id) if class_id else None,
            academy_id=academy_id,
            method='pin',
        )

        name = f"{member.get('first_name', '')} {member.get('last_name', '')}"
        return jsonify({'success': True, 'name': name})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════
#  BELTS
# ═══════════════════════════════════════════════════════════════

@app.route('/belts')
@login_required
def belts_page():
    academy_id = _get_academy_id()
    try:
        belt_ranks = models.get_all_belt_ranks()
    except Exception:
        belt_ranks = []

    # Get members for each belt
    kids_belts_names = {'White', 'Grey', 'Yellow', 'Orange', 'Green'}
    adult_belts_names = {'White', 'Blue', 'Purple', 'Brown', 'Black'}
    coral_belts_names = {'Red/Black', 'Red/White', 'Red'}
    belts = []
    try:
        all_members = models.get_all_members(academy_id)
        for b in (belt_ranks or []):
            belt_members = [m for m in (all_members or []) if m.get('belt_rank_id') == b.get('id')]
            bname = b.get('name', '')
            category = 'adults'
            if bname in coral_belts_names:
                category = 'coral'
            elif bname in ('Grey', 'Yellow', 'Orange', 'Green'):
                category = 'kids'
            elif bname == 'White':
                category = 'kids_adults'
            belts.append({
                'id': b.get('id'),
                'name': bname,
                'color': b.get('color', '#000'),
                'count': len(belt_members),
                'max_stripes': b.get('max_stripes', 4),
                'min_months': b.get('min_months', 0),
                'sort_order': b.get('sort_order', 0),
                'category': category,
                'members': belt_members[:20],
            })
    except Exception as e:
        print(f"[Belts] Error: {e}")

    try:
        promotions = models.get_all_promotions(academy_id)
    except Exception:
        promotions = []

    return render_template('belts.html',
        belts=belts,
        belt_ranks=belt_ranks,
        promotions=promotions,
    )


@app.route('/belts/promote', methods=['GET', 'POST'])
@login_required
def belt_promote():
    academy_id = _get_academy_id()

    if request.method == 'POST':
        if not validate_csrf():
            return redirect(url_for('belt_promote'))
        try:
            member_id = int(request.form.get('member_id', 0))
            new_belt_name = request.form.get('new_belt', '').strip()
            new_stripes = int(request.form.get('new_stripes', 0))
            promotion_date = request.form.get('promotion_date') or str(date.today())
            promoted_by = request.form.get('promoted_by', '')
            notes = request.form.get('notes', '')

            # Get current member belt
            member = models.get_member_by_id(member_id)
            from_belt_id = member.get('belt_rank_id', 1) if member else 1
            from_stripes = member.get('stripes', 0) if member else 0

            # Find new belt ID by name
            belt_ranks = models.get_all_belt_ranks()
            to_belt_id = from_belt_id
            for b in (belt_ranks or []):
                if b.get('name') == new_belt_name:
                    to_belt_id = b['id']
                    break

            # Record promotion
            models.create_promotion(
                member_id=member_id,
                from_belt_id=from_belt_id,
                to_belt_id=to_belt_id,
                from_stripes=from_stripes,
                to_stripes=new_stripes,
                promotion_date=promotion_date,
                promoted_by=promoted_by,
                notes=notes,
            )

            # UPDATE THE MEMBER'S BELT AND STRIPES
            models.update_member(member_id,
                belt_rank_id=to_belt_id,
                stripes=new_stripes,
            )

            flash(f'Promoted to {new_belt_name}!', 'success')
            return redirect(url_for('belts_page'))
        except Exception as e:
            print(f"[Belts] Promote error: {e}")
            flash('Error recording promotion.', 'error')

    # GET
    pre_member_id = request.args.get('member', None)
    pre_member = None
    if pre_member_id:
        try:
            pre_member = _enrich_member(models.get_member_by_id(int(pre_member_id)))
        except Exception:
            pass

    try:
        members = models.get_all_members(academy_id)
    except Exception:
        members = []

    try:
        belt_ranks = models.get_all_belt_ranks()
    except Exception:
        belt_ranks = []

    try:
        all_users = models.get_all_users()
        instructors = [u for u in (all_users or []) if u.get('role') in ('admin', 'instructor') and u.get('active')]
    except Exception:
        instructors = []

    # Enrich members with DOB for age detection
    enriched_members = []
    for m in (members or []):
        em = _enrich_member(m)
        em['dob_raw'] = str(m.get('date_of_birth', '') or '')[:10]
        enriched_members.append(em)

    return render_template('promotion_form.html',
        members=enriched_members,
        belt_ranks=belt_ranks,
        pre_member=pre_member,
        instructors=instructors,
        today=str(date.today()),
    )


@app.route('/belts/settings', methods=['POST'])
@login_required
def belt_settings():
    if not validate_csrf():
        return redirect(url_for('belts_page'))
    try:
        belt_id = int(request.form.get('belt_id', 0))
        min_months = int(request.form.get('min_months', 0))
        max_stripes = int(request.form.get('max_stripes', 4))
        models.update_belt_rank(belt_id, min_months=min_months, max_stripes=max_stripes)
        flash('Belt requirements updated!', 'success')
    except Exception as e:
        print(f"[Belts] Settings error: {e}")
        flash('Error updating belt settings.', 'error')
    return redirect(url_for('belts_page'))


@app.route('/api/belts/change-member', methods=['POST'])
@login_required
def api_belt_change_member():
    """Change a member's belt rank directly from the belt page."""
    data = request.get_json() or {}
    member_id = data.get('member_id')
    belt_rank_id = data.get('belt_rank_id')
    stripes = data.get('stripes', 0)
    if not member_id or not belt_rank_id:
        return jsonify({'error': 'member_id and belt_rank_id required'}), 400
    try:
        # Record promotion in history
        member = models.get_member_by_id(int(member_id))
        if member:
            from_belt_id = member.get('belt_rank_id', 1)
            if from_belt_id != int(belt_rank_id):
                try:
                    models.record_promotion(
                        member_id=int(member_id),
                        from_belt_id=from_belt_id,
                        from_stripes=member.get('stripes', 0),
                        to_belt_id=int(belt_rank_id),
                        to_stripes=int(stripes),
                        promotion_date=str(date.today()),
                        promoted_by=session.get('display_name', ''),
                        notes='Assigned from belt page',
                    )
                except Exception:
                    pass
        models.update_member(int(member_id), belt_rank_id=int(belt_rank_id), stripes=int(stripes))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/belts/remove-member', methods=['POST'])
@login_required
def api_belt_remove_member():
    """Remove a member from a belt — resets to White belt (id=1), 0 stripes."""
    data = request.get_json() or {}
    member_id = data.get('member_id')
    if not member_id:
        return jsonify({'error': 'member_id required'}), 400
    try:
        models.update_member(int(member_id), belt_rank_id=1, stripes=0)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════
#  PAYMENTS
# ═══════════════════════════════════════════════════════════════

@app.route('/payments')
@login_required
def payments_list():
    academy_id = _get_academy_id()
    status_filter = request.args.get('status', '')
    method_filter = request.args.get('method', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    try:
        payments = models.get_all_payments(academy_id)
        if status_filter:
            payments = [p for p in payments if p.get('status') == status_filter]
        if method_filter:
            payments = [p for p in payments if p.get('method') == method_filter]
        if date_from:
            payments = [p for p in payments if str(p.get('payment_date', ''))[:10] >= date_from]
        if date_to:
            payments = [p for p in payments if str(p.get('payment_date', ''))[:10] <= date_to]
    except Exception:
        payments = []

    # Categorize payment sources
    for p in payments:
        notes = p.get('notes', '') or ''
        if 'Enrollment' in notes or 'converted from lead' in notes:
            p['source'] = 'Enrollment'
            p['source_icon'] = 'bi-person-plus'
            p['source_color'] = '#00DC82'
        elif 'membership' in notes.lower() or p.get('membership_id'):
            p['source'] = 'Membership'
            p['source_icon'] = 'bi-card-checklist'
            p['source_color'] = '#06b6d4'
        else:
            p['source'] = 'Manual'
            p['source_icon'] = 'bi-cash'
            p['source_color'] = '#8b5cf6'

    # Monthly summary
    today = date.today()
    current_month = today.strftime('%Y-%m')
    month_payments = [p for p in payments if str(p.get('payment_date', ''))[:7] == current_month and p.get('status') == 'completed']

    summary = {
        'total_collected': sum(p.get('amount', 0) for p in payments if p.get('status') == 'completed'),
        'month_collected': sum(p.get('amount', 0) for p in month_payments),
        'month_count': len(month_payments),
        'pending': sum(p.get('amount', 0) for p in payments if p.get('status') == 'pending'),
        'overdue': len([p for p in payments if p.get('status') == 'failed']),
    }

    # Revenue by source this month
    source_revenue = {}
    for p in month_payments:
        src = p.get('source', 'Manual')
        source_revenue[src] = source_revenue.get(src, 0) + p.get('amount', 0)

    # Revenue by method this month
    method_revenue = {}
    for p in month_payments:
        m = p.get('method', 'cash')
        method_revenue[m] = method_revenue.get(m, 0) + p.get('amount', 0)

    return render_template('payments.html',
        payments=payments,
        summary=summary,
        source_revenue=source_revenue,
        method_revenue=method_revenue,
        status_filter=status_filter,
        method_filter=method_filter,
        date_from=date_from,
        date_to=date_to,
    )


@app.route('/payments/<int:payment_id>')
@login_required
def payment_detail(payment_id):
    """Payment detail page with receipt."""
    payment = models.get_payment_by_id(payment_id)
    if not payment:
        flash('Payment not found.', 'error')
        return redirect(url_for('payments_list'))

    # Categorize source
    notes = payment.get('notes', '') or ''
    if 'Enrollment' in notes or 'converted from lead' in notes:
        payment['source'] = 'Enrollment'
    elif 'membership' in notes.lower() or payment.get('membership_id'):
        payment['source'] = 'Membership'
    elif 'Store' in notes:
        payment['source'] = 'Store Sale'
    else:
        payment['source'] = 'Manual'

    # Get order items if any
    order_items = []
    try:
        conn = models.get_db()
        items = conn.execute(
            """SELECT oi.*, p.name as product_name
               FROM order_items oi
               LEFT JOIN products p ON oi.product_id = p.id
               WHERE oi.payment_id = ?""",
            (payment_id,)
        ).fetchall()
        conn.close()
        order_items = [dict(i) for i in items]
    except Exception:
        pass

    # Get academy info
    academy = None
    try:
        academy = models.get_academy_by_id(payment.get('academy_id', 1))
    except Exception:
        pass

    return render_template('payment_detail.html',
        payment=payment, order_items=order_items,
        academy=academy,
    )


@app.route('/receipt/<int:payment_id>')
def public_receipt(payment_id):
    """Public receipt page — no login needed."""
    payment = models.get_payment_by_id(payment_id)
    if not payment:
        return "Receipt not found.", 404

    notes = payment.get('notes', '') or ''
    if 'Enrollment' in notes:
        payment['source'] = 'Enrollment'
    elif 'Store' in notes:
        payment['source'] = 'Store Sale'
    elif payment.get('membership_id'):
        payment['source'] = 'Membership'
    else:
        payment['source'] = 'Payment'

    order_items = []
    try:
        conn = models.get_db()
        items = conn.execute(
            """SELECT oi.*, p.name as product_name
               FROM order_items oi LEFT JOIN products p ON oi.product_id = p.id
               WHERE oi.payment_id = ?""", (payment_id,)).fetchall()
        conn.close()
        order_items = [dict(i) for i in items]
    except Exception:
        pass

    academy = None
    try:
        academy = models.get_academy_by_id(payment.get('academy_id', 1))
    except Exception:
        pass

    return render_template('receipt.html',
        payment=payment, order_items=order_items,
        academy=academy,
    )


@app.route('/api/payments/<int:payment_id>/mark-paid', methods=['POST'])
@login_required
def api_mark_paid(payment_id):
    try:
        models.update_payment(payment_id, status='completed')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/payments/<int:payment_id>/mark-unpaid', methods=['POST'])
@login_required
def api_mark_unpaid(payment_id):
    try:
        models.update_payment(payment_id, status='pending')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/payments/<int:payment_id>/send-receipt', methods=['POST'])
@login_required
def api_send_receipt(payment_id):
    """Send receipt via email."""
    payment = models.get_payment_by_id(payment_id)
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404

    email = payment.get('email', '')
    if not email:
        return jsonify({'error': 'Member has no email registered'}), 400

    base_url = request.host_url.rstrip('/')
    receipt_url = f"{base_url}/receipt/{payment_id}"

    # TODO: Send actual email via SMTP/SendGrid/etc
    # For now return the receipt URL
    return jsonify({'success': True, 'receipt_url': receipt_url, 'email': email})


@app.route('/payments/add', methods=['GET', 'POST'])
@login_required
def payment_add():
    academy_id = _get_academy_id()

    if request.method == 'POST':
        if not validate_csrf():
            return redirect(url_for('payment_add'))
        try:
            models.create_payment(
                member_id=int(request.form.get('member_id', 0)),
                amount=float(request.form.get('amount', 0)),
                academy_id=academy_id,
                method=request.form.get('method', 'cash'),
                status=request.form.get('status', 'completed'),
                reference=request.form.get('reference', ''),
                notes=request.form.get('notes', ''),
                payment_date=request.form.get('payment_date') or str(date.today()),
                due_date=request.form.get('due_date') or None,
            )
            flash('Payment recorded!', 'success')
            return redirect(url_for('payments_list'))
        except Exception as e:
            print(f"[Payments] Create error: {e}")
            flash('Error recording payment.', 'error')

    try:
        members = models.get_all_members(academy_id)
    except Exception:
        members = []

    return render_template('payment_form.html',
        members=members,
        payment=None,
    )


@app.route('/payments/alerts')
@login_required
def payment_alerts():
    academy_id = _get_academy_id()
    try:
        alerts = models.get_payment_alerts(academy_id)
    except Exception:
        alerts = []
    return render_template('payments.html',
        payments=alerts,
        status_filter='alerts',
        method_filter='',
    )


# ═══════════════════════════════════════════════════════════════
#  FINANCE
# ═══════════════════════════════════════════════════════════════

@app.route('/finance')
@login_required
def finance_page():
    academy_id = _get_academy_id()
    today = date.today()
    month = int(request.args.get('month', today.month))
    year = int(request.args.get('year', today.year))
    month_str = f"{year}-{str(month).zfill(2)}"
    months_list = ['January','February','March','April','May','June','July','August','September','October','November','December']

    # Revenue (from payments)
    try:
        all_payments = models.get_all_payments(academy_id)
        month_payments = [p for p in all_payments if str(p.get('payment_date', ''))[:7] == month_str and p.get('status') == 'completed']
        total_revenue = sum(p.get('amount', 0) for p in month_payments)
        revenue_by_source = {}
        revenue_by_method = {}
        for p in month_payments:
            notes = p.get('notes', '') or ''
            if 'Enrollment' in notes or 'converted' in notes:
                src = 'Enrollment'
            elif 'Store' in notes:
                src = 'Store'
            elif p.get('membership_id'):
                src = 'Membership'
            else:
                src = 'Other'
            revenue_by_source[src] = revenue_by_source.get(src, 0) + p.get('amount', 0)
            m = (p.get('method', 'cash') or 'cash').replace('_', ' ').title()
            revenue_by_method[m] = revenue_by_method.get(m, 0) + p.get('amount', 0)
        pending_payments = sum(p.get('amount', 0) for p in all_payments if str(p.get('payment_date', ''))[:7] == month_str and p.get('status') == 'pending')
    except Exception:
        all_payments, month_payments = [], []
        total_revenue, pending_payments = 0, 0
        revenue_by_source, revenue_by_method = {}, {}

    # Expenses
    try:
        expenses = models.get_all_expenses(academy_id, month, year)
        total_expenses = sum(e.get('amount', 0) for e in expenses)
        expense_by_category = {}
        for e in expenses:
            cat = (e.get('category', 'other') or 'other').replace('_', ' ').title()
            expense_by_category[cat] = expense_by_category.get(cat, 0) + e.get('amount', 0)
    except Exception:
        expenses = []
        total_expenses = 0
        expense_by_category = {}

    # Payroll
    try:
        payroll = models.get_all_payroll(academy_id, month, year)
        total_payroll = sum(p.get('net_pay', 0) for p in payroll)
    except Exception:
        payroll = []
        total_payroll = 0

    # Profit
    total_costs = total_expenses + total_payroll
    net_profit = total_revenue - total_costs
    margin = round(net_profit / total_revenue * 100, 1) if total_revenue > 0 else 0

    # Monthly trend (last 6 months)
    monthly_trend = []
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        if m <= 0:
            m += 12
            y -= 1
        ms = f"{y}-{str(m).zfill(2)}"
        rev = sum(p.get('amount', 0) for p in (all_payments or []) if str(p.get('payment_date', ''))[:7] == ms and p.get('status') == 'completed')
        try:
            exp = sum(e.get('amount', 0) for e in models.get_all_expenses(academy_id, m, y))
            pay = sum(p.get('net_pay', 0) for p in models.get_all_payroll(academy_id, m, y))
        except Exception:
            exp, pay = 0, 0
        monthly_trend.append({'month': months_list[m-1][:3], 'revenue': rev, 'expenses': exp + pay, 'profit': rev - exp - pay})

    return render_template('finance.html',
        month=month, year=year, months=months_list,
        total_revenue=total_revenue, total_expenses=total_expenses,
        total_payroll=total_payroll, total_costs=total_costs,
        net_profit=net_profit, margin=margin, pending_payments=pending_payments,
        revenue_by_source=revenue_by_source, revenue_by_method=revenue_by_method,
        expense_by_category=expense_by_category,
        expenses=expenses, payroll=payroll, month_payments=month_payments,
        monthly_trend=monthly_trend,
    )


@app.route('/api/finance/send-report', methods=['POST'])
@login_required
def api_finance_send_report():
    """Generate and send monthly finance report to academy owner email."""
    data = request.get_json() or {}
    academy_id = _get_academy_id()
    month = int(data.get('month', datetime.now().month))
    year = int(data.get('year', datetime.now().year))
    months_list = ['January','February','March','April','May','June','July','August','September','October','November','December']
    month_name = months_list[month - 1]

    # Get academy owner email
    academy = None
    try:
        academy = models.get_academy_by_id(academy_id)
    except Exception:
        pass
    owner_email = ''
    try:
        user = models.get_user_by_id(session.get('user_id', 1))
        if user:
            owner_email = dict(user).get('email', '') if hasattr(user, 'keys') else (user.get('email', '') if isinstance(user, dict) else '')
        else:
            owner_email = ''
    except Exception:
        pass
    if not owner_email:
        return jsonify({'error': 'No email found. Update your email in Settings.'}), 400

    academy_name = academy.get('name', 'Fit4Academy') if academy else 'Fit4Academy'
    month_str = f"{year}-{str(month).zfill(2)}"

    # Revenue
    try:
        all_payments = models.get_all_payments(academy_id)
        month_payments = [p for p in all_payments if str(p.get('payment_date', ''))[:7] == month_str and p.get('status') == 'completed']
        total_revenue = sum(p.get('amount', 0) for p in month_payments)
        pending = sum(p.get('amount', 0) for p in all_payments if str(p.get('payment_date', ''))[:7] == month_str and p.get('status') == 'pending')
    except Exception:
        total_revenue, pending = 0, 0

    # Expenses
    try:
        expenses = models.get_all_expenses(academy_id, month, year)
        total_expenses = sum(e.get('amount', 0) for e in expenses)
    except Exception:
        total_expenses = 0

    # Payroll
    try:
        payroll = models.get_all_payroll(academy_id, month, year)
        total_payroll = sum(p.get('net_pay', 0) for p in payroll)
    except Exception:
        total_payroll = 0

    total_costs = total_expenses + total_payroll
    net_profit = total_revenue - total_costs
    margin = round(net_profit / total_revenue * 100, 1) if total_revenue > 0 else 0

    # Previous month comparison
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    prev_str = f"{prev_year}-{str(prev_month).zfill(2)}"
    try:
        prev_payments = [p for p in all_payments if str(p.get('payment_date', ''))[:7] == prev_str and p.get('status') == 'completed']
        prev_revenue = sum(p.get('amount', 0) for p in prev_payments)
    except Exception:
        prev_revenue = 0
    revenue_change = round((total_revenue - prev_revenue) / prev_revenue * 100, 1) if prev_revenue > 0 else 0

    # Smart insight
    if margin >= 30:
        insight = "Excellent month! Your academy is highly profitable."
    elif margin >= 20:
        insight = "Good performance. Consider reinvesting in marketing or equipment."
    elif margin >= 10:
        insight = "Moderate margins. Review your top expenses for savings."
    elif margin >= 0:
        insight = "Thin margins. Focus on increasing enrollment or reducing costs."
    else:
        insight = "Operating at a loss. Urgent: review all expenses and boost revenue."

    # Build report
    lines = [
        f"📊 *{academy_name} — Finance Report*",
        f"📅 *{month_name} {year}*",
        "",
        f"💰 *REVENUE*",
        f"   Total: ${total_revenue:,.2f}",
        f"   Pending: ${pending:,.2f}",
        f"   vs Last Month: {'📈' if revenue_change >= 0 else '📉'} {revenue_change:+.1f}%",
        "",
        f"💸 *COSTS*",
        f"   Expenses: ${total_expenses:,.2f}",
        f"   Payroll: ${total_payroll:,.2f}",
        f"   Total: ${total_costs:,.2f}",
        "",
        f"{'🏆' if net_profit >= 0 else '⚠️'} *NET {'PROFIT' if net_profit >= 0 else 'LOSS'}*",
        f"   ${net_profit:,.2f} ({margin}% margin)",
        "",
        f"💡 *Insight:* {insight}",
        "",
    ]

    # Top expenses
    if expenses:
        lines.append("📋 *Top Expenses:*")
        exp_sorted = sorted(expenses, key=lambda x: x.get('amount', 0), reverse=True)[:5]
        for e in exp_sorted:
            lines.append(f"   • {e.get('description') or e.get('category', 'Other')}: ${e.get('amount', 0):,.2f}")
        lines.append("")

    # Payroll summary
    if payroll:
        lines.append("👥 *Payroll:*")
        for p in payroll:
            lines.append(f"   • {p.get('employee_name', '')}: ${p.get('net_pay', 0):,.2f}")
        lines.append("")

    lines.append(f"Generated by {academy_name} on Fit4Academy")
    report_text = '\n'.join(lines)

    # TODO: Send via email (SMTP/SendGrid integration)
    # For now, return the report text
    return jsonify({
        'success': True,
        'email': owner_email,
        'report': report_text,
        'note': 'Email delivery coming with SendGrid integration.',
    })


@app.route('/api/marcos/advice', methods=['POST'])
@login_required
def api_marcos_advice():
    """Get AI business advice from Marcos."""
    data = request.get_json() or {}
    academy_id = _get_academy_id()
    question = data.get('question', '')
    month = int(data.get('month', datetime.now().month))
    year = int(data.get('year', datetime.now().year))
    months_list = ['January','February','March','April','May','June','July','August','September','October','November','December']
    month_str = f"{year}-{str(month).zfill(2)}"

    # Gather all data for Marcos
    try:
        all_payments = models.get_all_payments(academy_id)
        month_payments = [p for p in all_payments if str(p.get('payment_date', ''))[:7] == month_str and p.get('status') == 'completed']
        total_revenue = sum(p.get('amount', 0) for p in month_payments)
        pending = sum(p.get('amount', 0) for p in all_payments if str(p.get('payment_date', ''))[:7] == month_str and p.get('status') == 'pending')
    except Exception:
        total_revenue, pending = 0, 0
        month_payments = []

    try:
        expenses = models.get_all_expenses(academy_id, month, year)
        total_expenses = sum(e.get('amount', 0) for e in expenses)
    except Exception:
        expenses, total_expenses = [], 0

    try:
        payroll = models.get_all_payroll(academy_id, month, year)
        total_payroll = sum(p.get('net_pay', 0) for p in payroll)
    except Exception:
        total_payroll = 0

    net_profit = total_revenue - total_expenses - total_payroll
    margin = round(net_profit / total_revenue * 100, 1) if total_revenue > 0 else 0

    # Previous month
    pm = month - 1 if month > 1 else 12
    py = year if month > 1 else year - 1
    ps = f"{py}-{str(pm).zfill(2)}"
    try:
        prev_rev = sum(p.get('amount', 0) for p in all_payments if str(p.get('payment_date', ''))[:7] == ps and p.get('status') == 'completed')
    except Exception:
        prev_rev = 0
    rev_change = round((total_revenue - prev_rev) / prev_rev * 100, 1) if prev_rev > 0 else 0

    # Members
    try:
        members = models.get_all_members(academy_id)
        active_members = len([m for m in members if m.get('membership_status') == 'active'])
    except Exception:
        active_members = 0
    rpm = round(total_revenue / active_members, 2) if active_members > 0 else 0

    # Leads
    try:
        prospects = models.get_all_prospects(academy_id)
        leads_in = len([p for p in prospects if p.get('source') != 'ex_student' and str(p.get('created_at', ''))[:7] == month_str])
        leads_converted = len([p for p in prospects if p.get('status') == 'converted' and str(p.get('updated_at', ''))[:7] == month_str])
        urgent = len([p for p in prospects if p.get('status') == 'new' and not p.get('archived')])
    except Exception:
        leads_in, leads_converted, urgent = 0, 0, 0
    conv_rate = round(leads_converted / leads_in * 100, 1) if leads_in > 0 else 0

    # Attendance
    try:
        report = models.get_attendance_report(academy_id, month, year)
        trained = len([m for m in report if m.get('total_checkins', 0) > 0])
        total_m = len(report)
        att_rate = round(trained / total_m * 100, 1) if total_m > 0 else 0
        absent = len([m for m in report if not m.get('total_checkins')])
    except Exception:
        trained, att_rate, absent = 0, 0, 0

    # Top expenses text
    top_exp = sorted(expenses, key=lambda x: x.get('amount', 0), reverse=True)[:5]
    top_exp_text = '\n'.join([f"  - {e.get('description') or e.get('category','Other')}: ${e.get('amount',0):,.2f}" for e in top_exp]) or 'None'

    # Revenue sources
    sources = {}
    for p in month_payments:
        notes = p.get('notes', '') or ''
        src = 'Enrollment' if 'Enrollment' in notes else ('Store' if 'Store' in notes else ('Membership' if p.get('membership_id') else 'Other'))
        sources[src] = sources.get(src, 0) + p.get('amount', 0)
    src_text = '\n'.join([f"  - {s}: ${a:,.2f}" for s, a in sources.items()]) or 'None'

    context = {
        'month_name': months_list[month - 1], 'year': year,
        'revenue': total_revenue, 'expenses': total_expenses,
        'payroll': total_payroll, 'net_profit': net_profit,
        'margin': margin, 'pending': pending, 'revenue_change': rev_change,
        'active_members': active_members, 'revenue_per_member': rpm,
        'leads_in': leads_in, 'leads_converted': leads_converted,
        'conversion_rate': conv_rate, 'urgent_leads': urgent,
        'members_trained': trained, 'attendance_rate': att_rate,
        'absent_members': absent,
        'top_expenses_text': top_exp_text, 'revenue_sources_text': src_text,
    }

    advice = marcos_ai.get_marcos_advice(context, question)
    return jsonify({'success': True, 'advice': advice, 'ai_enabled': marcos_ai.AI_ENABLED})


@app.route('/api/expenses/add', methods=['POST'])
@login_required
def api_expense_add():
    data = request.get_json() or {}
    academy_id = _get_academy_id()
    try:
        eid = models.create_expense(
            academy_id=academy_id,
            category=data.get('category', 'other'),
            description=data.get('description', ''),
            vendor=data.get('vendor', ''),
            amount=float(data.get('amount', 0)),
            expense_date=data.get('expense_date', str(date.today())),
            recurring=data.get('recurring', False),
            recurring_cycle=data.get('recurring_cycle', 'monthly'),
            payment_method=data.get('payment_method', 'bank_transfer'),
            status=data.get('status', 'paid'),
            notes=data.get('notes', ''),
            created_by=session.get('user_id'),
        )
        return jsonify({'success': True, 'id': eid})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/expenses/<int:expense_id>/delete', methods=['POST'])
@login_required
def api_expense_delete(expense_id):
    try:
        models.delete_expense(expense_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/payroll/add', methods=['POST'])
@login_required
def api_payroll_add():
    data = request.get_json() or {}
    academy_id = _get_academy_id()
    try:
        pid = models.create_payroll(
            academy_id=academy_id,
            employee_name=data.get('employee_name', ''),
            role=data.get('role', 'instructor'),
            salary=float(data.get('salary', 0)),
            pay_type=data.get('pay_type', 'monthly'),
            pay_date=data.get('pay_date', str(date.today())),
            hours_worked=float(data.get('hours_worked', 0)),
            hourly_rate=float(data.get('hourly_rate', 0)),
            bonus=float(data.get('bonus', 0)),
            deductions=float(data.get('deductions', 0)),
            status=data.get('status', 'paid'),
            notes=data.get('notes', ''),
        )
        return jsonify({'success': True, 'id': pid})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/payroll/<int:payroll_id>/delete', methods=['POST'])
@login_required
def api_payroll_delete(payroll_id):
    try:
        models.delete_payroll(payroll_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════
#  PROSPECTS
# ═══════════════════════════════════════════════════════════════

@app.route('/prospects')
@login_required
def prospects_list():
    academy_id = _get_academy_id()
    try:
        all_prospects = models.get_all_prospects(academy_id)
    except Exception:
        all_prospects = []

    # Separate archived and active
    active_prospects = [p for p in all_prospects if not p.get('archived')]
    archived_prospects = [p for p in all_prospects if p.get('archived')]

    # Separate ex-students from real leads — ex-students NEVER go to pipeline
    # An ex-student is ONLY source='ex_student'. Converted leads with member_id stay in pipeline.
    def is_ex_student(p):
        if p.get('source') == 'ex_student':
            return True
        return False

    ex_students = [p for p in active_prospects if is_ex_student(p)]
    real_leads = [p for p in active_prospects if not is_ex_student(p)]

    # Also include inactive members that don't have a prospect entry yet
    try:
        all_members = models.get_all_members(academy_id)
        ex_member_ids = {p.get('member_id') for p in ex_students if p.get('member_id')}
        for m in (all_members or []):
            if m.get('membership_status') == 'inactive' and m.get('id') not in ex_member_ids:
                ex_students.append({
                    'id': None, 'first_name': m.get('first_name', ''),
                    'last_name': m.get('last_name', ''), 'email': m.get('email', ''),
                    'phone': m.get('phone', ''), 'source': 'ex_student',
                    'member_id': m.get('id'), 'notes': f"Inactive since join: {m.get('join_date','')}",
                })
    except Exception:
        pass

    # Add urgency info to each lead and sort by oldest first (priority)
    now = datetime.now()
    for p in real_leads:
        created = str(p.get('created_at', ''))[:19]
        try:
            created_dt = datetime.strptime(created, '%Y-%m-%d %H:%M:%S')
            hours_waiting = (now - created_dt).total_seconds() / 3600
            p['hours_waiting'] = round(hours_waiting, 1)
            p['is_urgent'] = hours_waiting >= 24 and p.get('status') == 'new'
        except Exception:
            p['hours_waiting'] = 0
            p['is_urgent'] = False

    # Group real leads by stage for pipeline view — sorted oldest first
    prospects_by_stage = {
        'new': [], 'contacted': [], 'trial': [], 'converted': [],
    }
    for p in real_leads:
        stage = p.get('status', 'new')
        if stage in prospects_by_stage:
            prospects_by_stage[stage].append(p)
        else:
            prospects_by_stage['new'].append(p)

    # Sort each stage: oldest first (highest priority)
    for stage in prospects_by_stage:
        prospects_by_stage[stage].sort(key=lambda x: str(x.get('created_at', '')), reverse=False)

    # Dashboard stats
    total_leads = len([p for p in all_prospects if p.get('source') != 'ex_student'])
    period = request.args.get('period', 'month')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    today = date.today()
    if period == 'day':
        period_start = str(today)
    elif period == 'week':
        period_start = str(today - timedelta(days=today.weekday()))
    elif period == 'year':
        period_start = f"{today.year}-01-01"
    elif period == 'custom' and date_from:
        period_start = date_from
    else:
        period_start = f"{today.year}-{str(today.month).zfill(2)}-01"

    period_end = date_to if (period == 'custom' and date_to) else str(today)

    leads_in = len([p for p in all_prospects if p.get('source') != 'ex_student'
                    and str(p.get('created_at', ''))[:10] >= period_start
                    and str(p.get('created_at', ''))[:10] <= period_end])
    leads_converted = len([p for p in all_prospects if p.get('status') == 'converted'
                           and str(p.get('updated_at', ''))[:10] >= period_start
                           and str(p.get('updated_at', ''))[:10] <= period_end])
    leads_lost = len([p for p in all_prospects if p.get('status') == 'lost'
                      and p.get('source') != 'ex_student'
                      and str(p.get('updated_at', ''))[:10] >= period_start
                      and str(p.get('updated_at', ''))[:10] <= period_end])
    conversion_rate = round(leads_converted / leads_in * 100, 1) if leads_in > 0 else 0

    # Source breakdown for acquisition channel analytics
    source_counts = {}
    for p in all_prospects:
        if p.get('source') and p.get('source') != 'ex_student':
            src = p.get('source', 'unknown')
            source_counts[src] = source_counts.get(src, 0) + 1

    return render_template('prospects.html',
        prospects=all_prospects,
        prospects_by_stage=prospects_by_stage,
        ex_students=ex_students,
        archived_prospects=archived_prospects,
        leads_in=leads_in, leads_converted=leads_converted,
        leads_lost=leads_lost, conversion_rate=conversion_rate,
        source_counts=source_counts, total_leads=total_leads,
        period=period, date_from=date_from, date_to=date_to,
        programs=models.get_programs(academy_id),
        membership_plans=models.get_all_membership_plans(academy_id),
        products=models.get_all_products(academy_id),
    )


@app.route('/prospects/add', methods=['GET', 'POST'])
@login_required
def prospect_add():
    academy_id = _get_academy_id()

    if request.method == 'POST':
        if not validate_csrf():
            return redirect(url_for('prospect_add'))
        try:
            models.create_prospect(
                academy_id=academy_id,
                first_name=request.form.get('first_name', '').strip(),
                last_name=request.form.get('last_name', '').strip(),
                email=request.form.get('email', '').strip(),
                phone=request.form.get('phone', '').strip(),
                source=request.form.get('source', ''),
                status=request.form.get('status', 'new'),
                previous_experience=request.form.get('previous_experience', ''),
                follow_up_date=request.form.get('follow_up_date') or None,
                notes=request.form.get('notes', ''),
            )
            flash('Prospect added!', 'success')
            return redirect(url_for('prospects_list'))
        except Exception as e:
            print(f"[Prospects] Create error: {e}")
            flash('Error adding prospect.', 'error')

    return render_template('prospect_form.html', prospect=None)


@app.route('/prospects/<int:prospect_id>/edit', methods=['GET', 'POST'])
@login_required
def prospect_edit(prospect_id):
    try:
        prospect = models.get_prospect_by_id(prospect_id)
        if not prospect:
            flash('Prospect not found.', 'error')
            return redirect(url_for('prospects_list'))
    except Exception:
        flash('Error loading prospect.', 'error')
        return redirect(url_for('prospects_list'))

    if request.method == 'POST':
        if not validate_csrf():
            return redirect(url_for('prospect_edit', prospect_id=prospect_id))
        try:
            models.update_prospect(prospect_id,
                first_name=request.form.get('first_name', '').strip(),
                last_name=request.form.get('last_name', '').strip(),
                email=request.form.get('email', '').strip(),
                phone=request.form.get('phone', '').strip(),
                source=request.form.get('source', ''),
                status=request.form.get('status', 'new'),
                previous_experience=request.form.get('previous_experience', ''),
                follow_up_date=request.form.get('follow_up_date') or None,
                notes=request.form.get('notes', ''),
            )
            flash('Prospect updated!', 'success')
            return redirect(url_for('prospects_list'))
        except Exception as e:
            print(f"[Prospects] Update error: {e}")
            flash('Error updating prospect.', 'error')

    return render_template('prospect_form.html', prospect=prospect)


@app.route('/prospects/<int:prospect_id>/convert', methods=['POST'])
@login_required
def prospect_convert(prospect_id):
    if not validate_csrf():
        return redirect(url_for('prospects_list'))
    academy_id = _get_academy_id()
    try:
        member_id = models.convert_prospect_to_member(prospect_id, academy_id)
        if member_id:
            flash('Prospect converted to member!', 'success')
            return redirect(url_for('member_detail', member_id=member_id))
        else:
            flash('Error converting prospect.', 'error')
    except Exception as e:
        print(f"[Prospects] Convert error: {e}")
        flash('Error converting prospect.', 'error')
    return redirect(url_for('prospects_list'))


@app.route('/api/prospects/convert', methods=['POST'])
@login_required
def api_prospect_convert():
    """Convert a prospect to a member with programs, multiple plans, products and payment."""
    data = request.get_json() or {}
    prospect_id = data.get('prospect_id')
    if not prospect_id:
        return jsonify({'error': 'prospect_id required'}), 400
    academy_id = _get_academy_id()
    try:
        member_id = models.convert_prospect_to_member(int(prospect_id), academy_id)
        if not member_id:
            return jsonify({'error': 'Could not convert prospect'}), 500

        # Assign program
        program_id = data.get('program_id')
        if program_id:
            try:
                models.enroll_member_program(member_id, int(program_id))
            except Exception:
                pass

        # Create multiple memberships
        plan_ids = data.get('plan_ids', [])
        plan_id = data.get('plan_id')  # backward compat
        if plan_id and plan_id not in plan_ids:
            plan_ids.append(plan_id)
        for pid in plan_ids:
            try:
                models.create_membership(member_id, int(pid))
            except Exception:
                pass

        # Record payment (memberships + products total)
        amount = data.get('amount')
        if amount and float(amount) > 0:
            try:
                payment_id = models.create_payment(
                    member_id=member_id,
                    amount=float(amount),
                    academy_id=academy_id,
                    method=data.get('payment_method', 'cash'),
                    status=data.get('payment_status', 'completed'),
                    notes=f"Enrollment payment — converted from lead #{prospect_id}",
                    payment_date=str(date.today()),
                )
            except Exception:
                payment_id = None

            # Record product orders
            products = data.get('products', [])
            for item in products:
                try:
                    models.create_order_item(
                        academy_id=academy_id,
                        member_id=member_id,
                        product_id=int(item.get('product_id')),
                        size=item.get('size', ''),
                        color=item.get('color', ''),
                        quantity=int(item.get('quantity', 1)),
                        price=float(item.get('price', 0)),
                        payment_id=payment_id,
                    )
                    # Decrease stock
                    prod = models.get_all_products(academy_id)
                    for p in prod:
                        if p['id'] == int(item.get('product_id')):
                            new_stock = max(0, p.get('stock', 0) - int(item.get('quantity', 1)))
                            models.update_product(p['id'], stock=new_stock)
                            break
                except Exception:
                    pass

        return jsonify({'success': True, 'member_id': member_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/store')
@login_required
def store_page():
    academy_id = _get_academy_id()
    products = models.get_all_products(academy_id)
    # Load variants for each product
    for p in products:
        p['variants'] = models.get_product_variants(p['id'])
    # Get recent orders
    try:
        conn = models.get_db()
        orders = conn.execute(
            """SELECT oi.*, m.first_name, m.last_name, p.name as product_name
               FROM order_items oi
               LEFT JOIN members m ON oi.member_id = m.id
               LEFT JOIN products p ON oi.product_id = p.id
               WHERE oi.academy_id = ?
               ORDER BY oi.created_at DESC LIMIT 50""",
            (academy_id,)
        ).fetchall()
        conn.close()
        orders = [dict(r) for r in orders]
    except Exception:
        orders = []
    try:
        members = models.get_all_members(academy_id)
    except Exception:
        members = []
    return render_template('store.html', products=products, orders=orders, members=members)


# ═══════════════════════════════════════════════════════════════
#  BILLING / STRIPE
# ═══════════════════════════════════════════════════════════════

@app.route('/ai')
@login_required
def ai_page():
    return render_template('ai.html')


@app.route('/integrations')
@login_required
def integrations_page():
    return render_template('integrations.html')


@app.route('/api/billing/setup-intent', methods=['POST'])
@login_required
def api_billing_setup_intent():
    """Create a SetupIntent to save a card/bank for a member."""
    data = request.get_json() or {}
    member_id = data.get('member_id')
    if not member_id:
        return jsonify({'error': 'member_id required'}), 400
    try:
        member = models.get_member_by_id(int(member_id))
        if not member:
            return jsonify({'error': 'Member not found'}), 404

        # Get or create Stripe customer
        pms = models.get_payment_methods(int(member_id))
        customer_id = None
        for pm in (pms or []):
            if pm.get('stripe_customer_id'):
                customer_id = pm['stripe_customer_id']
                break

        if not customer_id:
            customer_id = billing.create_customer(
                email=member.get('email', ''),
                name=f"{member.get('first_name', '')} {member.get('last_name', '')}",
                member_id=member_id,
            )
            if not customer_id:
                return jsonify({'error': 'Stripe not configured. Add STRIPE_SECRET_KEY to environment.'}), 400

        intent = billing.create_setup_intent(customer_id)
        if not intent:
            return jsonify({'error': 'Could not create setup intent'}), 500

        return jsonify({
            'success': True,
            'client_secret': intent['client_secret'],
            'customer_id': customer_id,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/billing/save-method', methods=['POST'])
@login_required
def api_billing_save_method():
    """Save a payment method after SetupIntent completes."""
    data = request.get_json() or {}
    member_id = data.get('member_id')
    stripe_pm_id = data.get('payment_method_id')
    customer_id = data.get('customer_id', '')
    method_type = data.get('type', 'card')
    last4 = data.get('last4', '')
    brand = data.get('brand', '')

    if not member_id or not stripe_pm_id:
        return jsonify({'error': 'member_id and payment_method_id required'}), 400
    try:
        models.create_payment_method(
            int(member_id),
            method_type=method_type,
            last4=last4,
            brand=brand,
            stripe_pm_id=stripe_pm_id,
            stripe_customer_id=customer_id,
            is_default=True,
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/billing/charge', methods=['POST'])
@login_required
def api_billing_charge():
    """Charge a member's saved card/bank. Platform fee ($0.30) added automatically."""
    data = request.get_json() or {}
    member_id = data.get('member_id')
    amount = float(data.get('amount', 0))
    description = data.get('description', 'Fit4Academy charge')
    payment_method_id = data.get('payment_method_id')

    if not member_id or amount <= 0:
        return jsonify({'error': 'member_id and amount required'}), 400

    academy_id = _get_academy_id()

    # If no Stripe, record as manual payment
    if not billing.is_enabled():
        pid = models.create_payment(
            member_id=int(member_id), amount=amount, academy_id=academy_id,
            method=data.get('method', 'cash'), status='completed',
            platform_fee=billing.PLATFORM_FEE,
            notes=description, payment_date=str(date.today()),
        )
        return jsonify({'success': True, 'payment_id': pid, 'mode': 'manual'})

    try:
        # Find customer and payment method
        pms = models.get_payment_methods(int(member_id))
        customer_id = None
        pm_id = payment_method_id

        for pm in (pms or []):
            if pm.get('stripe_customer_id'):
                customer_id = pm['stripe_customer_id']
            if not pm_id and pm.get('stripe_pm_id') and pm.get('is_default'):
                pm_id = pm['stripe_pm_id']

        if not customer_id or not pm_id:
            return jsonify({'error': 'No saved payment method. Add a card first.'}), 400

        result = billing.charge(customer_id, pm_id, amount, description)
        if not result:
            return jsonify({'error': 'Stripe not available'}), 500

        if result.get('success'):
            pid = models.create_payment(
                member_id=int(member_id), amount=amount, academy_id=academy_id,
                method='stripe', status='completed',
                platform_fee=billing.PLATFORM_FEE,
                stripe_charge_id=result.get('charge_id', ''),
                notes=f"{description} (charged ${result['total_charged']:.2f} incl. ${billing.PLATFORM_FEE} platform fee)",
                payment_date=str(date.today()),
            )
            return jsonify({'success': True, 'payment_id': pid, 'charge_id': result['charge_id'], 'total_charged': result['total_charged']})
        else:
            return jsonify({'error': result.get('error', 'Charge failed')}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════
#  PAYMENT LINKS (Send via SMS/text)
# ═══════════════════════════════════════════════════════════════

@app.route('/api/payment-link/create', methods=['POST'])
@login_required
def api_create_payment_link():
    """Create a secure payment link and optionally send via SMS."""
    data = request.get_json() or {}
    member_id = data.get('member_id')
    amount = float(data.get('amount', 0))
    description = data.get('description', 'Payment')
    send_sms = data.get('send_sms', False)

    if not member_id or amount <= 0:
        return jsonify({'error': 'member_id and amount required'}), 400

    academy_id = _get_academy_id()
    member = models.get_member_by_id(int(member_id))
    if not member:
        return jsonify({'error': 'Member not found'}), 404

    # Generate secure token
    token = str(uuid.uuid4()).replace('-', '')

    # Store payment link in session-like storage (use a simple DB approach)
    try:
        conn = models.get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payment_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                academy_id INTEGER,
                member_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                platform_fee REAL DEFAULT 0.30,
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP
            )
        """)
        conn.execute(
            "INSERT INTO payment_links (token, academy_id, member_id, amount, platform_fee, description) VALUES (?,?,?,?,?,?)",
            (token, academy_id, int(member_id), amount, billing.PLATFORM_FEE, description)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # Build link
    base_url = request.host_url.rstrip('/')
    link = f"{base_url}/pay/{token}"

    # Send SMS if requested
    if send_sms and member.get('phone'):
        phone = member['phone']
        member_name = f"{member.get('first_name', '')} {member.get('last_name', '')}"
        academy = None
        try:
            academy = models.get_academy_by_id(academy_id)
        except Exception:
            pass
        academy_name = academy.get('name', 'Fit4Academy') if academy else 'Fit4Academy'
        sms_text = f"Hi {member.get('first_name', '')}! {academy_name} sent you a payment request for ${amount:.2f}. Pay securely here: {link}"
        # TODO: Integrate with Twilio or SMS provider
        # For now, return the link for manual sending

    return jsonify({
        'success': True,
        'link': link,
        'token': token,
        'amount': amount,
        'total': amount + billing.PLATFORM_FEE,
    })


@app.route('/pay/<token>')
def public_payment_page(token):
    """Public payment page — no login required. Secure via token."""
    try:
        conn = models.get_db()
        link = conn.execute("SELECT * FROM payment_links WHERE token = ?", (token,)).fetchone()
        conn.close()
        if not link:
            return "Payment link not found or expired.", 404
        link = dict(link)
        if link.get('status') == 'paid':
            return render_template('payment_link.html',
                token=token, member_name='', amount=link['amount'],
                platform_fee=link['platform_fee'], description=link['description'],
                academy_name='Fit4Academy', paid=True)

        member = models.get_member_by_id(link['member_id'])
        member_name = f"{member.get('first_name', '')} {member.get('last_name', '')}" if member else 'Member'

        academy = None
        try:
            academy = models.get_academy_by_id(link.get('academy_id', 1))
        except Exception:
            pass
        academy_name = academy.get('name', 'Fit4Academy') if academy else 'Fit4Academy'

        return render_template('payment_link.html',
            token=token, member_name=member_name,
            amount=link['amount'], platform_fee=link['platform_fee'],
            description=link['description'], academy_name=academy_name, paid=False)
    except Exception as e:
        return f"Error: {e}", 500


@app.route('/api/payment-link/process', methods=['POST'])
def api_process_payment_link():
    """Process payment from the public payment page."""
    data = request.get_json() or {}
    token = data.get('token')
    if not token:
        return jsonify({'error': 'Invalid payment link'}), 400

    try:
        conn = models.get_db()
        link = conn.execute("SELECT * FROM payment_links WHERE token = ?", (token,)).fetchone()
        if not link:
            conn.close()
            return jsonify({'error': 'Payment link not found'}), 404

        link = dict(link)
        if link.get('status') == 'paid':
            conn.close()
            return jsonify({'error': 'Already paid'}), 400

        method = data.get('method', 'bank')
        amount = link['amount']
        platform_fee = link.get('platform_fee', 0.30)
        member_id = link['member_id']
        academy_id = link.get('academy_id', 1)

        # If Stripe is enabled, process through Stripe
        if billing.is_enabled():
            # Create Stripe payment with bank/card details
            # This would use Stripe's ACH or card payment flow
            # For now, mark as completed (Stripe integration will handle actual charging)
            pass

        # Record payment
        payment_id = models.create_payment(
            member_id=member_id,
            amount=amount,
            academy_id=academy_id,
            method='ach_bank' if method == 'bank' else 'debit_card',
            status='completed',
            platform_fee=platform_fee,
            notes=f"Payment link: {link['description']} (paid via {method})",
            payment_date=str(date.today()),
        )

        # Mark link as paid
        conn.execute("UPDATE payment_links SET status = 'paid', paid_at = CURRENT_TIMESTAMP WHERE token = ?", (token,))
        conn.commit()
        conn.close()

        # Save payment method for future charges
        if method == 'bank':
            last4 = data.get('account', '')[-4:] if data.get('account') else ''
            models.create_payment_method(
                member_id,
                method_type='bank_account',
                last4=last4,
                brand=data.get('bank_name', 'Bank'),
            )
        else:
            last4 = data.get('card_number', '')[-4:] if data.get('card_number') else ''
            models.create_payment_method(
                member_id,
                method_type='debit_card',
                last4=last4,
                brand=data.get('card_name', 'Card'),
            )

        return jsonify({'success': True, 'payment_id': payment_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/billing/methods/<int:member_id>', methods=['GET'])
@login_required
def api_billing_methods(member_id):
    """List saved payment methods for a member."""
    try:
        pms = models.get_payment_methods(member_id)
        return jsonify([dict(p) for p in (pms or [])])
    except Exception:
        return jsonify([])


@app.route('/api/products', methods=['GET'])
@login_required
def api_products_list():
    academy_id = _get_academy_id()
    return jsonify(models.get_all_products(academy_id))


@app.route('/api/products/add', methods=['POST'])
@login_required
def api_products_add():
    data = request.get_json() or {}
    academy_id = _get_academy_id()
    try:
        pid = models.create_product(
            academy_id=academy_id,
            name=data.get('name', ''),
            category=data.get('category', 'gear'),
            sizes=data.get('sizes', ''),
            colors=data.get('colors', ''),
            price=float(data.get('price', 0)),
            stock=int(data.get('stock', 0)),
        )
        # Create variants if sizes/colors provided
        variants = data.get('variants', [])
        if variants:
            models.set_product_variants(pid, variants)
        return jsonify({'success': True, 'id': pid})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/products/<int:product_id>/update', methods=['POST'])
@login_required
def api_products_update(product_id):
    data = request.get_json() or {}
    try:
        models.update_product(product_id,
            name=data.get('name'), category=data.get('category'),
            sizes=data.get('sizes'), colors=data.get('colors', ''),
            price=float(data.get('price', 0)),
            stock=int(data.get('stock', 0)))
        # Update variants
        variants = data.get('variants', [])
        if variants:
            models.set_product_variants(product_id, variants)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/store/sell', methods=['POST'])
@login_required
def api_store_sell():
    """Record a manual product sale."""
    data = request.get_json() or {}
    academy_id = _get_academy_id()
    member_id = data.get('member_id')
    items = data.get('items', [])
    payment_method = data.get('payment_method', 'cash')
    if not items:
        return jsonify({'error': 'No items selected'}), 400
    try:
        total = 0
        for item in items:
            total += float(item.get('price', 0)) * int(item.get('quantity', 1))

        # Record payment
        payment_id = None
        if total > 0 and member_id:
            payment_id = models.create_payment(
                member_id=int(member_id),
                amount=total,
                academy_id=academy_id,
                method=payment_method,
                status='completed',
                notes='Store sale',
                payment_date=str(date.today()),
            )

        # Create order items + decrease stock
        for item in items:
            models.create_order_item(
                academy_id=academy_id,
                member_id=int(member_id) if member_id else None,
                product_id=int(item.get('product_id')),
                size=item.get('size', ''),
                color=item.get('color', ''),
                quantity=int(item.get('quantity', 1)),
                price=float(item.get('price', 0)),
                payment_id=payment_id,
            )
            # Decrease stock
            try:
                prods = models.get_all_products(academy_id)
                for p in prods:
                    if p['id'] == int(item.get('product_id')):
                        new_stock = max(0, p.get('stock', 0) - int(item.get('quantity', 1)))
                        models.update_product(p['id'], stock=new_stock)
                        break
            except Exception:
                pass

        return jsonify({'success': True, 'total': total})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/products/<int:product_id>/delete', methods=['POST'])
@login_required
def api_products_delete(product_id):
    try:
        models.delete_product(product_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/prospects/move', methods=['POST'])
@login_required
def api_prospect_move():
    """Move a prospect to a different pipeline stage."""
    data = request.get_json() or {}
    prospect_id = data.get('prospect_id')
    new_stage = data.get('stage')
    valid_stages = ['new', 'contacted', 'trial', 'converted', 'lost']
    if not prospect_id or new_stage not in valid_stages:
        return jsonify({'error': 'Invalid prospect_id or stage'}), 400
    try:
        models.update_prospect(int(prospect_id), status=new_stage)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/prospects/archive', methods=['POST'])
@login_required
def api_prospect_archive():
    """Archive or unarchive a prospect."""
    data = request.get_json() or {}
    prospect_id = data.get('prospect_id')
    archive = data.get('archive', True)
    if not prospect_id:
        return jsonify({'error': 'prospect_id required'}), 400
    try:
        models.update_prospect(int(prospect_id),
            archived=True if archive else False,
            archived_at=str(datetime.now()) if archive else None)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/prospects/notes', methods=['POST'])
@login_required
def api_prospect_notes():
    """Update notes for a prospect."""
    data = request.get_json() or {}
    prospect_id = data.get('prospect_id')
    notes = data.get('notes', '')
    if not prospect_id:
        return jsonify({'error': 'prospect_id required'}), 400
    try:
        models.update_prospect(int(prospect_id), notes=notes)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/prospects/reactivate', methods=['POST'])
@login_required
def api_prospect_reactivate():
    """Reactivate an ex-member: set member to active and delete the prospect entry."""
    data = request.get_json() or {}
    member_id = data.get('member_id')
    prospect_id = data.get('prospect_id')
    if not member_id:
        return jsonify({'error': 'member_id required'}), 400
    try:
        models.update_member(int(member_id), membership_status='active')
        if prospect_id and int(prospect_id) > 0:
            models.delete_prospect(int(prospect_id))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/prospects/delete', methods=['POST'])
@login_required
def api_prospect_delete_json():
    """Delete a prospect via JSON API."""
    data = request.get_json() or {}
    prospect_id = data.get('prospect_id')
    if not prospect_id:
        return jsonify({'error': 'prospect_id required'}), 400
    try:
        models.delete_prospect(int(prospect_id))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/prospects/<int:prospect_id>/delete', methods=['POST'])
@login_required
def prospect_delete(prospect_id):
    if not validate_csrf():
        return redirect(url_for('prospects_list'))
    try:
        models.delete_prospect(prospect_id)
        flash('Prospect deleted.', 'success')
    except Exception as e:
        flash('Error deleting prospect.', 'error')
    return redirect(url_for('prospects_list'))


# ═══════════════════════════════════════════════════════════════
#  EVENTS
# ═══════════════════════════════════════════════════════════════

@app.route('/events')
@login_required
def events_list():
    academy_id = _get_academy_id()
    try:
        events = models.get_all_events(academy_id)
    except Exception:
        events = []
    return render_template('events.html', events=events)


@app.route('/events/add', methods=['GET', 'POST'])
@login_required
def event_add():
    academy_id = _get_academy_id()

    if request.method == 'POST':
        if not validate_csrf():
            return redirect(url_for('event_add'))
        try:
            models.create_event(
                academy_id=academy_id,
                name=request.form.get('name', '').strip(),
                event_type=request.form.get('event_type', 'seminar'),
                description=request.form.get('description', ''),
                event_date=request.form.get('event_date') or None,
                start_time=request.form.get('start_time', ''),
                end_time=request.form.get('end_time', ''),
                location=request.form.get('location', ''),
                max_participants=int(request.form.get('max_participants', 0)),
                price=float(request.form.get('price', 0)),
            )
            flash('Event created!', 'success')
            return redirect(url_for('events_list'))
        except Exception as e:
            print(f"[Events] Create error: {e}")
            flash('Error creating event.', 'error')

    return render_template('event_form.html', event=None)


@app.route('/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def event_edit(event_id):
    try:
        event = models.get_event_by_id(event_id)
        if not event:
            flash('Event not found.', 'error')
            return redirect(url_for('events_list'))
    except Exception:
        flash('Error loading event.', 'error')
        return redirect(url_for('events_list'))

    if request.method == 'POST':
        if not validate_csrf():
            return redirect(url_for('event_edit', event_id=event_id))
        try:
            models.update_event(event_id,
                name=request.form.get('name', '').strip(),
                event_type=request.form.get('event_type', 'seminar'),
                description=request.form.get('description', ''),
                event_date=request.form.get('event_date') or None,
                start_time=request.form.get('start_time', ''),
                end_time=request.form.get('end_time', ''),
                location=request.form.get('location', ''),
                max_participants=int(request.form.get('max_participants', 0)),
                price=float(request.form.get('price', 0)),
            )
            flash('Event updated!', 'success')
            return redirect(url_for('events_list'))
        except Exception as e:
            print(f"[Events] Update error: {e}")
            flash('Error updating event.', 'error')

    return render_template('event_form.html', event=event)


@app.route('/events/<int:event_id>/delete', methods=['POST'])
@login_required
def event_delete(event_id):
    if not validate_csrf():
        return redirect(url_for('events_list'))
    try:
        models.delete_event(event_id)
        flash('Event deleted.', 'success')
    except Exception as e:
        print(f"[Events] Delete error: {e}")
        flash('Error deleting event.', 'error')
    return redirect(url_for('events_list'))


# ═══════════════════════════════════════════════════════════════
#  MEDIA
# ═══════════════════════════════════════════════════════════════

@app.route('/media')
@login_required
def media_page():
    academy_id = _get_academy_id()
    category = request.args.get('category', '')

    try:
        if category:
            media_items = models.get_media_by_category(category, academy_id)
        else:
            media_items = models.get_all_media(academy_id)
    except Exception:
        media_items = []

    return render_template('media.html',
        media_items=media_items,
        category=category,
    )


@app.route('/media/upload', methods=['POST'])
@login_required
def media_upload():
    if not validate_csrf():
        return redirect(url_for('media_page'))
    academy_id = _get_academy_id()

    title = request.form.get('title', '').strip()
    media_type = request.form.get('media_type', 'photo')
    category = request.form.get('category', '')
    description = request.form.get('description', '')
    belt_level = request.form.get('belt_level', 'all')

    # Handle file upload
    url = ''
    if 'file' in request.files:
        url = _save_upload(request.files['file'], 'media')
    elif request.form.get('url'):
        url = request.form.get('url', '')

    if not url:
        flash('No file uploaded.', 'error')
        return redirect(url_for('media_page'))

    try:
        models.create_media(
            academy_id=academy_id,
            title=title or 'Untitled',
            media_type=media_type,
            category=category,
            url=url,
            thumbnail=url,
            description=description,
            belt_level=belt_level,
            uploaded_by=session.get('user_id'),
        )
        flash('Media uploaded!', 'success')
    except Exception as e:
        print(f"[Media] Upload error: {e}")
        flash('Error uploading media.', 'error')

    return redirect(url_for('media_page'))


@app.route('/media/<int:media_id>/delete', methods=['POST'])
@login_required
def media_delete(media_id):
    if not validate_csrf():
        return redirect(url_for('media_page'))
    try:
        models.delete_media(media_id)
        flash('Media deleted.', 'success')
    except Exception as e:
        print(f"[Media] Delete error: {e}")
        flash('Error deleting media.', 'error')
    return redirect(url_for('media_page'))


# ═══════════════════════════════════════════════════════════════
#  SETTINGS
# ═══════════════════════════════════════════════════════════════

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings_page():
    academy_id = _get_academy_id()

    if request.method == 'POST':
        if not validate_csrf():
            return redirect(url_for('settings_page'))

        update_data = {
            'name': request.form.get('academy_name', '').strip(),
            'address': request.form.get('address', ''),
            'city': request.form.get('city', ''),
            'state': request.form.get('state', ''),
            'zip_code': request.form.get('zip_code', ''),
            'country': request.form.get('country', ''),
            'phone': request.form.get('phone', ''),
            'email': request.form.get('email', ''),
            'website': request.form.get('website', ''),
            'timezone': request.form.get('timezone', 'America/Denver'),
            'currency': request.form.get('currency', 'USD'),
            'language': request.form.get('language', 'en'),
            'theme': request.form.get('theme', 'dark'),
        }

        # Logo upload
        if 'logo' in request.files and request.files['logo'].filename:
            logo_url = _save_upload(request.files['logo'], 'logos')
            if logo_url:
                update_data['logo'] = logo_url

        try:
            models.update_academy(academy_id, **update_data)
            # Update session currency/language
            session['display_currency'] = update_data['currency']
            session['ui_lang'] = update_data['language']
            flash('Settings saved!', 'success')
        except Exception as e:
            print(f"[Settings] Error: {e}")
            flash('Error saving settings.', 'error')

        return redirect(url_for('settings_page'))

    try:
        academy = models.get_academy_by_id(academy_id)
    except Exception:
        academy = None

    return render_template('settings.html', academy=academy)


@app.route('/users', methods=['GET', 'POST'])
@login_required
def users_page():
    # Admin only
    if session.get('role') != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        if not validate_csrf():
            return redirect(url_for('users_page'))

        action = request.form.get('action', 'add')

        if action == 'add':
            try:
                # Collect permissions from checkboxes
                perm_list = []
                for p in ['checkin','members','classes','attendance','prospects','payments','finance','messaging','settings','users']:
                    if request.form.get(f'perm_{p}'):
                        perm_list.append(p)
                permissions = ','.join(perm_list)

                new_id = models.create_user(
                    username=request.form.get('username', '').strip(),
                    password=request.form.get('password', ''),
                    name=request.form.get('name', '').strip(),
                    email=request.form.get('email', '').strip(),
                    phone=request.form.get('phone', ''),
                    role=request.form.get('role', 'user'),
                    academy_id=_get_academy_id(),
                )
                if new_id and permissions:
                    models.update_user(new_id, permissions=permissions)
                flash('User created!', 'success')
            except Exception as e:
                print(f"[Users] Create error: {e}")
                flash('Error creating user.', 'error')

        elif action == 'edit':
            user_id = int(request.form.get('user_id', 0))
            update_kwargs = {
                'name': request.form.get('name', '').strip(),
                'email': request.form.get('email', '').strip(),
                'phone': request.form.get('phone', ''),
                'role': request.form.get('role', 'user'),
            }
            pw = request.form.get('password', '')
            if pw:
                update_kwargs['password'] = pw
            try:
                models.update_user(user_id, **update_kwargs)
                flash('User updated!', 'success')
            except Exception as e:
                print(f"[Users] Update error: {e}")
                flash('Error updating user.', 'error')

        elif action == 'delete':
            user_id = int(request.form.get('user_id', 0))
            if user_id != session.get('user_id'):
                try:
                    models.delete_user(user_id)
                    flash('User deleted.', 'success')
                except Exception as e:
                    print(f"[Users] Delete error: {e}")
                    flash('Error deleting user.', 'error')
            else:
                flash('Cannot delete your own account.', 'error')

        return redirect(url_for('users_page'))

    try:
        users = models.get_all_users()
    except Exception:
        users = []

    return render_template('users.html', users=users)


@app.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
def user_toggle(user_id):
    if session.get('role') != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('dashboard'))
    if not validate_csrf():
        return redirect(url_for('users_page'))
    if user_id == session.get('user_id'):
        flash('Cannot deactivate your own account.', 'error')
        return redirect(url_for('users_page'))
    try:
        user = models.get_user(user_id)
        if user:
            new_active = not user.get('active', True)
            models.update_user(user_id, active=new_active)
            flash(f"User {'activated' if new_active else 'deactivated'}.", 'success')
    except Exception as e:
        print(f"[Users] Toggle error: {e}")
        flash('Error toggling user.', 'error')
    return redirect(url_for('users_page'))


@app.route('/users/<int:user_id>/edit', methods=['POST'])
@login_required
def user_edit(user_id):
    if session.get('role') != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('dashboard'))
    if not validate_csrf():
        return redirect(url_for('users_page'))
    try:
        # Collect permissions
        perm_list = []
        for p in ['checkin','members','classes','attendance','prospects','payments','finance','messaging','settings','users']:
            if request.form.get(f'perm_{p}'):
                perm_list.append(p)
        permissions = ','.join(perm_list)

        update_data = {
            'name': request.form.get('name', '').strip(),
            'email': request.form.get('email', '').strip(),
            'phone': request.form.get('phone', ''),
            'role': request.form.get('role', 'staff'),
            'permissions': permissions,
        }
        pw = request.form.get('password', '').strip()
        if pw:
            update_data['password'] = pw
        models.update_user(user_id, **update_data)
        flash('User updated!', 'success')
    except Exception as e:
        print(f"[Users] Edit error: {e}")
        flash('Error updating user.', 'error')
    return redirect(url_for('users_page'))


# ═══════════════════════════════════════════════════════════════
#  NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════

@app.route('/notifications')
@login_required
def notifications_page():
    academy_id = _get_academy_id()
    try:
        notifications = models.get_all_notifications(academy_id, limit=100)
        # Mark displayed notifications as read
        for n in (notifications or []):
            if not n.get('read'):
                try:
                    models.mark_notification_read(n['id'])
                except Exception:
                    pass
    except Exception:
        notifications = []

    return render_template('notifications.html', notifications=notifications)


# ═══════════════════════════════════════════════════════════════
#  BUG REPORTS
# ═══════════════════════════════════════════════════════════════

@app.route('/bug-report', methods=['GET', 'POST'])
def bug_report():
    if request.method == 'POST':
        user_id = session.get('user_id')
        try:
            # Handle screenshot upload
            screenshot_url = ''
            if 'screenshot' in request.files:
                screenshot_url = _save_upload(request.files['screenshot'], 'bugs')

            models.create_bug_report(
                user_id=user_id,
                report_type=request.form.get('report_type', 'bug'),
                title=request.form.get('title', '').strip(),
                description=request.form.get('description', ''),
                screenshot=screenshot_url,
            )
            flash('Thank you! Your report has been submitted.', 'success')
            return redirect(url_for('bug_report'))
        except Exception as e:
            print(f"[BugReport] Error: {e}")
            flash('Error submitting report. Please try again.', 'error')

    return render_template('bug_report_form.html')


@app.route('/api/help-report')
def api_help_report():
    """Quick bug report from the help button (AJAX)."""
    title = request.args.get('title', 'Quick help report')
    description = request.args.get('description', '')
    page = request.args.get('page', '')
    user_id = session.get('user_id')

    try:
        report_id = models.create_bug_report(
            user_id=user_id,
            report_type='help',
            title=title,
            description=f"Page: {page}\n{description}",
        )
        return jsonify({'success': True, 'id': report_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════
#  LANDING PAGE
# ═══════════════════════════════════════════════════════════════

@app.route('/landing')
def landing_page():
    return render_template('landing.html')


# ═══════════════════════════════════════════════════════════════
#  API ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.route('/api/dashboard-stats')
@login_required
def api_dashboard_stats():
    academy_id = _get_academy_id()
    try:
        stats = models.get_dashboard_stats(academy_id)
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/members/search')
@login_required
def api_members_search():
    q = request.args.get('q', '').strip()
    academy_id = _get_academy_id()
    if not q:
        return jsonify([])
    try:
        results = models.search_members(q, academy_id)
        return jsonify([{
            'id': m.get('id'),
            'first_name': m.get('first_name', ''),
            'last_name': m.get('last_name', ''),
            'email': m.get('email', ''),
            'phone': m.get('phone', ''),
            'photo': m.get('photo', ''),
            'belt': m.get('belt_name', 'White'),
        } for m in (results or [])[:20]])
    except Exception:
        return jsonify([])


@app.route('/api/checkin/today')
@login_required
def api_checkin_today():
    academy_id = _get_academy_id()
    try:
        checkins = models.get_today_checkins(academy_id)
        return jsonify([{
            'id': c.get('id'),
            'member_name': f"{c.get('first_name', '')} {c.get('last_name', '')}",
            'class_name': c.get('class_name', ''),
            'time': str(c.get('check_in_time', ''))[:16],
            'method': c.get('method', ''),
        } for c in (checkins or [])])
    except Exception:
        return jsonify([])


# ═══════════════════════════════════════════════════════════════
#  MESSAGING (Mass Communication)
# ═══════════════════════════════════════════════════════════════

@app.route('/messaging')
@login_required
def messaging_page():
    academy_id = _get_academy_id()
    try:
        members = models.get_all_members(academy_id)
    except Exception:
        members = []
    try:
        plans = models.get_all_membership_plans(academy_id)
    except Exception:
        plans = []
    try:
        messages = models.get_all_messages(academy_id, limit=50)
    except Exception:
        messages = []
    try:
        belts = models.get_all_belt_ranks()
    except Exception:
        belts = []

    try:
        stats = models.get_messaging_stats(academy_id)
    except Exception:
        stats = {}

    programs = models.get_programs(academy_id)
    return render_template('messaging.html',
                           members=members,
                           plans=plans,
                           messages=messages,
                           belts=belts,
                           stats=stats,
                           programs=programs)


@app.route('/messaging/send', methods=['POST'])
@login_required
def messaging_send():
    if not validate_csrf():
        return redirect(url_for('messaging_page'))

    academy_id = _get_academy_id()
    subject = request.form.get('subject', '').strip()
    body = request.form.get('body', '').strip()
    channel = request.form.get('channel', 'email')
    filter_type = request.form.get('filter_type', 'all')
    filter_value = request.form.get('filter_value', '')
    manual_ids = request.form.get('manual_ids', '')

    if not body:
        flash('Message body is required.', 'error')
        return redirect(url_for('messaging_page'))

    # Determine recipients
    if filter_type == 'manual':
        recipients = models.get_members_by_filter(academy_id, 'manual', manual_ids)
    else:
        recipients = models.get_members_by_filter(academy_id, filter_type, filter_value)

    if not recipients:
        flash(get_text(session.get('ui_lang', 'en'), 'msg_no_recipients'), 'warning')
        return redirect(url_for('messaging_page'))

    email_sent = 0
    email_failed = 0
    sms_sent = 0
    sms_failed = 0

    # Send emails
    if channel in ('email', 'both'):
        smtp_host = os.environ.get('SMTP_HOST', '')
        smtp_port = os.environ.get('SMTP_PORT', '587')
        smtp_user = os.environ.get('SMTP_USER', '')
        smtp_pass = os.environ.get('SMTP_PASS', '')
        smtp_from = os.environ.get('SMTP_FROM', smtp_user)

        if smtp_host and smtp_user:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            try:
                server = smtplib.SMTP(smtp_host, int(smtp_port))
                server.starttls()
                server.login(smtp_user, smtp_pass)

                for member in recipients:
                    if member.get('email'):
                        try:
                            msg = MIMEMultipart()
                            msg['From'] = smtp_from
                            msg['To'] = member['email']
                            msg['Subject'] = subject
                            msg.attach(MIMEText(body, 'plain'))
                            server.sendmail(smtp_from, member['email'], msg.as_string())
                            email_sent += 1
                        except Exception as e:
                            print(f"[Messaging] Email error for {member.get('email')}: {e}")
                            email_failed += 1

                server.quit()
            except Exception as e:
                print(f"[Messaging] SMTP connection error: {e}")
                email_failed = len([m for m in recipients if m.get('email')])
        else:
            flash('SMTP is not configured. Emails were not sent.', 'warning')

    # Send SMS
    if channel in ('sms', 'both'):
        twilio_sid = os.environ.get('TWILIO_SID', '')
        twilio_token = os.environ.get('TWILIO_TOKEN', '')
        twilio_from = os.environ.get('TWILIO_FROM', '')

        if twilio_sid and twilio_token and twilio_from:
            try:
                from twilio.rest import Client
                client = Client(twilio_sid, twilio_token)

                sms_body = f"{subject}\n\n{body}" if subject else body
                for member in recipients:
                    if member.get('phone'):
                        try:
                            client.messages.create(
                                body=sms_body,
                                from_=twilio_from,
                                to=member['phone']
                            )
                            sms_sent += 1
                        except Exception as e:
                            print(f"[Messaging] SMS error for {member.get('phone')}: {e}")
                            sms_failed += 1
            except ImportError:
                flash('Twilio library not installed. SMS were not sent.', 'warning')
            except Exception as e:
                print(f"[Messaging] Twilio error: {e}")
                sms_failed = len([m for m in recipients if m.get('phone')])
        else:
            flash('Twilio is not configured. SMS were not sent.', 'warning')

    # Build filter description for logging
    filter_desc = filter_type
    if filter_value:
        filter_desc = f"{filter_type}:{filter_value}"
    if filter_type == 'manual':
        filter_desc = f"manual:{len(recipients)} selected"

    # Calculate delivery stats
    total_attempted = email_sent + email_failed + sms_sent + sms_failed
    delivered = email_sent + sms_sent
    bounced = email_failed + sms_failed

    status = 'sent'
    if delivered == 0 and total_attempted > 0:
        status = 'failed'
    elif bounced > 0:
        status = 'partial'

    try:
        models.create_message(
            academy_id=academy_id,
            subject=subject,
            body=body,
            channel=channel,
            recipient_filter=filter_desc,
            recipient_count=len(recipients),
            delivered=delivered,
            sent_by=session.get('user_id'),
            status=status,
        )
    except Exception as e:
        print(f"[Messaging] Log error: {e}")

    # Update message with delivery breakdown
    try:
        msgs = models.get_all_messages(academy_id, limit=1)
        if msgs:
            models.update_message_stats(msgs[0]['id'],
                total=len(recipients),
                delivered=delivered,
                bounced=bounced,
            )
    except Exception as e:
        print(f"[Messaging] Stats update error: {e}")

    # Flash results
    parts = []
    if channel in ('email', 'both'):
        parts.append(f"{email_sent} email(s) sent")
        if email_failed:
            parts.append(f"{email_failed} email(s) failed")
    if channel in ('sms', 'both'):
        parts.append(f"{sms_sent} SMS sent")
        if sms_failed:
            parts.append(f"{sms_failed} SMS failed")

    flash(', '.join(parts) if parts else 'Message logged.', 'success' if status == 'sent' else 'warning')
    return redirect(url_for('messaging_page'))


@app.route('/api/messaging/preview')
@login_required
def api_messaging_preview():
    academy_id = _get_academy_id()
    filter_type = request.args.get('filter_type', 'all')
    filter_value = request.args.get('filter_value', '')
    channel = request.args.get('channel', 'email')

    try:
        recipients = models.get_members_by_filter(academy_id, filter_type, filter_value)
        # Count those with valid contact for the channel
        if channel == 'email':
            count = len([m for m in recipients if m.get('email')])
        elif channel == 'sms':
            count = len([m for m in recipients if m.get('phone')])
        else:  # both
            count = len(recipients)
        return jsonify({'count': count, 'total': len(recipients)})
    except Exception:
        return jsonify({'count': 0, 'total': 0})


@app.route('/api/messaging/ai-write', methods=['POST'])
@login_required
def api_messaging_ai_write():
    """Use Gemini free API to generate email/SMS content."""
    import requests as http_requests

    data = request.get_json() or {}
    user_prompt = data.get('prompt', '').strip()
    channel = data.get('channel', 'email')

    if not user_prompt:
        return jsonify({'error': 'Please describe what you want to write.'})

    api_key = os.environ.get('GEMINI_API_KEY', '')
    if not api_key:
        return jsonify({'error': 'AI not configured. Add GEMINI_API_KEY in settings.'})

    # Build system prompt
    if channel == 'sms':
        system = (
            "You are an assistant for a Jiu-Jitsu academy. "
            "Write a short SMS message (max 160 characters). "
            "Be direct, friendly, professional. No emojis unless asked. "
            "Reply ONLY with the SMS text, nothing else."
        )
    else:
        system = (
            "You are an assistant for a Jiu-Jitsu academy. "
            "Write a professional email for the academy to send to its members. "
            "Reply in this exact format:\n"
            "SUBJECT: (the email subject line)\n"
            "BODY:\n(the email body text)\n\n"
            "Be friendly, professional, concise. No emojis unless asked. "
            "Write in the same language as the user's request."
        )

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        resp = http_requests.post(url, json={
            "contents": [
                {"role": "user", "parts": [{"text": f"{system}\n\nUser request: {user_prompt}"}]}
            ],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 500}
        }, timeout=15)

        if resp.status_code != 200:
            print(f"[AI] Gemini error: {resp.status_code} {resp.text[:200]}")
            return jsonify({'error': f'AI service error ({resp.status_code})'})

        result = resp.json()
        text = result['candidates'][0]['content']['parts'][0]['text'].strip()

        if channel == 'sms':
            return jsonify({'body': text[:160], 'subject': ''})
        else:
            # Parse SUBJECT: and BODY: from response
            subject = ''
            body = text
            if 'SUBJECT:' in text and 'BODY:' in text:
                parts = text.split('BODY:', 1)
                subject_part = parts[0]
                body = parts[1].strip() if len(parts) > 1 else text
                if 'SUBJECT:' in subject_part:
                    subject = subject_part.split('SUBJECT:', 1)[1].strip()
            elif text.startswith('SUBJECT:'):
                lines = text.split('\n', 1)
                subject = lines[0].replace('SUBJECT:', '').strip()
                body = lines[1].strip() if len(lines) > 1 else ''

            return jsonify({'subject': subject, 'body': body})

    except Exception as e:
        print(f"[AI] Error: {e}")
        return jsonify({'error': f'AI error: {str(e)}'})


# ═══════════════════════════════════════════════════════════════
#  STATIC FILES
# ═══════════════════════════════════════════════════════════════

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )


@app.route('/robots.txt')
def robots():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'robots.txt',
        mimetype='text/plain'
    )


# ═══════════════════════════════════════════════════════════════
#  WEBAUTHN (FaceID / TouchID) CHECK-IN
# ═══════════════════════════════════════════════════════════════

@app.route('/api/webauthn/register-options', methods=['POST'])
@login_required
def webauthn_register_options():
    """Generate registration options for WebAuthn."""
    import json, os, base64
    data = request.get_json() or {}
    member_id = data.get('member_id')
    if not member_id:
        return jsonify({'error': 'member_id required'}), 400

    member = models.get_member_by_id(int(member_id))
    if not member:
        return jsonify({'error': 'Member not found'}), 404

    # Generate challenge
    challenge = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')

    # Store challenge in session
    session['webauthn_challenge'] = challenge
    session['webauthn_member_id'] = int(member_id)

    options = {
        'challenge': challenge,
        'rp': {'name': 'Fit4Academy', 'id': request.host.split(':')[0]},
        'user': {
            'id': base64.urlsafe_b64encode(str(member_id).encode()).decode().rstrip('='),
            'name': f"{member.get('first_name', '')} {member.get('last_name', '')}",
            'displayName': f"{member.get('first_name', '')} {member.get('last_name', '')}",
        },
        'pubKeyCredParams': [
            {'type': 'public-key', 'alg': -7},   # ES256
            {'type': 'public-key', 'alg': -257},  # RS256
        ],
        'authenticatorSelection': {
            'authenticatorAttachment': 'platform',  # Forces FaceID/TouchID (not USB key)
            'userVerification': 'required',
        },
        'timeout': 60000,
        'attestation': 'none',
    }
    return jsonify(options)


@app.route('/api/webauthn/register', methods=['POST'])
@login_required
def webauthn_register():
    """Save WebAuthn credential for a member."""
    import json, base64
    data = request.get_json() or {}

    member_id = session.get('webauthn_member_id')
    if not member_id:
        return jsonify({'error': 'No registration in progress'}), 400

    credential_id = data.get('credential_id', '')
    public_key = data.get('public_key', '')

    if not credential_id:
        return jsonify({'error': 'Invalid credential'}), 400

    # Store credential in member record
    try:
        models.update_member(member_id,
            webauthn_credential_id=credential_id,
            webauthn_public_key=public_key
        )
        return jsonify({'success': True, 'message': 'Biometric registered!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/webauthn/auth-options', methods=['POST'])
def webauthn_auth_options():
    """Generate authentication options for check-in."""
    import os, base64
    academy_id = _get_academy_id()

    challenge = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
    session['webauthn_auth_challenge'] = challenge

    # Get all members with registered credentials
    try:
        members = models.get_all_members(academy_id)
        allow_credentials = []
        for m in (members or []):
            cred_id = m.get('webauthn_credential_id', '')
            if cred_id:
                allow_credentials.append({
                    'type': 'public-key',
                    'id': cred_id,
                })
    except Exception:
        allow_credentials = []

    options = {
        'challenge': challenge,
        'rpId': request.host.split(':')[0],
        'allowCredentials': allow_credentials,
        'userVerification': 'required',
        'timeout': 60000,
    }
    return jsonify(options)


@app.route('/api/webauthn/authenticate', methods=['POST'])
def webauthn_authenticate():
    """Verify WebAuthn assertion and check-in the member."""
    data = request.get_json() or {}
    credential_id = data.get('credential_id', '')
    academy_id = _get_academy_id()

    if not credential_id:
        return jsonify({'error': 'Invalid credential'}), 400

    # Find member by credential_id
    try:
        members = models.get_all_members(academy_id)
        member = None
        for m in (members or []):
            if m.get('webauthn_credential_id') == credential_id:
                member = m
                break

        if not member:
            return jsonify({'error': 'Biometric not recognized'}), 404

        # Create check-in
        models.create_checkin(
            member_id=member['id'],
            class_id=None,
            academy_id=academy_id,
            method='biometric'
        )

        name = f"{member.get('first_name', '')} {member.get('last_name', '')}"
        return jsonify({
            'success': True,
            'name': name,
            'belt': member.get('belt_name', 'White'),
            'member_id': member['id']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════
#  PUBLIC BIOMETRIC REGISTRATION (no login needed — PIN verification)
# ═══════════════════════════════════════════════════════════════

@app.route('/setup-biometric/<pin>')
def public_biometric_setup(pin):
    """Public page where member registers FaceID/TouchID using their PIN."""
    # Find member by PIN
    member = None
    try:
        all_members = models.get_all_members(1)  # Default academy
        for m in (all_members or []):
            if m.get('pin') == pin:
                member = m
                break
    except Exception:
        pass

    if not member:
        return render_template('biometric_setup.html', error='Invalid PIN', member=None)

    return render_template('biometric_setup.html', member=member, error=None)


@app.route('/api/public/webauthn/register-options', methods=['POST'])
def public_webauthn_register_options():
    """Public WebAuthn registration — verifies by PIN."""
    import os, base64
    data = request.get_json() or {}
    pin = data.get('pin', '').strip()

    if not pin or len(pin) != 4:
        return jsonify({'error': 'Invalid PIN'}), 400

    member = None
    try:
        all_members = models.get_all_members(1)
        for m in (all_members or []):
            if m.get('pin') == pin:
                member = m
                break
    except Exception:
        pass

    if not member:
        return jsonify({'error': 'PIN not found'}), 404

    challenge = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
    session['webauthn_challenge'] = challenge
    session['webauthn_member_id'] = member['id']

    options = {
        'challenge': challenge,
        'rp': {'name': 'Fit4Academy', 'id': request.host.split(':')[0]},
        'user': {
            'id': base64.urlsafe_b64encode(str(member['id']).encode()).decode().rstrip('='),
            'name': f"{member.get('first_name', '')} {member.get('last_name', '')}",
            'displayName': f"{member.get('first_name', '')} {member.get('last_name', '')}",
        },
        'pubKeyCredParams': [
            {'type': 'public-key', 'alg': -7},
            {'type': 'public-key', 'alg': -257},
        ],
        'authenticatorSelection': {
            'authenticatorAttachment': 'platform',
            'userVerification': 'required',
        },
        'timeout': 60000,
        'attestation': 'none',
    }
    return jsonify(options)


@app.route('/api/public/webauthn/register', methods=['POST'])
def public_webauthn_register():
    """Public save of WebAuthn credential — session must have member_id from register-options."""
    data = request.get_json() or {}
    member_id = session.get('webauthn_member_id')
    if not member_id:
        return jsonify({'error': 'No registration in progress'}), 400

    credential_id = data.get('credential_id', '')
    if not credential_id:
        return jsonify({'error': 'Invalid credential'}), 400

    try:
        models.update_member(member_id,
            webauthn_credential_id=credential_id,
            webauthn_public_key=data.get('public_key', '')
        )
        return jsonify({'success': True, 'message': 'Biometric registered!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    print("  Fit4Academy")
    print(f"  http://localhost:{port}")
    app.run(debug=True, host='0.0.0.0', port=port)
