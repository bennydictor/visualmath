from flask.cli import with_appcontext
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.hybrid import hybrid_property
from werkzeug.security import generate_password_hash, check_password_hash
import click
import enum


db = SQLAlchemy()

admins = db.Table('admins', db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True))

teachers = db.Table('teachers',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id'), primary_key=True),
)

students = db.Table('students',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id'), primary_key=True),
)

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(128), nullable=False)
    last_name = db.Column(db.String(128), nullable=False)
    middle_name = db.Column(db.String(128), nullable=False)
    university = db.Column(db.String(1024), nullable=False)
    university_group = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(1024), unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)

    sessions = db.relationship('Session')
    teaches = db.relationship('Course', secondary=teachers)
    studies = db.relationship('Course', secondary=students)
    created_lectures = db.relationship('Lecture')
    created_modules = db.relationship('Module')
    started_lectures = db.relationship('StartedLecture')
    responses = db.relationship('QuestionResponse')

    def __init__(self, *, password=None, **kwargs):
        if password is not None:
            password = generate_password_hash(password)
        super().__init__(password=password, **kwargs)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    @hybrid_property
    def admin(self):
        return db.session.execute(admins.select().where(admins.c.user_id == self.id)).fetchone() is not None

    @admin.setter
    def admin(self, value):
        a = self.admin
        if value and not a:
            db.session.execute(admins.insert().values((self.id,)))
        elif not value and a:
            db.session.execute(admins.delete().where(admins.c.user_id == self.id))

class Session(db.Model):
    __tablename__ = 'sessions'
    id = db.Column(db.String, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    user = db.relationship('User')

class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False, unique=True)

    teachers = db.relationship('User', secondary=teachers)
    students = db.relationship('User', secondary=students)
    lectures = db.relationship('Lecture')
    modules = db.relationship('Module')

lecture_modules = db.Table('lecture_modules',
    db.Column('lecture_id', db.Integer, db.ForeignKey('lectures.id', ondelete='cascade'), primary_key=True),
    db.Column('number', db.Integer, primary_key=True),
    db.Column('module_id', db.Integer, db.ForeignKey('modules.id', ondelete='cascade'), nullable=False),
)

lecture_questions = db.Table('lecture_questions',
    db.Column('lecture_id', db.Integer, db.ForeignKey('lectures.id', ondelete='cascade'), primary_key=True),
    db.Column('number', db.Integer, primary_key=True),
    db.Column('question_id', db.Integer, db.ForeignKey('questions.id', ondelete='cascade'), nullable=False),
)

class QuestionType(enum.Enum):
    multiple_choice = 1
    multiple_select = 2
    free_response = 3

class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(QuestionType), nullable=False)

    multiple_choice_question = db.relationship('MultipleChoiceQuestion')
    multiple_choice_question_variants = db.relationship('MultipleChoiceQuestionVariant', order_by='multiple_choice_question_variants.c.number')
    multiple_select_question_variants = db.relationship('MultipleSelectQuestionVariant', order_by='multiple_select_question_variants.c.number')
    free_response_question = db.relationship('FreeResponseQuestion')

class MultipleChoiceQuestion(db.Model):
    __tablename__ = 'multiple_choice_questions'

    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='cascade'), primary_key=True)
    correct_answer = db.Column(db.Integer, nullable=False)

    question = db.relationship('Question')

class MultipleChoiceQuestionVariant(db.Model):
    __tablename__ = 'multiple_choice_question_variants'

    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='cascade'), primary_key=True)
    number = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String, nullable=False)

    question = db.relationship('Question')

class MultipleSelectQuestionVariant(db.Model):
    __tablename__ = 'multiple_select_question_variants'

    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='cascade'), primary_key=True)
    number = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String, nullable=False)
    correct = db.Column(db.Boolean, nullable=False)

    question = db.relationship('Question')

class FreeResponseQuestionChecker(enum.Enum):
    exact_match = 1

