from . import model
from . import resources

from datetime import datetime
from flask import Blueprint, request, jsonify, url_for
from flask import session as flask_session
from flask_socketio import SocketIO, send, emit, join_room, leave_room
import functools
import jsonschema
import secrets


class NotUnique(Exception):
    def __init__(self, path, value):
        self.path = path
        self.value = value

class NotFound(Exception):
    def __init__(self, path, value):
        self.path = path
        self.value = value

class Unauthorized(Exception): pass

class Forbidden(Exception): pass


bp = Blueprint('api', __name__)
bp_schemas = Blueprint('api_schemas', __name__)

def handler(view=None, *, method=None, route=None, request_schema=None, response_schema=None, authorized=True):
    if view is None:
        return functools.partial(handler, route=route, method=method, request_schema=request_schema, response_schema=response_schema, authorized=authorized)

    if request_schema is not None:
        request_schema_view_route = view.__name__ + '_request_schema'
        request_schema['$schema'] = 'http://json-schema.org/schema#'
        @bp_schemas.route('/' + request_schema_view_route, methods=['GET'], endpoint=request_schema_view_route)
        def request_schema_view():
            request_schema['$id'] = request.url_root[:-1] + url_for('api_schemas.' + request_schema_view_route)
            return jsonify(request_schema)

    if response_schema:
        response_schema_view_route = view.__name__ + '_response_schema'
        response_schema['$schema'] = 'http://json-schema.org/schema#'
        @bp_schemas.route('/' + response_schema_view_route, methods=['GET'], endpoint=response_schema_view_route)
        def response_schema_view():
            response_schema['$id'] = request.url_root[:-1] + url_for('api_schemas.' + response_schema_view_route)
            return jsonify(response_schema)

    @bp.route(route, methods=[method])
    @functools.wraps(view)
    def wrapper(**kwargs):
        if authorized:
            session_id = request.headers.get('Authorization')
            session = model.Session.query.filter_by(id=session_id).one_or_none()
            if session is None:
                return jsonify({'status': 'error', 'error': 'unauthorized'}), 401
            kwargs['user'] = session.user

        if request_schema is not None:
            rq = request.get_json(silent=True)
            try:
                jsonschema.validate(rq, request_schema)
            except jsonschema.exceptions.ValidationError as e:
                return jsonify({'status': 'error', 'error': 'bad_request', 'request_schema': request.url_root[:-1] + url_for('api_schemas.' + request_schema_view_route)}), 400
            kwargs['rq'] = rq

        try:
            model.db.session.execute('PRAGMA foreign_keys = ON;')
            rs = view(**kwargs)
        except NotUnique as e:
            return jsonify({'status': 'error', 'error': 'not_unique', 'path': e.path, 'value': e.value}), 400
        except NotFound as e:
            return jsonify({'status': 'error', 'error': 'not_found', 'path': e.path, 'value': e.value}), 404
        except Forbidden as e:
            return jsonify({'status': 'error', 'error': 'forbidden'}), 403

        if response_schema is not None:
            jsonschema.validate(rs, response_schema)
            rs['status'] = 'ok'
            rs['$schema'] = request.url_root[:-1] + url_for('api_schemas.' + response_schema_view_route)
            return jsonify(rs)
        else:
            return jsonify({'status': 'ok'})

def sio_handler(view=None, *, event=None, request_schema=None):
    if view is None:
        return functools.partial(sio_handler, event=event, request_schema=request_schema)

    if request_schema is not None:
        request_schema_view_route = view.__name__ + '_request_schema'
        request_schema['$schema'] = 'http://json-schema.org/schema#'
        @bp_schemas.route('/' + request_schema_view_route, methods=['GET'], endpoint=request_schema_view_route)
        def request_schema_view():
            request_schema['$id'] = request.url_root[:-1] + url_for('api_schemas.' + request_schema_view_route)
            return jsonify(request_schema)

    @socketio.on(event)
    @functools.wraps(view)
    def wrapper(data):
        flask_session.setdefault('state', 'none')

        kwargs = {}
        session_id = data.get('authorization', '')
        del data['authorization']
        session = model.Session.query.filter_by(id=session_id).one_or_none()
        if session is None:
            send({'status': 'error', 'error': 'unauthorized'})
            return
        kwargs['user'] = session.user

        if request_schema is not None:
            rq = data
            try:
                jsonschema.validate(rq, request_schema)
            except jsonschema.exceptions.ValidationError as e:
                send({'status': 'error', 'error': 'bad_request'})
                return
            kwargs['rq'] = rq

        try:
            model.db.session.execute('PRAGMA foreign_keys = ON;')
            rs = view(**kwargs)
        except NotUnique as e:
            send({'status': 'error', 'error': 'not_unique', 'path': e.path, 'value': e.value})
            return
        except NotFound as e:
            send({'status': 'error', 'error': 'not_found', 'path': e.path, 'value': e.value})
            return
        except Forbidden as e:
            send({'status': 'error', 'error': 'forbidden'})
            return

def sio_send(rs, response_schema=None, **kwargs):
    if response_schema is not None:
        jsonschema.validate(rs, response_schema)
    rs['status'] = 'ok'
    send(rs, **kwargs)


