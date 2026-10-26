import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Configuración de la base de datos
# En Render uso PostgreSQL (Neon). La direccion la leo de la variable DATABASE_URL
# para no poner la contraseña en el codigo.
# En mi ordenador esa variable no existe, asi que sigo usando SQLite.
database_url = os.environ.get('DATABASE_URL')

if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///accessiedu.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Neon apaga la base de datos cuando no se usa.
# Con esto se comprueba que la conexion sigue viva antes de hacer una consulta.
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}

db = SQLAlchemy(app)

# ---------------------------
# VALIDACIÓN EN EL SERVIDOR
# ---------------------------
# No me fío solo del formulario de React: cualquiera podría llamar a la API
# directamente. Por eso el servidor comprueba los datos antes de guardarlos.

TASK_LIMITS = {'title': 200, 'subject': 100, 'course': 100, 'difficulty': 50}
VALID_DIFFICULTIES = ['Fácil', 'Media', 'Difícil']
ADAPTATION_TYPE_LIMIT = 100


def error_response(message, status=400):
    return jsonify({'error': message}), status


def read_json():
    # Devuelve el JSON recibido o None si no es un objeto JSON válido
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None
    return data


def clean_text(value):
    # Quita espacios al principio y al final; si no es texto, lo deja como None
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    return value.strip()


def validate_task(data, partial=False):
    # partial=True se usa al editar (PUT): solo se validan los campos que llegan
    if not partial or 'title' in data:
        title = clean_text(data.get('title'))
        if not title:
            return 'El título es obligatorio.'

    for field, limit in TASK_LIMITS.items():
        if field in data and data[field] is not None:
            if not isinstance(data[field], str):
                return f'El campo {field} tiene que ser texto.'
            if len(data[field].strip()) > limit:
                return f'El campo {field} no puede tener más de {limit} caracteres.'

    if 'instructions' in data and data['instructions'] is not None:
        if not isinstance(data['instructions'], str):
            return 'Las instrucciones tienen que ser texto.'

    difficulty = data.get('difficulty')
    if difficulty and difficulty not in VALID_DIFFICULTIES:
        return 'La dificultad tiene que ser Fácil, Media o Difícil.'

    return None


def validate_adaptation(data, partial=False):
    for field in ['type', 'content']:
        if not partial or field in data:
            if not clean_text(data.get(field)):
                return 'El tipo y el contenido de la adaptación son obligatorios.'

    adaptation_type = clean_text(data.get('type'))
    if adaptation_type and len(adaptation_type) > ADAPTATION_TYPE_LIMIT:
        return f'El tipo no puede tener más de {ADAPTATION_TYPE_LIMIT} caracteres.'

    return None


# Errores en JSON (y no en HTML) para que el frontend los pueda leer
@app.errorhandler(404)
def not_found(error):
    return error_response('No encontrado', 404)


@app.errorhandler(405)
def method_not_allowed(error):
    return error_response('Método no permitido', 405)

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
    tasks = Task.query.order_by(Task.id).all()
    return jsonify([task.to_dict() for task in tasks])

@app.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = db.get_or_404(Task, task_id)
    return jsonify(task.to_dict())

@app.route('/tasks', methods=['POST'])
def create_task():
    data = read_json()
    if data is None:
        return error_response('Hay que enviar los datos en formato JSON.')

    error = validate_task(data)
    if error:
        return error_response(error)

    new_task = Task(
        title=clean_text(data.get('title')),
        subject=clean_text(data.get('subject')),
        course=clean_text(data.get('course')),
        difficulty=data.get('difficulty') or 'Fácil',
        instructions=clean_text(data.get('instructions'))
    )
    db.session.add(new_task)
    db.session.commit()
    return jsonify(new_task.to_dict()), 201

@app.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task = db.get_or_404(Task, task_id)
    data = read_json()
    if data is None:
        return error_response('Hay que enviar los datos en formato JSON.')

    error = validate_task(data, partial=True)
    if error:
        return error_response(error)

    for field in ['title', 'subject', 'course', 'instructions']:
        if field in data:
            setattr(task, field, clean_text(data[field]))
    if data.get('difficulty'):
        task.difficulty = data['difficulty']
    db.session.commit()
    return jsonify(task.to_dict())

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = db.get_or_404(Task, task_id)

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
    db.get_or_404(Task, task_id)
    adaptations = Adaptation.query.filter_by(task_id=task_id).order_by(Adaptation.id).all()
    return jsonify([adaptation.to_dict() for adaptation in adaptations])

@app.route('/adaptations/<int:adaptation_id>', methods=['GET'])
def get_adaptation(adaptation_id):
    adaptation = db.get_or_404(Adaptation, adaptation_id)
    return jsonify(adaptation.to_dict())

@app.route('/tasks/<int:task_id>/adaptations', methods=['POST'])
def create_adaptation(task_id):
    # Aseguramos que la tarea existe antes de crear una adaptación para ella
    db.get_or_404(Task, task_id)
    data = read_json()
    if data is None:
        return error_response('Hay que enviar los datos en formato JSON.')

    error = validate_adaptation(data)
    if error:
        return error_response(error)

    new_adaptation = Adaptation(
        task_id=task_id,
        type=clean_text(data.get('type')),
        content=clean_text(data.get('content'))
    )
    db.session.add(new_adaptation)
    db.session.commit()
    return jsonify(new_adaptation.to_dict()), 201

@app.route('/adaptations/<int:adaptation_id>', methods=['PUT'])
def update_adaptation(adaptation_id):
    adaptation = db.get_or_404(Adaptation, adaptation_id)
    data = read_json()
    if data is None:
        return error_response('Hay que enviar los datos en formato JSON.')

    error = validate_adaptation(data, partial=True)
    if error:
        return error_response(error)

    if 'type' in data:
        adaptation.type = clean_text(data['type'])
    if 'content' in data:
        adaptation.content = clean_text(data['content'])
    db.session.commit()
    return jsonify(adaptation.to_dict())

@app.route('/adaptations/<int:adaptation_id>', methods=['DELETE'])
def delete_adaptation(adaptation_id):
    adaptation = db.get_or_404(Adaptation, adaptation_id)
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