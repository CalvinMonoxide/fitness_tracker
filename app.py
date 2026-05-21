from flask import Flask, render_template, request, redirect, url_for
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
            cursor = conn.execute('INSERT INTO workouts (date) VALUES (?)',
                (date,)
            )
            workout_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return redirect(url_for('add_exercise', workout_id=workout_id))

    return render_template('add_workout.html')


@app.route('/workout/<int:workout_id>/add', methods=['GET', 'POST'])
def add_exercise(workout_id):
    if request.method == 'POST':
        exercise_name = request.form.get('exercise')
        num_sets = request.form.get('sets')

        if exercise_name and num_sets:
            conn = get_db()

            conn.execute(
                'INSERT OR IGNORE INTO exercises (name) VALUES (?)',
                (exercise_name,)
            )

            row = conn.execute(
                'SELECT id FROM exercises WHERE name = ?',
                (exercise_name,)
            ).fetchone()
            exercise_id = row['id']

            num_sets = int(num_sets)
            for set_num in range(1, num_sets + 1):
                conn.execute(
                    'INSERT INTO sets (workout_id, exercise_id, set_number) VALUES (?, ?, ?)',
                    (workout_id, exercise_id, set_num)
                )

            conn.commit()
            conn.close()
            return redirect(url_for('fill_sets', workout_id=workout_id, exercise_id=exercise_id))

    return render_template('add_exercise.html', workout_id=workout_id)


@app.route('/workout/<int:workout_id>/sets/<int:exercise_id>', methods=['GET', 'POST'])
def fill_sets(workout_id, exercise_id):
    conn = get_db()
    sets = conn.execute(
        'SELECT * FROM sets WHERE workout_id = ? AND exercise_id = ? ORDER BY set_number',
        (workout_id, exercise_id)
    ).fetchall()

    exercise_row = conn.execute(
        'SELECT name FROM exercises WHERE id = ?',
        (exercise_id,)
    ).fetchone()
    exercise_name = exercise_row['name']
    conn.close()

    if request.method == 'POST':
        conn = get_db()
        for set_num in range(1, len(sets) + 1):
            set_id = request.form.get(f'set_id_{set_num}')
            weight = request.form.get(f'weight_{set_num}')
            reps = request.form.get(f'reps_{set_num}')
            duration = request.form.get(f'duration_{set_num}')

            if set_id:
                weight = int(weight) if weight else None
                reps = int(reps) if reps else None
                duration = int(duration) if duration else None
                conn.execute(
                    'UPDATE sets SET weight=?, reps=?, duration=? WHERE id=?',
                    (weight, reps, duration, set_id)
                )
        conn.commit()
        conn.close()
        return redirect(url_for('add_exercise', workout_id=workout_id))

    return render_template(
        'fill_sets.html',
        sets=sets,
        workout_id=workout_id,
        exercise_id=exercise_id,
        exercise_name=exercise_name
    )

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
            'name': exercise['name'],
            'sets': sets
        })

    conn.close()

    return render_template(
        'view_workout.html',
        workout=workout,
        exercise_data=exercise_data
    )

if __name__ == '__main__':
    init_db()  # Create the table on startup
    app.run(debug=True)