def is_teacher(user, course):
    return model.db.session.query(model.User).join(model.User.teaches).filter(model.User.id == user.id).filter(model.Course.id == course.id).one_or_none() is not None

def is_student(user, course):
    return model.db.session.query(model.User).join(model.User.studies).filter(model.User.id == user.id).filter(model.Course.id == course.id).one_or_none() is not None


get_users_id_includes = {
    'id': {},
    'first_name': {},
    'last_name': {},
    'middle_name': {},
    'university': {},
    'university_group': {},
    'email': {},
    'admin': {},
}

@handler(
    method='GET',
    route='/users/<id>',
    response_schema=resources.user.schema(get_users_id_includes),
)
def get_users_id(user, id):
    if id == 'self':
        u = user
    else:
        u = model.User.query.filter_by(id=id).one_or_none()
    if u is None:
        raise NotFound('/users/id', id)
    if not (u is user or user.admin):
        raise Forbidden
    return resources.user.to_json(u, get_users_id_includes)

@handler(
    method='GET',
    route='/users',
    response_schema=resources.user.paginated_schema(get_users_id_includes)
)
def get_users(user):
    if not user.admin:
        raise Forbidden
    return resources.user.paginated_to_json(model.User.query, get_users_id_includes)

get_users_id_public_includes = {
    'id': {},
    'first_name': {},
    'last_name': {},
    'middle_name': {},
    'university': {},
    'university_group': {},
    'admin': {},
}

@handler(
    method='GET',
    route='/users/<id>/public',
    response_schema=resources.user.schema(get_users_id_public_includes),
)
def get_users_id_public(user, id):
    if id == 'self':
        u = user
    else:
        u = model.User.query.filter_by(id=id).one_or_none()
    if u is None:
        raise NotFound('/users/id', id)
    return resources.user.to_json(u, get_users_id_public_includes)

@handler(
    method='GET',
    route='/users/public',
    response_schema=resources.user.paginated_schema(get_users_id_public_includes)
)
def get_users_public(user):
    return resources.user.paginated_to_json(model.User.query, get_users_id_public_includes)


get_sessions_id_includes = {
    'id': {},
    'user': get_users_id_includes,
}

@handler(
    method='GET',
    route='/sessions/<id>',
    response_schema=resources.session.schema(get_sessions_id_includes),
)
def get_sessions_id(user, id):
    s = model.Session.query.filter_by(id=id).one_or_none()
    if s is None:
        raise NotFound('/sessions/id', id)
    if not (s.user is user or user.admin):
        raise Forbidden
    return resources.session.to_json(s, get_sessions_id_includes)

@handler(
    method='GET',
    route='/sessions',
    response_schema=resources.session.paginated_schema(get_sessions_id_includes),
)
def get_sessions(user):
    if not user.admin:
        raise Forbidden
    return resources.session.paginated_to_json(model.Session.query, get_sessions_id_includes)


get_courses_id_includes = {
    'id': {},
    'title': {},
}

@handler(
    method='GET',
    route='/courses/<id>',
    response_schema=resources.course.schema(get_courses_id_includes),
)
def get_courses_id(user, id):
    c = model.Course.query.filter_by(id=id).one_or_none()
    if c is None:
        raise NotFound('/courses/id', id)
    if not (is_student(user, c) or is_teacher(user, c) or user.admin):
        raise Forbidden
    return resources.course.to_json(c, get_courses_id_includes)

@handler(
    method='GET',
    route='/courses',
    response_schema=resources.course.paginated_schema(get_courses_id_includes),
)
def get_courses(user):
    if not user.admin:
        raise Forbidden
    return resources.course.paginated_to_json(model.Course.query, get_courses_id_includes)


get_modules_id_question_includes = {
    model.QuestionType.multiple_choice: {
        'id': {},
        'type': {},
        'correct_answer': {},
        'variants': {}
    },
    model.QuestionType.multiple_select: {
        'id': {},
        'type': {},
        'variants': {
            'correct': {},
            'text': {},
        },
    },
    model.QuestionType.free_response: {
        'id': {},
        'type': {},
        'correct_answer': {},
        'checker': {},
    },
}

get_modules_id_includes = {
    model.ModuleType.text: {
        'id': {},
        'title': {},
        'type': {},
        'created_at': {},
        'author': get_users_id_public_includes,
        'course': get_courses_id_includes,
        'text': {},
        'question': get_modules_id_question_includes,
    },
    model.ModuleType.visual: {
        'id': {},
        'title': {},
        'type': {},
        'created_at': {},
        'author': get_users_id_public_includes,
        'course': get_courses_id_includes,
    },
    model.ModuleType.test_block: {
        'id': {},
        'title': {},
        'type': {},
        'created_at': {},
        'author': get_users_id_public_includes,
        'course': get_courses_id_includes,
        'test_block_modules': {
            'id': {},
            'title': {},
            'type': {},
            'created_at': {},
            'author': get_users_id_public_includes,
            'course': get_courses_id_includes,
            'text': {},
            'question': get_modules_id_question_includes,
        },
    },
}

