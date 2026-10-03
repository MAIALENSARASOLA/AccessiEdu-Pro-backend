# AccessiEdu Pro - Backend

Este es el backend de AccessiEdu Pro, mi proyecto final del bootcamp de Full Stack. Es una API en Flask donde se guardan las tareas que crea el profesorado y las adaptaciones de cada una.

- API: https://accessiedu-pro-backend.onrender.com
- Web: https://accessiedu-pro.netlify.app
- Repo del frontend: https://github.com/MAIALENSARASOLA/AccessiEdu-Pro

Ojo: el backend está en el plan gratuito de Render y se duerme si nadie lo usa. La primera vez puede tardar hasta un minuto en responder.

## Con qué está hecho

Python, Flask, Flask-SQLAlchemy y Flask-CORS. En mi ordenador uso SQLite y en producción PostgreSQL en Neon. Lo tengo desplegado en Render con Gunicorn.

## Las tablas

Son dos:

- Task: id, title, subject, course, difficulty, instructions
- Adaptation: id, task_id, type, content

Cada adaptación va unida a su tarea con task_id, que es una clave foránea. Así una misma tarea puede tener varias versiones adaptadas (lectura simplificada, apoyo visual, menos ejercicios...).

## Rutas

Tareas:
- GET /tasks
- GET /tasks/<id>
- POST /tasks
- PUT /tasks/<id>
- DELETE /tasks/<id>

Adaptaciones:
- GET /tasks/<task_id>/adaptations
- POST /tasks/<task_id>/adaptations
- GET /adaptations/<id>
- PUT /adaptations/<id>
- DELETE /adaptations/<id>

## Cómo arrancarlo en local

```
git clone https://github.com/MAIALENSARASOLA/AccessiEdu-Pro-backend.git
cd AccessiEdu-Pro-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Se abre en http://localhost:5000. Si no está la variable DATABASE_URL, tira de SQLite.

## Problemas que me encontré y cómo los resolví

**Las tareas desaparecían en Render.** Al principio usaba SQLite también en producción, pero el disco gratuito de Render no es permanente y cada vez que el servidor se reiniciaba se perdía todo. Lo pasé a PostgreSQL en Neon y puse la conexión en una variable de entorno (DATABASE_URL) para no dejar la contraseña en el código. Al desplegar me salió un error con el driver, lo vi en los logs y lo arreglé cambiando a psycopg 3, que es el que pide SQLAlchemy 2.1.

**Neon se apaga cuando no se usa.** Para que la primera consulta no falle, añadí pool_pre_ping, que comprueba que la conexión sigue viva antes de usarla.

**Error 500 al borrar una tarea.** Si la tarea tenía adaptaciones, la base de datos no la dejaba borrar porque seguían apuntando a ella. Ahora primero borro sus adaptaciones y después la tarea.

**Las tablas no se creaban en Render.** En local arrancaba con python app.py, pero Render usa Gunicorn y nunca entraba en el if __name__ == '__main__', así que db.create_all() no se ejecutaba. Lo saqué fuera de ese bloque.

Lo de PostgreSQL, Neon, las variables de entorno y el despliegue en Render no lo vimos en el curso (allí usamos SQLite, MySQL y Heroku). Lo aprendí por mi cuenta mientras lo desplegaba.

## Autora

Maialen Sarasola