from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
DATABASE = 'fitness.db'


def get_db():
    """Open a connection to the database. This function gets called
    every time we need to read or write data."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Lets us access columns by name: row['exercise']
    conn.execute("PRAGMA foreign_keys = ON")  # Add this line
    return conn


def init_db():
    """Create the workouts table if it doesn't exist yet.
    This runs once when the app starts."""
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER NOT NULL,
            exercise_id INTEGER NOT NULL,
            set_number INTEGER NOT NULL,
            weight INTEGER,
            reps INTEGER,
            duration INTEGER,
            FOREIGN KEY (workout_id) REFERENCES workouts(id),
            FOREIGN KEY (exercise_id) REFERENCES exercises(id)
        )
    ''')
    
    conn.commit()
    conn.close()


@app.route('/')
def index():
    conn = get_db()
    workouts = conn.execute(
        'SELECT * FROM workouts ORDER BY date DESC'
    ).fetchall()
    conn.close()
    return render_template('index.html', workouts=workouts)


@app.route('/workout/new', methods=['GET', 'POST'])
def add_workout():
    if request.method == 'POST':
        date = request.form.get('date')
        if date:
            conn = get_db()
            cursor = conn.execute('INSERT INTO workouts (date) VALUES (?)', (date,))
            workout_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return redirect(url_for('build_workout', workout_id=workout_id))
    return render_template('add_workout.html')

@app.route('/workout/<int:workout_id>/build')
def build_workout(workout_id):
    conn = get_db()
    workout = conn.execute('SELECT * FROM workouts WHERE id = ?', (workout_id,)).fetchone()
    conn.close()
    return render_template('build_workout.html', workout=workout)

@app.route('/workout/<int:workout_id>/save', methods=['POST'])
def save_workout(workout_id):
    data = request.get_json()
    conn = get_db()

    for exercise_data in data.get('exercises', []):
        exercise_name = exercise_data['name']

        # Get or create exercise
        conn.execute(
            'INSERT OR IGNORE INTO exercises (name) VALUES (?)',
            (exercise_name,)
        )
        row = conn.execute(
            'SELECT id FROM exercises WHERE name = ?',
            (exercise_name,)
        ).fetchone()
        exercise_id = row['id']

        # Delete existing sets for this exercise in this workout
        # (in case they're re-saving)
        conn.execute(
            'DELETE FROM sets WHERE workout_id = ? AND exercise_id = ?',
            (workout_id, exercise_id)
        )

        # Insert the new sets
        for i, set_data in enumerate(exercise_data.get('sets', [])):
            conn.execute(
                'INSERT INTO sets (workout_id, exercise_id, set_number, weight, reps, duration) VALUES (?, ?, ?, ?, ?, ?)',
                (workout_id, exercise_id, i + 1, 
                    set_data.get('weight'), 
                    set_data.get('reps'), 
                    set_data.get('duration'))
            )

    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/workout/<int:workout_id>')
def view_workout(workout_id):
    conn = get_db()

    # Step 1: Get the workout
    workout = conn.execute(
        'SELECT * FROM workouts WHERE id = ?',
        (workout_id,)
    ).fetchone()

    # Step 2: Get all exercises in this workout (via sets, grouped by exercise)
    exercises = conn.execute('''
        SELECT DISTINCT e.id, e.name
        FROM sets s
        JOIN exercises e ON s.exercise_id = e.id
        WHERE s.workout_id = ?
        ORDER BY e.name
    ''', (workout_id,)).fetchall()

    # Step 3: For each exercise, get its sets
    exercise_data = []
    for exercise in exercises:
        sets = conn.execute('''
            SELECT set_number, weight, reps, duration
            FROM sets
            WHERE workout_id = ? AND exercise_id = ?
            ORDER BY set_number
        ''', (workout_id, exercise['id'])).fetchall()

        exercise_data.append({
            'id': exercise['id'],
            'name': exercise['name'],
            'sets': sets
        })

    conn.close()

    return render_template(
        'view_workout.html',
        workout=workout,
        exercise_data=exercise_data
    )

@app.route('/workout/<int:workout_id>/data')
def get_workout_data(workout_id):
    conn = get_db()

    exercises = conn.execute('''
        SELECT DISTINCT e.id, e.name
        FROM sets s
        JOIN exercises e ON s.exercise_id = e.id
        WHERE s.workout_id = ?
    ''', (workout_id,)).fetchall()

    exercise_list = []
    for exercise in exercises:
        sets = conn.execute('''
            SELECT weight, reps, duration
            FROM sets
            WHERE workout_id = ? AND exercise_id = ?
            ORDER BY set_number
        ''', (workout_id, exercise['id'])).fetchall()

        set_list = []
        for s in sets:
            set_list.append({
                'weight': s['weight'],
                'reps': s['reps'],
                'duration': s['duration']
            })

        exercise_list.append({
            'name': exercise['name'],
            'sets': set_list
        })

    conn.close()
    return jsonify({'exercises': exercise_list})

@app.route('/workout/<int:workout_id>/exercise/<int:exercise_id>/delete', methods=['POST'])
def delete_exercise(workout_id, exercise_id):
    conn = get_db()
    conn.execute(
        'DELETE FROM sets WHERE workout_id = ? AND exercise_id = ?',
        (workout_id, exercise_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for('build_workout', workout_id=workout_id))

if __name__ == '__main__':
    init_db()  # Create the table on startup
    app.run(debug=True)