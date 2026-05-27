from core.database import get_db
from user_management.models import UserModel


class UserRepository:
    def __init__(self):
        self.db = get_db()

    def get(self, user_id):
        return self.db.query(UserModel).filter_by(id=user_id).first()

    def delete(self, user_id):
        self.db.query(UserModel).filter_by(id=user_id).delete()
        self.db.commit()