@handler(
    method='GET',
    route='/modules/<id>',
    response_schema=resources.module.schema(get_modules_id_includes),
)
def get_modules_id(user, id):
    m = model.Module.query.filter_by(id=id).one_or_none()
    if m is None:
        raise NotFound('/modules/id', id)
    if not (is_teacher(user, m.course) or user.admin):
        raise Forbidden
    return resources.module.to_json(m, get_modules_id_includes)

get_modules_includes = {
    model.ModuleType.text: {
        'id': {},
        'title': {},
        'type': {},
        'created_at': {},
        'author': get_users_id_public_includes,
        'course': get_courses_id_includes,
    },
    model.ModuleType.visual: {
        'id': {},
        'title': {},
        'type': {},
        'created_at': {},
        'author': get_users_id_public_includes,
        'course': get_courses_id_includes,
    },
    model.ModuleType.test_block: {
        'id': {},
        'title': {},
        'type': {},
        'created_at': {},
        'author': get_users_id_public_includes,
        'course': get_courses_id_includes,
    },
}

@handler(
    method='GET',
    route='/modules',
    response_schema=resources.module.paginated_schema(get_modules_includes),
)
def get_modules(user):
    if not user.admin:
        raise Forbidden
    return resources.module.paginated_to_json(model.Module.query, get_modules_includes)

get_lectures_id_includes = {
    'id': {},
    'title': {},
    'created_at': {},
    'author': get_users_id_public_includes,
    'course': get_courses_id_includes,
    'modules': get_modules_id_includes,
}

@handler(
    method='GET',
    route='/lectures/<id>',
    response_schema=resources.lecture.schema(get_lectures_id_includes),
)
def get_lectures_id(user, id):
    l = model.Lecture.query.filter_by(id=id).one_or_none()
    if l is None:
        raise NotFound('/lectures/id', id)
    if not (is_teacher(user, l.course) or user.admin):
        raise Forbidden
    return resources.lecture.to_json(l, get_lectures_id_includes)

get_lectures_includes = {
    'id': {},
    'title': {},
    'created_at': {},
    'author': get_users_id_public_includes,
    'course': get_courses_id_includes,
}

@handler(
    method='GET',
    route='/lectures',
    response_schema=resources.lecture.paginated_schema(get_lectures_includes),
)
def get_lectures(user):
    if not user.admin:
        raise Forbidden
    return resources.lecture.paginated_to_json(model.Lecture.query, get_lectures_includes)

get_lectures_id_student_includes = {
    'id': {},
    'title': {},
    'created_at': {},
    'author': get_users_id_public_includes,
    'course': get_courses_id_includes,
    'modules_without_questions': {
        model.ModuleType.text: {
            'id': {},
            'title': {},
            'type': {},
            'created_at': {},
            'author': get_users_id_public_includes,
            'course': get_courses_id_includes,
            'text': {},
        },
        model.ModuleType.visual: {
            'id': {},
            'title': {},
            'type': {},
            'created_at': {},
            'author': get_users_id_public_includes,
            'course': get_courses_id_includes,
        },
        model.ModuleType.test_block: {
            'id': {},
            'title': {},
            'type': {},
            'created_at': {},
            'author': get_users_id_public_includes,
            'course': get_courses_id_includes,
        },
    },
}

@handler(
    method='GET',
    route='/lectures/<id>/student',
    response_schema=resources.lecture.schema(get_lectures_id_student_includes),
)
def get_lectures_id_student(user, id):
    l = model.Lecture.query.filter_by(id=id).one_or_none()
    if l is None:
        raise NotFound('/lectures/id', id)
    if not (is_student(user, l.course) or is_teacher(user, l.course) or user.admin):
        raise Forbidden
    return resources.lecture.to_json(l, get_lectures_id_student_includes)

get_started_lectures_id_includes = {
    'id': {},
    'lecture': get_lectures_includes,
    'started_at': {},
    'lecturer': get_users_id_public_includes,
    'active': {},
    'current_module': get_modules_id_includes,
    'current_module_started': {},
}

@handler(
    method='GET',
    route='/started_lectures/<id>',
    response_schema=resources.started_lecture.schema(get_started_lectures_id_includes),
)
def get_started_lectures_id(user, id):
    s = model.StartedLecture.query.filter_by(id=id).one_or_none()
    if s is None:
        raise NotFound('/started_lectures/id', id)
    if not (is_teacher(user, s.lecture.course) or user.admin):
        raise Forbidden
    return resources.started_lecture.to_json(s, get_started_lectures_id_includes)

get_started_lectures_includes = {
    'id': {},
    'lecture': get_lectures_includes,
    'started_at': {},
    'lecturer': get_users_id_public_includes,
    'active': {},
}

@handler(
    method='GET',
    route='/started_lectures',
    response_schema=resources.started_lecture.paginated_schema(get_started_lectures_includes),
)
def get_started_lectures(user):
    if not user.admin:
        raise Forbidden
    return resources.started_lecture.paginated_to_json(model.StartedLecture.query, get_started_lectures_includes)

get_started_lectures_id_student_module_question_includes = {
    model.QuestionType.multiple_choice: {
        'id': {},
        'type': {},
        'variants': {}
    },
    model.QuestionType.multiple_select: {
        'id': {},
        'type': {},
        'variants': {
            'text': {},
        },
    },
    model.QuestionType.free_response: {
        'id': {},
        'type': {},
        'checker': {},
    },
}