class FreeResponseQuestion(db.Model):
    __tablename__ = 'free_response_questions'

    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='cascade'), primary_key=True)
    correct_answer = db.Column(db.String, nullable=False)
    checker = db.Column(db.Enum(FreeResponseQuestionChecker), nullable=False)

    question = db.relationship('Question')

test_block_modules = db.Table('test_block_modules',
    db.Column('test_block_id', db.Integer, db.ForeignKey('modules.id', ondelete='cascade'), primary_key=True),
    db.Column('number', db.Integer, primary_key=True),
    db.Column('module_id', db.Integer, db.ForeignKey('modules.id'), nullable=False),
)

class ModuleType(enum.Enum):
    text = 1
    visual = 2
    test_block = 3

class Module(db.Model):
    __tablename__ = 'modules'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    type = db.Column(db.Enum(ModuleType), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)

    author = db.relationship('User')
    course = db.relationship('Course')
    text_module = db.relationship('TextModule')
    test_block_modules = db.relationship('Module',
        secondary = test_block_modules,
        primaryjoin = id == test_block_modules.c.test_block_id,
        secondaryjoin = id == test_block_modules.c.module_id
    )

class TextModule(db.Model):
    __tablename__ = 'text_modules'

    module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='cascade'), primary_key=True)
    text = db.Column(db.String, nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=True)

    module = db.relationship('Module')
    question = db.relationship('Question')

class Lecture(db.Model):
    __tablename__ = 'lectures'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)

    author = db.relationship('User')
    course = db.relationship('Course')

    modules = db.relationship('Module', secondary=lecture_modules, order_by=lecture_modules.c.number)
    questions = db.relationship('Question', secondary=lecture_questions, order_by=lecture_questions.c.number)

    @hybrid_property
    def modules_without_questions(self):
        return [m for m in self.modules if not (m.type == ModuleType.test_block or (m.type == ModuleType.text and m.text_module[0].question is not None))]

class StartedLecture(db.Model):
    __tablename__ = 'started_lectures'

    id = db.Column(db.Integer, primary_key=True)
    lecture_id = db.Column(db.Integer, db.ForeignKey('lectures.id'), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    current_module_number = db.Column(db.Integer, nullable=True)
    current_module_started = db.Column(db.Boolean, nullable=True)

    lecture = db.relationship('Lecture')
    lecturer = db.relationship('User')
    responses = db.relationship('QuestionResponse')

    @hybrid_property
    def active(self):
        return self.current_module_number is not None

    @hybrid_property
    def current_module(self):
        mod = db.session.query(Module) \
            .join(lecture_modules, lecture_modules.c.module_id == Module.id) \
            .filter(lecture_modules.c.lecture_id == self.lecture_id) \
            .filter(lecture_modules.c.number == self.current_module_number).one_or_none()
        return mod

class QuestionResponse(db.Model):
    __tablename__ = 'question_responses'

    started_lecture_id = db.Column(db.Integer, db.ForeignKey('started_lectures.id'), primary_key=True)
    question_number = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    response = db.Column(db.String, nullable=True)
    correct = db.Column(db.Boolean, nullable=True)

    started_lecture = db.relationship('StartedLecture')
    user = db.relationship('User')

    @hybrid_property
    def question(self):
        return db.session.query(Question) \
            .join(lecture_questions, lecture_questions.c.question_id == Question.id) \
            .filter(lecture_questions.c.lecture_id == self.started_lecture.lecture_id) \
            .filter(lecture_questions.c.number == self.question_number).one_or_none()


def init_app(app):
    db.init_app(app)
    app.cli.add_command(init_db)

@click.command('init-db')
@click.option('--password', prompt='admin password', hide_input=True, confirmation_prompt=True)
@with_appcontext
def init_db(password):
    db.drop_all()
    db.create_all()

    u = User(first_name='Lucius', last_name='User', middle_name='Q.', university='', university_group='', email='admin@visualmath.ru', password=password, admin=True)
    db.session.add(u)
    db.session.commit()
