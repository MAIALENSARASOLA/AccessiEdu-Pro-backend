import os
import sys

import pytest

# Los tests usan una base de datos SQLite temporal, nunca la de Neon.
os.environ['DATABASE_URL'] = 'sqlite:///test_accessiedu.db'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db  # noqa: E402


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.session.remove()
        db.drop_all()
