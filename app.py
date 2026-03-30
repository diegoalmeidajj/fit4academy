"""Fit4Academy — Jiu-Jitsu Academy CRM
Main Flask application."""

# ═══════════════════════════════════════════════════════════════
#  IMPORTS & SETUP
# ═══════════════════════════════════════════════════════════════

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, send_from_directory, Response, abort)
import config
import models
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

    return render_template('dashboard.html',
        greeting=greeting,
        stats=stats,
        today_classes=today_classes,
        recent_checkins=recent_checkins,
        upcoming_birthdays=upcoming_birthdays,
        payment_alerts=payment_alerts,
        belt_distribution=belt_distribution,
        at_risk=at_risk,
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

    return render_template('member_form.html',
        member=None,
        belt_ranks=belt_ranks,
        membership_plans=plans_display,
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
        }

        # Photo upload
        if 'photo' in request.files and request.files['photo'].filename:
            photo_url = _save_upload(request.files['photo'], 'members')
            if photo_url:
                update_data['photo'] = photo_url

        try:
            models.update_member(member_id, **update_data)
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

    return render_template('member_form.html',
        member=member,
        belt_ranks=belt_ranks,
        membership_plans=plans_display,
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

        # QR contains: CHECKIN:{pin}
        qr_data = f"CHECKIN:{pin}"

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
                'capacity': 30,
            })
    except Exception as e:
        print(f"[Classes] Error: {e}")

    try:
        classes = models.get_all_classes(academy_id)
    except Exception:
        classes = []

    return render_template('classes.html',
        schedule=schedule,
        classes=classes,
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
            class_id = models.create_class(
                academy_id=academy_id,
                name=request.form.get('name', '').strip(),
                class_type=request.form.get('class_type', 'gi'),
                instructor=request.form.get('instructor', '').strip(),
                description=request.form.get('description', ''),
                duration=int(request.form.get('duration', 60)),
                max_capacity=int(request.form.get('max_capacity', 30)),
                belt_level=request.form.get('belt_level', 'all'),
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

    return render_template('class_form.html', cls=None)


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
            models.update_class(class_id,
                name=request.form.get('name', '').strip(),
                class_type=request.form.get('class_type', 'gi'),
                instructor=request.form.get('instructor', '').strip(),
                description=request.form.get('description', ''),
                duration=int(request.form.get('duration', 60)),
                max_capacity=int(request.form.get('max_capacity', 30)),
                belt_level=request.form.get('belt_level', 'all'),
            )
            flash('Class updated!', 'success')
            return redirect(url_for('classes_list'))
        except Exception as e:
            print(f"[Classes] Update error: {e}")
            flash('Error updating class.', 'error')

    return render_template('class_form.html', cls=cls)


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
    belts = []
    try:
        all_members = models.get_all_members(academy_id)
        for b in (belt_ranks or []):
            belt_members = [m for m in (all_members or []) if m.get('belt_rank_id') == b.get('id')]
            belts.append({
                'id': b.get('id'),
                'name': b.get('name', ''),
                'color': b.get('color', '#000'),
                'count': len(belt_members),
                'max_stripes': b.get('max_stripes', 4),
                'min_months': b.get('min_months', 0),
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
            from_belt_id = int(request.form.get('from_belt_id', 1))
            to_belt_id = int(request.form.get('to_belt_id', 1))
            from_stripes = int(request.form.get('from_stripes', 0))
            to_stripes = int(request.form.get('to_stripes', 0))
            promotion_date = request.form.get('promotion_date') or str(date.today())
            promoted_by = request.form.get('promoted_by', '')
            notes = request.form.get('notes', '')

            models.create_promotion(
                member_id=member_id,
                from_belt_id=from_belt_id,
                to_belt_id=to_belt_id,
                from_stripes=from_stripes,
                to_stripes=to_stripes,
                promotion_date=promotion_date,
                promoted_by=promoted_by,
                notes=notes,
            )
            flash('Promotion recorded!', 'success')
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

    return render_template('promotion_form.html',
        members=members,
        belt_ranks=belt_ranks,
        pre_member=pre_member,
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


# ═══════════════════════════════════════════════════════════════
#  PAYMENTS
# ═══════════════════════════════════════════════════════════════

@app.route('/payments')
@login_required
def payments_list():
    academy_id = _get_academy_id()
    status_filter = request.args.get('status', '')
    method_filter = request.args.get('method', '')

    try:
        payments = models.get_all_payments(academy_id)
        if status_filter:
            payments = [p for p in payments if p.get('status') == status_filter]
        if method_filter:
            payments = [p for p in payments if p.get('method') == method_filter]
    except Exception:
        payments = []

    summary = {
        'total_collected': sum(p.get('amount', 0) for p in payments if p.get('status') == 'completed'),
        'pending': sum(p.get('amount', 0) for p in payments if p.get('status') == 'pending'),
        'overdue': len([p for p in payments if p.get('status') == 'failed']),
    }

    return render_template('payments.html',
        payments=payments,
        summary=summary,
        status_filter=status_filter,
        method_filter=method_filter,
    )


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

    finance = {
        'total_revenue': 0,
        'avg_per_member': 0,
        'this_month': 0,
        'outstanding': 0,
    }

    monthly_revenue = {}
    revenue_by_method = {}

    try:
        stats = models.get_dashboard_stats(academy_id)
        finance['this_month'] = stats.get('monthly_revenue', 0)
        active_count = stats.get('active_members', 1) or 1

        # Monthly data
        monthly_raw = models.get_monthly_revenue(academy_id, months=12)
        total = 0
        for row in (monthly_raw or []):
            month_key = row.get('month', '')
            amount = row.get('total', 0) or 0
            monthly_revenue[month_key] = amount
            total += amount
        finance['total_revenue'] = total
        finance['avg_per_member'] = round(total / active_count, 2) if active_count else 0

        # Revenue by method
        method_raw = models.get_revenue_by_method(academy_id)
        for row in (method_raw or []):
            revenue_by_method[row.get('method', 'other')] = row.get('total', 0)

        # Outstanding
        alerts = models.get_payment_alerts(academy_id)
        finance['outstanding'] = sum(a.get('amount', 0) for a in (alerts or []))

    except Exception as e:
        print(f"[Finance] Error: {e}")

    return render_template('finance.html',
        finance=finance,
        monthly_revenue=monthly_revenue,
        revenue_by_method=revenue_by_method,
    )


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

    # Group by stage for pipeline view
    prospects_by_stage = {
        'new': [],
        'contacted': [],
        'trial': [],
        'converted': [],
        'lost': [],
        'ex_student': [],
    }
    for p in (all_prospects or []):
        stage = p.get('status', 'new')
        # Ex-students: source=ex_student OR status=lost with member_id
        if p.get('source') == 'ex_student' or (stage == 'lost' and p.get('member_id')):
            prospects_by_stage['ex_student'].append(p)
        elif stage in prospects_by_stage:
            prospects_by_stage[stage].append(p)
        else:
            prospects_by_stage['new'].append(p)

    return render_template('prospects.html',
        prospects=all_prospects,
        prospects_by_stage=prospects_by_stage,
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
                models.create_user(
                    username=request.form.get('username', '').strip(),
                    password=request.form.get('password', ''),
                    name=request.form.get('name', '').strip(),
                    email=request.form.get('email', '').strip(),
                    phone=request.form.get('phone', ''),
                    role=request.form.get('role', 'user'),
                    academy_id=_get_academy_id(),
                )
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

    return render_template('messaging.html',
                           members=members,
                           plans=plans,
                           messages=messages,
                           belts=belts,
                           stats=stats)


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
#  MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    print("  Fit4Academy")
    print(f"  http://localhost:{port}")
    app.run(debug=True, host='0.0.0.0', port=port)