get_started_lectures_id_student_module_includes = {
    model.ModuleType.text: {
        'id': {},
        'title': {},
        'type': {},
        'created_at': {},
        'author': get_users_id_public_includes,
        'course': get_courses_id_includes,
        'text': {},
        'question': get_started_lectures_id_student_module_question_includes,
    },
    model.ModuleType.visual: {
        'id': {},
        'title': {},
        'type': {},
        'created_at': {},
        'author': get_users_id_public_includes,
        'course': get_courses_id_includes,
    },
    model.ModuleType.test_block: {
        'id': {},
        'title': {},
        'type': {},
        'created_at': {},
        'author': get_users_id_public_includes,
        'course': get_courses_id_includes,
        'test_block_modules': {
            'id': {},
            'title': {},
            'type': {},
            'created_at': {},
            'author': get_users_id_public_includes,
            'course': get_courses_id_includes,
            'text': {},
            'question': get_started_lectures_id_student_module_question_includes,
        },
    },
}

get_started_lectures_id_student_includes = {
    'id': {},
    'lecture': get_lectures_includes,
    'started_at': {},
    'lecturer': get_users_id_public_includes,
    'current_module_if_started': get_started_lectures_id_student_module_includes,
    'current_module_started': {},
}

@handler(
    method='GET',
    route='/started_lectures/<id>/student',
    response_schema=resources.started_lecture.schema(get_started_lectures_id_student_includes),
)
def get_started_lectures_id_student(user):
    s = model.StartedLecture.query.filter_by(id=id).one_or_none()
    if s is None:
        raise NotFound('/started_lectures/id', id)
    if not (is_student(user, s.lecture.course) or is_teacher(user, s.lecture.course) or user.admin):
        raise Forbidden
    return resources.started_lecture.to_json(s, get_started_lectures_id_student_includes)


get_users_id_sessions_includes = {
    'id': {},
}

@handler(
    method='GET',
    route='/users/<id>/sessions',
    response_schema=resources.session.paginated_schema(get_users_id_sessions_includes),
)
def get_users_id_sessions(user, id):
    if id == 'self':
        u = user
    else:
        u = model.User.query.filter_by(id=id).one_or_none()
    if u is None:
        raise NotFound('/users/id', id)
    if not (user is u or user.admin):
        raise Forbidden
    return resources.session.paginated_to_json(model.Session.query.filter(model.Session.user_id == u.id), get_users_id_sessions_includes)

@handler(
    method='GET',
    route='/users/<id>/courses',
    response_schema=resources.course.paginated_schema(get_courses_id_includes),
)
def get_users_id_courses(user, id):
    if id == 'self':
        u = user
    else:
        u = model.User.query.filter_by(id=id).one_or_none()
    if u is None:
        raise NotFound('/users/id', id)
    if user.admin:
        return resources.course.paginated_to_json(model.Course.query, get_courses_id_includes)
    elif user is u:
        return resources.course.paginated_to_json(
            model.Course.query
            .join(model.Course.teachers)
            .filter(model.User.id == u.id)
            .union(
                model.Course.query
                .join(model.Course.students)
                .filter(model.User.id == u.id)
            ), get_courses_id_includes)
    else:
        raise Forbidden

@handler(
    method='GET',
    route='/users/<id>/teaches',
    response_schema=resources.course.paginated_schema(get_courses_id_includes),
)
def get_users_id_teaches(user, id):
    if id == 'self':
        u = user
    else:
        u = model.User.query.filter_by(id=id).one_or_none()
    if u is None:
        raise NotFound('/users/id', id)
    if not (user is u or user.admin):
        raise Forbidden
    return resources.course.paginated_to_json(model.Course.query.join(model.Course.teachers).filter(model.User.id == u.id), get_courses_id_includes)

@handler(
    method='GET',
    route='/users/<id>/studies',
    response_schema=resources.course.paginated_schema(get_courses_id_includes),
)
def get_users_id_studies(user, id):
    if id == 'self':
        u = user
    else:
        u = model.User.query.filter_by(id=id).one_or_none()
    if u is None:
        raise NotFound('/users/id', id)
    if not (user is u or user.admin):
        raise Forbidden
    return resources.course.paginated_to_json(model.Course.query.join(model.Course.students).filter(model.User.id == u.id), get_courses_id_includes)

get_users_id_created_lectures_includes = {
    'id': {},
    'title': {},
    'created_at': {},
    'course': get_courses_id_includes,
}

@handler(
    method='GET',
    route='/users/<id>/lectures',
    response_schema=resources.lecture.paginated_schema(get_lectures_includes),
)
def get_users_id_lectures(user, id):
    if id == 'self':
        u = user
    else:
        u = model.User.query.filter_by(id=id).one_or_none()
    if u is None:
        raise NotFound('/users/id', id)
    if user.admin:
        return resources.lecture.paginated_to_json(model.Lecture.query, get_lectures_includes)
    elif user is u:
        return resources.lecture.paginated_to_json(
            model.Lecture.query
            .join(model.Lecture.course)
            .join(model.Course.teachers)
            .filter(model.User.id == u.id)
            .union(
                model.Lecture.query
                .join(model.Lecture.course)
                .join(model.Course.students)
                .filter(model.User.id == u.id)
            ), get_lectures_includes)
    else:
        raise Forbidden

