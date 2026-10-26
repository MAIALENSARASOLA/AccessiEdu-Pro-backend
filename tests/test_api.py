def create_task(client, **overrides):
    data = {
        'title': 'El faro',
        'subject': 'Lengua',
        'course': '4º Primaria',
        'difficulty': 'Media',
        'instructions': 'Lee el texto y contesta las preguntas.',
    }
    data.update(overrides)
    return client.post('/tasks', json=data)


# ---------- TAREAS ----------

def test_lista_vacia_al_empezar(client):
    response = client.get('/tasks')
    assert response.status_code == 200
    assert response.get_json() == []


def test_crear_tarea(client):
    response = create_task(client)
    assert response.status_code == 201
    task = response.get_json()
    assert task['id'] == 1
    assert task['title'] == 'El faro'
    assert client.get('/tasks').get_json()[0]['title'] == 'El faro'


def test_crear_tarea_quita_espacios(client):
    task = create_task(client, title='  El faro  ').get_json()
    assert task['title'] == 'El faro'


def test_no_deja_crear_tarea_sin_titulo(client):
    response = create_task(client, title='   ')
    assert response.status_code == 400
    assert 'título' in response.get_json()['error']
    assert client.get('/tasks').get_json() == []


def test_no_deja_crear_tarea_sin_json(client):
    response = client.post('/tasks', data='hola', content_type='text/plain')
    assert response.status_code == 400


def test_no_deja_dificultad_inventada(client):
    response = create_task(client, difficulty='Imposible')
    assert response.status_code == 400


def test_no_deja_titulo_demasiado_largo(client):
    response = create_task(client, title='a' * 201)
    assert response.status_code == 400


def test_ver_una_tarea(client):
    create_task(client)
    response = client.get('/tasks/1')
    assert response.status_code == 200
    assert response.get_json()['subject'] == 'Lengua'


def test_tarea_que_no_existe_da_404_en_json(client):
    response = client.get('/tasks/99')
    assert response.status_code == 404
    assert 'error' in response.get_json()


def test_editar_tarea(client):
    create_task(client)
    response = client.put('/tasks/1', json={'title': 'El faro (revisada)'})
    assert response.status_code == 200
    task = response.get_json()
    assert task['title'] == 'El faro (revisada)'
    assert task['subject'] == 'Lengua'  # lo que no se envía no cambia


def test_no_deja_vaciar_el_titulo_al_editar(client):
    create_task(client)
    response = client.put('/tasks/1', json={'title': ''})
    assert response.status_code == 400
    assert client.get('/tasks/1').get_json()['title'] == 'El faro'


def test_borrar_tarea(client):
    create_task(client)
    response = client.delete('/tasks/1')
    assert response.status_code == 200
    assert client.get('/tasks/1').status_code == 404


def test_borrar_tarea_con_adaptaciones(client):
    # Antes daba error 500: ahora se borran primero sus adaptaciones
    create_task(client)
    client.post('/tasks/1/adaptations', json={'type': 'Apoyo visual', 'content': 'Con dibujos'})
    response = client.delete('/tasks/1')
    assert response.status_code == 200
    assert client.get('/adaptations/1').status_code == 404


# ---------- ADAPTACIONES ----------

def test_crear_y_listar_adaptaciones(client):
    create_task(client)
    response = client.post('/tasks/1/adaptations', json={
        'type': 'Lectura simplificada',
        'content': 'Texto corto con frases sencillas.',
    })
    assert response.status_code == 201
    adaptations = client.get('/tasks/1/adaptations').get_json()
    assert len(adaptations) == 1
    assert adaptations[0]['task_id'] == 1


def test_no_deja_adaptacion_vacia(client):
    create_task(client)
    response = client.post('/tasks/1/adaptations', json={'type': 'Apoyo visual', 'content': ' '})
    assert response.status_code == 400


def test_no_deja_adaptar_tarea_que_no_existe(client):
    response = client.post('/tasks/5/adaptations', json={'type': 'Apoyo visual', 'content': 'x'})
    assert response.status_code == 404


def test_editar_adaptacion(client):
    create_task(client)
    client.post('/tasks/1/adaptations', json={'type': 'Apoyo visual', 'content': 'Con dibujos'})
    response = client.put('/adaptations/1', json={'content': 'Con pictogramas'})
    assert response.status_code == 200
    assert response.get_json()['content'] == 'Con pictogramas'
    assert response.get_json()['type'] == 'Apoyo visual'


def test_no_deja_vaciar_adaptacion_al_editar(client):
    create_task(client)
    client.post('/tasks/1/adaptations', json={'type': 'Apoyo visual', 'content': 'Con dibujos'})
    response = client.put('/adaptations/1', json={'content': ''})
    assert response.status_code == 400


def test_borrar_adaptacion(client):
    create_task(client)
    client.post('/tasks/1/adaptations', json={'type': 'Apoyo visual', 'content': 'Con dibujos'})
    response = client.delete('/adaptations/1')
    assert response.status_code == 200
    assert client.get('/tasks/1/adaptations').get_json() == []
