from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import json
from datetime import datetime, timedelta
import pytz
import random
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from collections import defaultdict
from collections import defaultdict
from calendar import monthrange
import calendar
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = 'face_data'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
VALID_DEPARTMENTS = ['IT', 'Chemistry', 'English', 'Microbiology']
SECURITY_QUESTIONS = {
    'pet': 'What was your first pets name?',
    'city': 'In which city were you born?',
    'school': 'What was your first schools name?',
    'mother': 'What is your mothers maiden name?',
    'food': 'What is your favorite childhood food?'
}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_user_data():
    try:
        with open('user_records.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_user_data(data):
    with open('user_records.json', 'w') as f:
        json.dump(data, f, indent=4)

def generate_student_id(user_data):
    while True:
        student_id = str(random.randint(0, 999999)).zfill(6)
        if student_id not in user_data:
            return student_id

def get_attendance_files():
    return [f for f in os.listdir('.') if f.startswith('attendance_') and f.endswith('.json')]


def calculate_attendance_stats(student_id):
    """Calculate detailed attendance statistics for a student"""
    attendance_data = defaultdict(list)
    monthly_stats = defaultdict(lambda: {'present': 0, 'late': 0, 'absent': 0})

    # Get all attendance records
    for file in get_attendance_files():
        with open(file, 'r') as f:
            data = json.load(f)
            for date, entries in data.items():
                year_month = date[:7]  # Get YYYY-MM from YYYY-MM-DD
                if student_id in entries:
                    entry = entries[student_id]
                    attendance_data[date].append(entry)

                    # Update monthly statistics
                    if 'Late' in entry['status']:
                        monthly_stats[year_month]['late'] += 1
                    else:
                        monthly_stats[year_month]['present'] += 1
                else:
                    # If no entry for this date, count as absent
                    monthly_stats[year_month]['absent'] += 1

    return attendance_data, monthly_stats
def get_student_records(student_id):
    records = []
    for file in get_attendance_files():
        with open(file, 'r') as f:
            data = json.load(f)
            for date, entries in data.items():
                if student_id in entries:
                    record = entries[student_id]
                    record['date'] = date
                    records.append(record)
    return sorted(records, key=lambda x: x['date'], reverse=True)

def count_lates(student_id):
    count = 0
    for file in get_attendance_files():
        with open(file, 'r') as f:
            data = json.load(f)
            for entries in data.values():
                if student_id in entries and "Late" in entries[student_id].get('status', ''):
                    count += 1
    return count

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        password = request.form.get('password')
        user_data = load_user_data()

        if student_id not in user_data or not check_password_hash(user_data[student_id]['password'], password):
            flash('Invalid ID or password', 'danger')
            return redirect(url_for('login'))

        session['user_id'] = student_id
        return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        department = request.form.get('department')
        password = request.form.get('password')
        photo = request.files.get('photo')
        security_question = request.form.get('security_question')
        security_answer = request.form.get('security_answer')

        if not all([name, department, password, photo, security_question, security_answer]):
            flash('All fields are required', 'danger')
            return redirect(url_for('register'))

        # ... (existing validation code) ...

        user_data = load_user_data()
        student_id = generate_student_id(user_data)

        filename = f"user_{student_id}.{secure_filename(photo.filename).rsplit('.', 1)[1].lower()}"
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        photo.save(photo_path)

        user_data[student_id] = {
            'name': name,
            'department': department,
            'photo_path': photo_path,
            'password': generate_password_hash(password),
            'security_question': security_question,
            'security_answer': generate_password_hash(security_answer.lower()),  # Store hashed answer
            'registration_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_user_data(user_data)

        flash(f'Registration successful! Your Student ID is {student_id}', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        step = request.form.get('step', 'verify_id')
        student_id = request.form.get('student_id')
        user_data = load_user_data()

        if step == 'verify_id':
            if student_id in user_data:
                security_question = SECURITY_QUESTIONS[user_data[student_id]['security_question']]
                return render_template('forgot_password.html',
                                     step='security_question',
                                     student_id=student_id,
                                     security_question=security_question)
            else:
                flash('Invalid Student ID', 'danger')
                return render_template('forgot_password.html', step='verify_id')

        elif step == 'security_question':
            security_answer = request.form.get('security_answer')
            if student_id in user_data and check_password_hash(
                user_data[student_id]['security_answer'],
                security_answer.lower()
            ):
                return render_template('forgot_password.html',
                                     step='reset_password',
                                     student_id=student_id,
                                     verified='true')
            else:
                flash('Incorrect answer', 'danger')
                return redirect(url_for('forgot_password'))

        elif step == 'reset_password':
            if student_id in user_data and request.form.get('verified') == 'true':
                password = request.form.get('password')
                confirm_password = request.form.get('confirm_password')

                if password != confirm_password:
                    flash('Passwords do not match', 'danger')
                    return render_template('forgot_password.html',
                                         step='reset_password',
                                         student_id=student_id,
                                         verified='true')

                user_data[student_id]['password'] = generate_password_hash(password)
                save_user_data(user_data)
                flash('Password has been reset successfully', 'success')
                return redirect(url_for('login'))

    return render_template('forgot_password.html', step='verify_id')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/help')
def help():
    return render_template('help.html')


@app.route('/profile/dashboard')
def personal_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_data = load_user_data()
    user = user_data[user_id]

    # Calculate attendance statistics
    attendance_stats = {
        'total_days': 0,
        'present_days': 0,
        'late_days': 0,
        'absent_days': 0,
        'last_attendance': None,
        'streak': 0,
        'recent_records': []
    }

    current_streak = 0
    last_date = None

    # Process attendance records
    for file in get_attendance_files():
        with open(file, 'r') as f:
            data = json.load(f)
            for date, entries in sorted(data.items(), reverse=True):
                if user_id in entries:
                    entry = entries[user_id]
                    attendance_stats['total_days'] += 1

                    # Update last attendance
                    if not attendance_stats['last_attendance']:
                        attendance_stats['last_attendance'] = {
                            'date': date,
                            'time': entry['time'],
                            'status': entry['status']
                        }

                    # Calculate streak
                    current_date = datetime.strptime(date, '%Y-%m-%d').date()
                    if last_date:
                        if (last_date - current_date).days == 1:
                            current_streak += 1
                        else:
                            current_streak = 1
                    else:
                        current_streak = 1

                    last_date = current_date
                    attendance_stats['streak'] = max(attendance_stats['streak'], current_streak)

                    # Count status
                    if 'Late' in entry['status']:
                        attendance_stats['late_days'] += 1
                    else:
                        attendance_stats['present_days'] += 1

                    # Add to recent records (keep last 5)
                    if len(attendance_stats['recent_records']) < 5:
                        attendance_stats['recent_records'].append({
                            'date': date,
                            'time': entry['time'],
                            'status': entry['status']
                        })

    # Calculate absent days
    total_school_days = attendance_stats['total_days']  # You might want to calculate this differently
    attendance_stats['absent_days'] = total_school_days - (
                attendance_stats['present_days'] + attendance_stats['late_days'])

    # Get current UTC time
    current_time = datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')

    return render_template('profile/dashboard.html',
                           user=user,
                           stats=attendance_stats,
                           current_time=current_time)


@app.route('/profile/settings', methods=['GET', 'POST'])
def profile_settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_data = load_user_data()
    user = user_data[user_id]

    if request.method == 'POST':
        # Update basic information
        user['name'] = request.form.get('name', user['name'])
        user['email'] = request.form.get('email', user['email'])
        user['department'] = request.form.get('department', user['department'])

        # Handle password change
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if current_password and new_password:
            if not check_password_hash(user['password'], current_password):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('profile_settings'))

            if new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
                return redirect(url_for('profile_settings'))

            user['password'] = generate_password_hash(new_password)

        # Save changes
        user_data[user_id] = user
        save_user_data(user_data)

        flash('Profile updated successfully.', 'success')
        return redirect(url_for('personal_dashboard'))

    return render_template('profile/settings.html', user=user)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        # Here you could add code to store the message or send it to administrators
        flash('Thank you for your message. We will respond soon.', 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html')
@app.route('/attendance_summary')
def attendance_summary():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    student_id = session['user_id']
    user_data = load_user_data()

    # Get attendance statistics
    attendance_data, monthly_stats = calculate_attendance_stats(student_id)

    # Calculate overall statistics
    total_days = sum(len(days) for days in attendance_data.values())
    total_late = sum(1 for days in attendance_data.values()
                     for entry in days if 'Late' in entry['status'])

    # Get current month's working days
    current_month = datetime.now().strftime('%Y-%m')
    _, days_in_month = monthrange(datetime.now().year, datetime.now().month)

    # Prepare monthly data for chart
    months = sorted(monthly_stats.keys())
    attendance_counts = {
        'present': [monthly_stats[m]['present'] for m in months],
        'late': [monthly_stats[m]['late'] for m in months],
        'absent': [monthly_stats[m]['absent'] for m in months]
    }

    return render_template('attendance_summary.html',
                           user=user_data[student_id],
                           total_days=total_days,
                           total_late=total_late,
                           monthly_stats=monthly_stats,
                           current_month=current_month,
                           days_in_month=days_in_month,
                           months=months,
                           attendance_counts=attendance_counts)
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    attendance_data = defaultdict(list)
    total_lates = 0
    department_count = defaultdict(int)

    for file in get_attendance_files():
        with open(file, 'r') as f:
            daily_data = json.load(f)
            for date, entries in daily_data.items():
                attendance_data[date].extend(entries.values())
                for entry in entries.values():
                    department = entry.get('department', 'Unknown')
                    status = entry.get('status', '')

                    department_count[department] += 1
                    if "Late" in status:
                        total_lates += 1

    dates = sorted(attendance_data.keys())[-7:]
    daily_counts = [len(attendance_data[date]) for date in dates]

    return render_template('dashboard.html',
                           total_students=len(load_user_data()),
                           total_lates=total_lates,
                           dates=json.dumps(dates),
                           daily_counts=json.dumps(daily_counts),
                           department_count=json.dumps(department_count))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    student_id = session['user_id']
    user_data = load_user_data()
    if student_id not in user_data:
        flash('Student not found', 'danger')
        return redirect(url_for('login'))

    records = get_student_records(student_id)
    lates = count_lates(student_id)

    return render_template('student.html',
                           student=user_data[student_id],
                           student_id=student_id,
                           records=records,
                           lates=lates)

@app.route('/warnings')
def warnings():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    warnings = []
    user_data = load_user_data()
    for student_id in user_data:
        late_count = count_lates(student_id)
        if late_count >= 3:
            warnings.append({
                'student': user_data[student_id],
                'late_count': late_count,
                'student_id': student_id
            })

    return render_template('warnings.html', warnings=warnings)


@app.route('/search', methods=['GET'])
def search():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    query = request.args.get('q', '')
    search_type = request.args.get('type', 'students')

    results = []
    if query:
        user_data = load_user_data()

        if search_type == 'students':
            # Search through students
            for student_id, data in user_data.items():
                if (query.lower() in data['name'].lower() or
                        query.lower() in student_id.lower() or
                        query.lower() in data['department'].lower()):
                    results.append({
                        'student_id': student_id,
                        **data
                    })
        else:
            # Search through attendance records
            for file in get_attendance_files():
                with open(file, 'r') as f:
                    data = json.load(f)
                    for date, entries in data.items():
                        for student_id, entry in entries.items():
                            if (query.lower() in entry['name'].lower() or
                                    query.lower() in student_id.lower() or
                                    query.lower() in entry['department'].lower()):
                                results.append({
                                    'date': date,
                                    'student_id': student_id,
                                    **entry
                                })

            # Sort attendance results by date
            results = sorted(results, key=lambda x: x['date'], reverse=True)

    return render_template('search.html',
                           query=query,
                           search_type=search_type,
                           results=results)
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

def create_attendance_entry(student_id, status):
    user_data = load_user_data()
    if student_id in user_data:
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"attendance_{date_str}.json"

        entry = {
            student_id: {
                'name': user_data[student_id]['name'],
                'department': user_data[student_id]['department'],
                'time': datetime.now().strftime("%H:%M:%S"),
                'status': status
            }
        }

        if os.path.exists(filename):
            with open(filename, 'r') as f:
                data = json.load(f)
            data.setdefault(date_str, {}).update(entry)
        else:
            data = {date_str: entry}

        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