@handler(
    method='GET',
    route='/users/<id>/created_lectures',
    response_schema=resources.lecture.paginated_schema(get_users_id_created_lectures_includes),
)
def get_users_id_created_lectures(user, id):
    if id == 'self':
        u = user
    else:
        u = model.User.query.filter_by(id=id).one_or_none()
    if u is None:
        raise NotFound('/users/id', id)
    if not (user is u or user.admin):
        raise Forbidden
    return resources.course.paginated_to_json(model.Lecture.query.join(model.Lecure.author).filter(model.User.id == u.id), get_users_id_created_lectures_includes)

@handler(
    method='GET',
    route='/users/<id>/modules',
    response_schema=resources.module.paginated_schema(get_modules_includes),
)
def get_users_id_modules(user, id):
    if id == 'self':
        u = user
    else:
        u = model.User.query.filter_by(id=id).one_or_none()
    if u is None:
        raise NotFound('/users/id', id)
    if user.admin:
        return resources.module.paginated_to_json(model.Module.query, get_modules_includes)
    elif user is u:
        return resources.module.paginated_to_json(
            model.Module.query
            .join(model.Module.course)
            .join(model.Course.teachers)
            .filter(model.User.id == u.id)
            .union(
                model.Module.query
                .join(model.Module.course)
                .join(model.Course.students)
                .filter(model.User.id == u.id)
            ), get_modules_includes)
    else:
        raise Forbidden

get_users_id_created_modules_includes = {
    model.ModuleType.text: {
        'id': {},
        'title': {},
        'type': {},
        'created_at': {},
        'course': get_courses_id_includes,
    },
    model.ModuleType.visual: {
        'id': {},
        'title': {},
        'type': {},
        'created_at': {},
        'course': get_courses_id_includes,
    },
    model.ModuleType.test_block: {
        'id': {},
        'title': {},
        'type': {},
        'created_at': {},
        'course': get_courses_id_includes,
    },
}

@handler(
    method='GET',
    route='/users/<id>/created_modules',
    response_schema=resources.module.paginated_schema(get_users_id_created_modules_includes),
)
def get_users_id_created_modules(user, id):
    if id == 'self':
        u = user
    else:
        u = model.User.query.filter_by(id=id).one_or_none()
    if u is None:
        raise NotFound('/users/id', id)
    if not (user is u or user.admin):
        raise Forbidden
    return resources.course.paginated_to_json(model.Module.query.join(model.Module.author).filter(model.User.id == u.id), get_users_id_created_modules_includes)

get_users_id_started_lectures_includes = {
    'id': {},
    'lecture': get_lectures_includes,
    'started_at': {},
    'active': {},
}

@handler(
    method='GET',
    route='/users/<id>/started_lectures',
    response_schema=resources.started_lecture.paginated_schema(get_users_id_started_lectures_includes),
)
def get_users_id_started_lectures(user, id):
    if id == 'self':
        u = user
    else:
        u = model.User.query.filter_by(id=id).one_or_none()
    if u is None:
        raise NotFound('/users/id', id)
    if not (user is u or user.admin):
        raise Forbidden
    return resources.started_lecture.paginated_to_json(model.StartedLecture.query.join(model.StartedLecture.lecturer).filter(model.User.id == u.id), get_users_id_started_lectures_includes)

get_users_id_active_lectures_includes = {
    'id': {},
    'lecture': get_lectures_includes,
    'started_at': {},
}

@handler(
    method='GET',
    route='/users/<id>/active_lectures',
    response_schema=resources.started_lecture.paginated_schema(get_users_id_active_lectures_includes),
)
def get_users_id_active_lectures(user, id):
    if id == 'self':
        u = user
    else:
        u = model.User.query.filter_by(id=id).one_or_none()
    if u is None:
        raise NotFound('/users/id', id)
    if not (user is u or user.admin):
        raise Forbidden

    if user.admin:
        return resources.started_lecture.paginated_to_json(model.StartedLecture.query, get_users_id_active_lectures_includes)
    else:
        return resources.started_lecture.paginated_to_json(
            model.StartedLecture.query.join(model.StartedLecture.lecture)
            .join(model.Lecture.course)
            .join(model.Course.students)
            .filter(model.User.id == u.id)
            .filter(model.StartedLecture.active), get_users_id_active_lectures_includes)

@handler(
    method='GET',
    route='/users/<id>/creatable_courses',
    response_schema=resources.course.paginated_schema(get_courses_id_includes),
)
def get_users_id_creatable_courses(user, id):
    if id == 'self':
        u = user
    else:
        u = model.User.query.filter_by(id=id).one_or_none()
    if u is None:
        raise NotFound('/users/id', id)
    if not (user is u or user.admin):
        raise Forbidden
    if user.admin:
        query = model.Course.query
    else:
        query = model.Course.query.join(model.Course.teachers).filter(model.User.id == u.id)
    return resources.course.paginated_to_json(query, get_courses_id_includes, allowall=True)

