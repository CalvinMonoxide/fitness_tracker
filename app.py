from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Temporary storage — we'll replace this with a database soon
workouts = []

@app.route('/')
def index():
    return render_template('index.html', workouts=workouts)

@app.route('/add', methods=['GET', 'POST'])
def add_workout():
    if request.method == 'POST':
        exercise = request.form.get('exercise')
        duration = request.form.get('duration')
        date = request.form.get('date')

        if exercise and duration and date:
            workouts.append({
                'exercise': exercise,
                'duration': int(duration),
                'date': date
            })
            return redirect(url_for('index'))

    return render_template('add_workout.html')

if __name__ == '__main__':
    app.run(debug=True)