from flask import Flask
from flask_login import LoginManager

from config import settings
from app.db.database import init_db
from app.db.models import User

from app.db.routes import main_blueprint
from app.db.database import session_scope

app = Flask(__name__, template_folder='app/db/templates')
app.config['SECRET_KEY'] = settings.SECRET_KEY
app.register_blueprint(main_blueprint)

login_manager = LoginManager(app)
login_manager.login_view = 'main.login'


@login_manager.user_loader
def load_user(user_id):
    with session_scope() as session:
        user = session.get(User, int(user_id))
        if user:
            session.expunge(user)
        return user


if __name__ == '__main__':
    init_db()
    app.run(port=settings.APP_PORT, debug=settings.DEBUG)
