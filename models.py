from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notices = db.relationship("Notice", backref="owner", cascade="all, delete-orphan")
    tasks = db.relationship("Task", backref="owner", cascade="all, delete-orphan")
    notifications = db.relationship("Notification", backref="owner", cascade="all, delete-orphan")
    chats = db.relationship("ChatMessage", backref="owner", cascade="all, delete-orphan")

class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(220), nullable=False)
    category = db.Column(db.String(60), default="Other")
    original_filename = db.Column(db.String(255))
    stored_filename = db.Column(db.String(255))
    source_type = db.Column(db.String(30), default="text")
    extracted_text = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, default="")
    venue = db.Column(db.String(220), default="")
    priority = db.Column(db.String(20), default="Medium")
    event_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tasks = db.relationship("Task", backref="notice", cascade="all, delete-orphan")

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    notice_id = db.Column(db.Integer, db.ForeignKey("notice.id"), nullable=True)
    title = db.Column(db.String(220), nullable=False)
    description = db.Column(db.Text, default="")
    category = db.Column(db.String(60), default="Other")
    due_date = db.Column(db.DateTime, nullable=True)
    priority = db.Column(db.String(20), default="Medium")
    status = db.Column(db.String(30), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(220), nullable=False)
    message = db.Column(db.Text, default="")
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