@handler(
    method='GET',
    route='/courses/<id>/teachers',
    response_schema=resources.user.paginated_schema(get_users_id_public_includes),
)
def get_courses_id_teachers(user, id):
    c = model.Course.query.filter_by(id=id).one_or_none()
    if c is None:
        raise NotFound('/courses/id', id)
    if not (is_student(user, c) or is_teacher(user, c) or user.admin):
        raise Forbidden
    return resources.user.paginated_to_json(model.User.query.join(model.User.teaches).filter(model.Course.id == c.id), get_users_id_public_includes)

@handler(
    method='GET',
    route='/courses/<id>/students',
    response_schema=resources.user.paginated_schema(get_users_id_public_includes),
)
def get_courses_id_students(user, id):
    c = model.Course.query.filter_by(id=id).one_or_none()
    if c is None:
        raise NotFound('/courses/id', id)
    if not (is_student(user, c) or is_teacher(user, c) or user.admin):
        raise Forbidden
    return resources.user.paginated_to_json(model.User.query.join(model.User.students).filter(model.Course.id == c.id), get_users_id_public_includes)

get_started_lectures_id_responses_includes = {
    'user': get_users_id_public_includes,
    'number': {},
    'response': {},
}

@handler(
    method='GET',
    route='/started_lectures/<id>/responses',
    response_schema=resources.question_response.paginated_schema(get_started_lectures_id_responses_includes),
)
def get_started_lectures_id_responses(user, id):
    s = model.StartedLecture.query.filter_by(id=id).one_or_none()
    if c is None:
        raise NotFound('/started_lectures/id', id)
    if not (s.lecturer is user or user.admin):
        raise Forbidden
    return resources.question_response.paginated_to_json(model.QuestionResponse.query.filter(model.QuestionResponse.started_lecture_id == s.id), get_started_lectures_id_responses_includes)

post_users_includes = {
    'first_name': {},
    'last_name': {},
    'middle_name': {},
    'university': {},
    'university_group': {},
    'email': {},
    'password': {},
}

@handler(
    method='POST',
    route='/users',
    request_schema=resources.user.schema(post_users_includes),
    authorized=False,
)
def post_users(rq):
    if model.User.query.filter_by(email=rq['email']).one_or_none() is not None:
        raise NotUnique('/users/email', rq['email'])

    u = model.User(
        first_name = rq['first_name'],
        last_name = rq['last_name'],
        middle_name = rq['middle_name'],
        university = rq['university'],
        university_group = rq['university_group'],
        email = rq['email'],
        password = rq['password'],
    )
    model.db.session.add(u)
    model.db.session.commit()

patch_users_id_includes = {
    'first_name': {},
    'last_name': {},
    'middle_name': {},
    'university': {},
    'university_group': {},
}

@handler(
    method='PATCH',
    route='/users/<id>',
    request_schema=resources.user.schema(patch_users_id_includes),
)
def patch_users_id(user, id, rq):
    if id == 'self':
        u = user
    else:
        u = model.User.query.filter_by(id=id).one_or_none()
    if u is None:
        raise NotFound('/users/id', id)
    if not (u is user or user.admin):
        raise Forbidden

    u.first_name = rq['first_name']
    u.last_name = rq['last_name']
    u.middle_name = rq['middle_name']
    u.university = rq['university']
    u.university_group = rq['university_group']

    model.db.session.commit()

post_sessions_user_includes = {
    'email': {},
    'password': {},
}

@handler(
    method='POST',
    route='/sessions',
    request_schema=resources.user.schema(post_sessions_user_includes),
    response_schema=resources.session.schema(get_sessions_id_includes),
    authorized=False,
)
def post_sessions(rq):
    u = model.User.query.filter_by(email=rq['email']).one_or_none()
    if u is None:
        raise NotFound('/users/email', rq['email'])
    if not u.check_password(rq['password']):
        raise Forbidden

    model.Session.query.filter_by(user_id=u.id).delete()
    s = model.Session(id=secrets.token_hex(16), user=u)

    model.db.session.add(s)
    model.db.session.commit()

    return resources.session.to_json(s, get_sessions_id_includes)

post_courses_includes = {
    'title': {},
}

@handler(
    method='POST',
    route='/courses',
    request_schema=resources.course.schema(post_courses_includes),
)
def post_courses(user, rq):
    if model.Course.query.filter_by(title=rq['title']).one_or_none() is not None:
        raise NotUnique('/courses/title', rq['title'])
    if not user.admin:
        raise Forbidden

    c = model.Course(title=rq['title'])

    model.db.session.add(c)
    model.db.session.commit()

@handler(
    method='DELETE',
    route='/courses/<id>',
)
def delete_courses_id(user, id):
    c = model.Course.query.filter_by(id=id).one_or_none()
    if c is None:
        raise NotFound('/courses/id', id)
    if not user.admin:
        raise Forbidden

    model.db.session.delete(c)
    model.db.session.commit()

post_modules_question_includes = {
    model.QuestionType.multiple_choice: {
        'type': {},
        'correct_answer': {},
        'variants': {}
    },
    model.QuestionType.multiple_select: {
        'type': {},
        'variants': {
            'correct': {},
            'text': {},
        },
    },
    model.QuestionType.free_response: {
        'type': {},
        'correct_answer': {},
        'checker': {},
    },
}

