from uuid import uuid4, UUID
from sqlalchemy_utils import UUIDType
import hashlib
import os
from base64 import b64encode, b64decode

from backend.db import db

from datetime import datetime, timedelta

roles = ("admin", "customer", "employee")

class Session(db.Model):
    __tablename__ = 'session'

    id = db.Column(UUIDType(), primary_key=True)
    uid = db.Column(UUIDType(),db.ForeignKey('user.id'),nullable=False)
    user = db.relationship('User', backref=db.backref('sessions', lazy=True))
    expire = db.Column(db.DateTime(), nullable=False)

    @staticmethod
    def new_session(username, expire=None) -> 'Session':
        if expire == None:
            expire = datetime.now() + timedelta(hours=3)
        if type(expire) in (int, float):
            expire = datetime.fromtimestamp(expire)

        user = User.get_by_username(username)
        return Session(
            id=uuid4(),
            user=user,
            expire=expire,
        )
    
    @staticmethod
    def get_by_id(id) -> 'Session':
        if type(id) != UUID:
            try:
                id = UUID(id)
            except:
                raise AttributeError("Invalid UUID")

        query = Session.query.filter_by(id=id)

        if query.count() == 0:
            raise ValueError(f"Session {str(id)} not found.")

        session = query.first()

        if session.expired():
            db.session.delete(session)
            db.session.commit()
            raise ValueError(f"Session {str(id)} not found.")
        
        return session

    def json(self) -> dict:
        return {
            "id": str(self.id),
            "user": self.user.json(),
            "expire": int(self.expire.timestamp()),
        }
    
    def expired(self) -> bool:
        return self.expire < datetime.now()

class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(UUIDType(), primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    hash = db.Column(db.BINARY(32), nullable=False)
    salt = db.Column(db.BINARY(32), nullable=False)
    role = db.Column(db.String(10), nullable=False)

    @staticmethod
    def new_user(username, password, role="customer") -> 'User':
        if not role in roles:
            raise ValueError(f"Invalid role '{role}'")

        hash, salt = User.create_hash(password)
        return User(
            id = uuid4(),
            username = username, 
            hash = hash, 
            salt = salt,
            role = role
        )
    
    @staticmethod
    def new_user_with_id(uid, username, password, role="customer") -> 'User':
        if not role in roles:
            raise ValueError(f"Invalid role '{role}'")

        hash, salt = User.create_hash(password)
        return User(
            id = UUID(uid),
            username = username, 
            hash = hash, 
            salt = salt,
            role = role,
        )

    @staticmethod
    def create_hash(password, salt=None) -> (bytes, bytes):
        if salt == None:
            salt = os.urandom(32)

        hash = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt, 
            100000
        )
        return hash, salt
    
    @staticmethod
    def username_available(username) -> bool:
        result = User.query.filter_by(username = username).all()
        return len(result) == 0

    def check_password(self, password) -> bool:
        input_hash, salt = User.create_hash(password, self.salt)
        return self.hash == input_hash
        
    def json(self) -> dict:
        return {
            "id": str(self.id),
            "username": self.username,
            "role": self.role
        }
    
    @staticmethod
    def get_by_id(id) -> 'User':
        if type(id) != UUID:
            try:
                id = UUID(id)
            except:
                raise AttributeError("Invalid UUID")

        query = User.query.filter_by(id=id)

        if query.count() == 0:
            raise ValueError(f"User {str(id)} not found.")

        return query.first()
    
    @staticmethod
    def get_by_username(username) -> 'User':
        query = User.query.filter_by(username=username)

        if query.count() == 0:
            raise ValueError(f"User '{username}' not found.")

        return query.first()
    
    @staticmethod
    def get_by_role(role) -> 'User':
        query = User.query.filter_by(role=role)
        return query.all()