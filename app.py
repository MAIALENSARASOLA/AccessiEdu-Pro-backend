from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Configuración de la base de datos SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///accessiedu.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------------------
# MODELOS (TABLAS)
# ---------------------------

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(100))
    course = db.Column(db.String(100))
    difficulty = db.Column(db.String(50))
    instructions = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'subject': self.subject,
            'course': self.course,
            'difficulty': self.difficulty,
            'instructions': self.instructions
        }


class Adaptation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    type = db.Column(db.String(100))       # ej: "Lectura simplificada", "Apoyo visual"
    content = db.Column(db.Text)           # el contenido/instrucciones de esa adaptación

    # Relación: permite acceder a adaptation.task para ver la tarea original
    task = db.relationship('Task', backref=db.backref('adaptations', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'type': self.type,
            'content': self.content
        }

# ---------------------------
# RUTAS (CRUD) - TASKS
# ---------------------------

@app.route('/tasks', methods=['GET'])
def get_tasks():
    tasks = Task.query.all()
    return jsonify([task.to_dict() for task in tasks])

@app.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = Task.query.get_or_404(task_id)
    return jsonify(task.to_dict())

@app.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    new_task = Task(
        title=data.get('title'),
        subject=data.get('subject'),
        course=data.get('course'),
        difficulty=data.get('difficulty'),
        instructions=data.get('instructions')
    )
    db.session.add(new_task)
    db.session.commit()
    return jsonify(new_task.to_dict()), 201

@app.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json()
    task.title = data.get('title', task.title)
    task.subject = data.get('subject', task.subject)
    task.course = data.get('course', task.course)
    task.difficulty = data.get('difficulty', task.difficulty)
    task.instructions = data.get('instructions', task.instructions)
    db.session.commit()
    return jsonify(task.to_dict())

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)

    # Borramos primero las adaptaciones asociadas a esta tarea.
    # Si no lo hacemos, la base de datos rechaza el borrado de la tarea
    # porque hay adaptaciones que todavía la referencian (task_id),
    # y eso provoca un error 500.
    Adaptation.query.filter_by(task_id=task.id).delete()

    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Tarea eliminada'})

# ---------------------------
# RUTAS (CRUD) - ADAPTATIONS
# ---------------------------

@app.route('/tasks/<int:task_id>/adaptations', methods=['GET'])
def get_adaptations(task_id):
    # Aseguramos que la tarea existe antes de listar sus adaptaciones
    Task.query.get_or_404(task_id)
    adaptations = Adaptation.query.filter_by(task_id=task_id).all()
    return jsonify([adaptation.to_dict() for adaptation in adaptations])

@app.route('/adaptations/<int:adaptation_id>', methods=['GET'])
def get_adaptation(adaptation_id):
    adaptation = Adaptation.query.get_or_404(adaptation_id)
    return jsonify(adaptation.to_dict())

@app.route('/tasks/<int:task_id>/adaptations', methods=['POST'])
def create_adaptation(task_id):
    # Aseguramos que la tarea existe antes de crear una adaptación para ella
    Task.query.get_or_404(task_id)
    data = request.get_json()
    new_adaptation = Adaptation(
        task_id=task_id,
        type=data.get('type'),
        content=data.get('content')
    )
    db.session.add(new_adaptation)
    db.session.commit()
    return jsonify(new_adaptation.to_dict()), 201

@app.route('/adaptations/<int:adaptation_id>', methods=['PUT'])
def update_adaptation(adaptation_id):
    adaptation = Adaptation.query.get_or_404(adaptation_id)
    data = request.get_json()
    adaptation.type = data.get('type', adaptation.type)
    adaptation.content = data.get('content', adaptation.content)
    db.session.commit()
    return jsonify(adaptation.to_dict())

@app.route('/adaptations/<int:adaptation_id>', methods=['DELETE'])
def delete_adaptation(adaptation_id):
    adaptation = Adaptation.query.get_or_404(adaptation_id)
    db.session.delete(adaptation)
    db.session.commit()
    return jsonify({'message': 'Adaptación eliminada'})

# ---------------------------
# ARRANQUE
# ---------------------------

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)