def question_from_json(rq):
    ret = model.Question(type=getattr(model.QuestionType, rq['type']))
    model.db.session.add(ret)
    if rq['type'] == 'multiple_choice':
        q = model.MultipleChoiceQuestion(question=ret, correct_answer=rq['correct_answer'])
        model.db.session.add(q)
        for number, text in enumerate(rq['variants']):
            model.db.session.add(model.MultipleChoiceQuestionVariant(number=number, text=text, question=ret))
    elif rq['type'] == 'multiple_select':
        for number, var in enumerate(rq['variants']):
            model.db.session.add(model.MultipleSelectQuestionVariant(number=number, text=var['text'], correct=var['correct'], question=ret))
    elif rq['type'] == 'free_response':
        model.db.session.add(model.FreeResponseQuestion(correct_answer=rq['correct_answer'], checker=getattr(model.FreeResponseQuestionChecker, rq['checker']), question=ret))
    return ret

post_modules_includes = {
    model.ModuleType.text: {
        'title': {},
        'type': {},
        'course_id': {},
        'text': {},
        'question': post_modules_question_includes,
    },
    model.ModuleType.visual: {
        'title': {},
        'type': {},
        'course_id': {},
    },
    model.ModuleType.test_block: {
        'title': {},
        'type': {},
        'course_id': {},
        'test_block_modules': {
            'title': {},
            'type': {},
            'text': {},
            'question': post_modules_question_includes,
        },
    },
}

def module_from_json(rq, author, course):
    ret = model.Module(title=rq['title'], type=getattr(model.ModuleType, rq['type']), created_at=datetime.now(), author=author, course=course)
    model.db.session.add(ret)
    if rq['type'] == 'text':
        q = None
        if rq['question'] is not None:
            q = question_from_json(rq['question'])
        model.db.session.add(model.TextModule(text=rq['text'], question=q, module=ret))
    elif rq['type'] == 'visual':
        pass
    elif rq['type'] == 'test_block':
        for i, tbm in enumerate(rq['test_block_modules']):
            m = module_from_json(tbm, author, course)
            model.db.session.add(m)
            model.db.session.flush()
            model.db.session.execute(model.test_block_modules.insert().values(test_block_id=ret.id, number=i, module_id=m.id))
    return ret

@handler(
    method='POST',
    route='/modules',
    request_schema=resources.module.schema(post_modules_includes),
)
def post_modules(user, rq):
    c = model.Course.query.filter_by(id=rq['course_id']).one_or_none()
    if c is None:
        raise NotFound('/courses/id', rq['course_id'])
    if not (user.admin or is_teacher(user, c)):
        raise Forbidden

    module_from_json(rq, user, c)
    model.db.session.commit()

post_lectures_modules_includes = {
    model.ModuleType.text: {
        'title': {},
        'type': {},
        'text': {},
        'question': post_modules_question_includes,
    },
    model.ModuleType.visual: {
        'title': {},
        'type': {},
    },
    model.ModuleType.test_block: {
        'title': {},
        'type': {},
        'test_block_modules': {
            'title': {},
            'type': {},
            'text': {},
            'question': post_modules_question_includes,
        },
    },
}

post_lectures_includes = {
    'title': {},
    'course_id': {},
    'modules': post_lectures_modules_includes,
}

def lecture_from_json(rq, author, course):
    ret = model.Lecture(title=rq['title'], created_at=datetime.now(), author=author, course=course)
    model.db.session.add(ret)
    qi = 0
    for i, mrq in enumerate(rq['modules']):
        m = module_from_json(mrq, author, course)
        model.db.session.add(m)
        model.db.session.flush()
        model.db.session.execute(model.lecture_modules.insert().values(lecture_id=ret.id, number=i, module_id=m.id))
        if m.type == model.ModuleType.text and m.text_module[0].question is not None:
            model.db.session.execute(model.lecture_questions.insert().values(lecture_id=ret.id, number=qi, question_id=m.text_module[0].question.id))
            qi += 1
        elif m.type == model.ModuleType.test_block:
            for mm in m.test_block_modules:
                model.db.session.execute(model.lecture_questions.insert().values(lecture_id=ret.id, number=qi, question_id=mm.text_module[0].question.id))
                qi += 1
    return ret

@handler(
    method='POST',
    route='/lectures',
    request_schema=resources.lecture.schema(post_lectures_includes),
)
def post_lectures(user, rq):
    c = model.Course.query.filter_by(id=rq['course_id']).one_or_none()
    if c is None:
        raise NotFound('/courses/id', rq['course_id'])
    if not (user.admin or is_teacher(user, c)):
        raise Forbidden

    lecture_from_json(rq, user, c)
    model.db.session.commit()

post_started_lectures_includes = {
    'lecture_id': {},
}

@handler(
    method='POST',
    route='/started_lectures',
    request_schema=resources.started_lecture.schema(post_started_lectures_includes),
)
def post_started_lectures(user, rq):
    l = model.Lecture.query.filter_by(id=rq['lecture_id']).one_or_none()
    if l is None:
        raise NotFound('/lectures/id', rq['lecture_id'])
    if not (is_teacher(user, l.course) or user.admin):
        raise Forbidden

    cur_mod = l.modules[0]
    if cur_mod.type == model.ModuleType.text and cur_mod.text_module[0].question is not None:
        cur_mod_started = False
    elif cur_mod.type == model.ModuleType.test_block:
        cur_mod_started = False
    else:
        cur_mod_started = None
    sl = model.StartedLecture(lecture=l, lecturer=user, started_at=datetime.now(), current_module_number=0, current_module_started=cur_mod_started)
    model.db.session.add(sl)
    model.db.session.commit()


socketio = SocketIO()

sio_join_started_lectures_includes = {
    'id': {}
}

@sio_handler(
    event='join',
    request_schema=resources.started_lecture.schema(sio_join_started_lectures_includes),
)
def sio_join(user, rq):
    if flask_session['state'] != 'none':
        raise Forbidden

    s = model.StartedLecture.query.filter_by(id=rq['id']).one_or_none()
    if s is None:
        raise NotFound('/started_lectures/id', id)
    if not (is_student(user, s.lecture.course) or is_teacher(user, s.lecture.course) or user.admin):
        raise Forbidden

    flask_session['state'] = 'viewing'
    flask_session['id'] = rq['id']
    join_room(f'{flask_session["id"]}-{flask_session["state"]}')

    sio_send(resources.started_lecture.to_json(s, get_started_lectures_id_student_includes), resources.started_lecture.schema(get_started_lectures_id_student_includes))

@sio_handler(
    event='present',
    request_schema=resources.started_lecture.schema(sio_join_started_lectures_includes),
)
def sio_present(user, rq):
    if flask_session['state'] != 'none':
        raise Forbidden

    s = model.StartedLecture.query.filter_by(id=rq['id']).one_or_none()
    if s is None:
        raise NotFound('/started_lectures/id', id)
    if not (is_teacher(user, s.lecture.course) or user.admin):
        raise Forbidden

    flask_session['state'] = 'presenting'
    flask_session['id'] = rq['id']
    join_room(f'{flask_session["id"]}-{flask_session["state"]}')

    sio_send(resources.started_lecture.to_json(s, get_started_lectures_id_includes), resources.started_lecture.schema(get_started_lectures_id_includes))

@sio_handler(
    event='leave',
)
def sio_leave(user):
    if flask_session['state'] == 'none':
        raise Forbidden

    leave_room(f'{flask_session["id"]}-{flask_session["state"]}')
    flask_session['state'] = 'none'
    del flask_session['id']

@sio_handler(
    event='prev-module',
)
def sio_prev_module(user):
    if flask_session['state'] != 'presenting':
        raise Forbidden

    s = model.StartedLecture.query.filter_by(id=flask_session['id']).one_or_none()
    if s.current_module_number == 0:
        raise Forbidden

    s.current_module_number -= 1
    if s.current_module.type == model.ModuleType.text and s.current_module.text_module[0].question is not None:
        cur_mod_started = False
    elif s.current_module.type == model.ModuleType.test_block:
        cur_mod_started = False
    else:
        cur_mod_started = None
    s.current_module_started = cur_mod_started
    model.db.session.commit()

    sio_send(resources.started_lecture.to_json(s, get_started_lectures_id_student_includes), resources.started_lecture.schema(get_started_lectures_id_student_includes), room=f'{flask_session["id"]}-viewing')
    sio_send(resources.started_lecture.to_json(s, get_started_lectures_id_includes), resources.started_lecture.schema(get_started_lectures_id_includes), room=f'{flask_session["id"]}-presenting')

@sio_handler(
    event='next-module',
)
def sio_next_module(user):
    if flask_session['state'] != 'presenting':
        print(flask_session['state'])
        raise Forbidden

    s = model.StartedLecture.query.filter_by(id=flask_session['id']).one_or_none()
    if s.current_module_number + 1 == len(s.lecture.modules):
        raise Forbidden

    s.current_module_number += 1
    if s.current_module.type == model.ModuleType.text and s.current_module.text_module[0].question is not None:
        cur_mod_started = False
    elif s.current_module.type == model.ModuleType.test_block:
        cur_mod_started = False
    else:
        cur_mod_started = None
    s.current_module_started = cur_mod_started
    model.db.session.commit()

    sio_send(resources.started_lecture.to_json(s, get_started_lectures_id_student_includes), resources.started_lecture.schema(get_started_lectures_id_student_includes), room=f'{flask_session["id"]}-viewing')
    sio_send(resources.started_lecture.to_json(s, get_started_lectures_id_includes), resources.started_lecture.schema(get_started_lectures_id_includes), room=f'{flask_session["id"]}-presenting')

# @socketio.on('stop')
# def sio_stop(user, rq):
#     pass

# @socketio.on('start-module')
# def sio_start_module(user, rq):
#     pass

# @socketio.on('stop-module')
# def sio_stop_module(user, rq):
#     pass

# @socketio.on('answer')
# def sio_answer(user, rq):
#     pass

def init_app(app):
    socketio.init_app(app)
    app.register_blueprint(bp, url_prefix='/api')
    app.register_blueprint(bp_schemas, url_prefix='/api-schemas')
