from . import model
from flask import request

class Property(object):
    def __init__(self, *, name=None, jsontype=None, getter=None, resource=None, many=False, nullable=False):
        self.name = name
        if isinstance(jsontype, str):
            self.jsontype = {'type': jsontype}
        else:
            self.jsontype = jsontype
        if getter is None:
            self.getter = lambda res: getattr(res, self.name)
        else:
            self.getter = getter
        self.resource = resource
        self.many = many
        self.nullable = nullable

    def get(self, res, includes):
        subres = self.getter(res)
        if self.nullable and subres is None:
            return None
        if self.resource is not None:
            if self.many:
                return [self.resource.to_json(i, includes) for i in subres]
            else:
                return self.resource.to_json(subres, includes)
        else:
            return subres

    def schema(self, includes):
        if self.resource is not None:
            if self.many:
                ret = {'type': 'array', 'items': self.resource.schema(includes)}
            else:
                ret = self.resource.schema(includes)
        else:
            ret = self.jsontype
        if self.nullable:
            ret = {'oneOf': [{'type': 'null'}, ret]}
        return ret

class Resource(object):
    def __init__(self):
        self.properties = {}

    def __setitem__(self, key, value):
        if isinstance(value, Property):
            value.name = key
            self.properties[key] = value
        else:
            self.properties[key] = Property(name=key, jsontype=value)

    def to_json(self, res, includes):
        ret = {}
        for include, nested_includes in includes.items():
            ret[include] = self.properties[include].get(res, nested_includes)
        return ret

    def schema(self, includes):
        properties = {}
        for include, nested_includes in includes.items():
            properties[include] = self.properties[include].schema(nested_includes)
        return {
            'type': 'object',
            'properties': properties,
            'required': list(includes.keys()),
        }

    def paginated_to_json(self, query, includes, maxpagesize=100, allowall=False):
        try:
            page = max(1, int(request.args.get('page', '')))
        except ValueError:
            page = 1
        try:
            if allowall and request.args.get('pagesize', '') == 'all':
                pagesize = 'all'
            else:
                pagesize = max(1, min(maxpagesize, int(request.args.get('pagesize', ''))))
        except ValueError:
            pagesize = maxpagesize

        total = query.count()
        if pagesize == 'all':
            pagesize = total
            items = query.all()
        else:
            items = query.offset((page-1) * pagesize).limit(pagesize).all()

        return {
            'items': [self.to_json(i, includes) for i in items],
            'page': page,
            'pagesize': pagesize,
            'total': total,
        }

    def paginated_schema(self, includes):
        return {
            'type': 'object',
            'properties': {
                'items': {
                    'type': 'array',
                    'items': self.schema(includes),
                },
                'page': {'type': 'integer'},
                'pagesize': {'type': 'integer'},
                'total': {'type': 'integer'},
            },
            'required': ['items', 'page', 'pagesize', 'total'],
        }

class OneOfResource(Resource):
    def __init__(self, resources):
        self.resources = resources

    def to_json(self, res, includes):
        resource = self.resources[res.type]
        includes = includes[res.type]
        return resource.to_json(res, includes)

    def schema(self, includes):
        return {'anyOf': [r.schema(includes[t]) for t, r in self.resources.items()]}


user = Resource()
session = Resource()
course = Resource()
multiple_choice_question = Resource()
multiple_select_question_variant = Resource()
multiple_select_question = Resource()
free_response_question = Resource()
question = OneOfResource({
    model.QuestionType.multiple_choice: multiple_choice_question,
    model.QuestionType.multiple_select: multiple_select_question,
    model.QuestionType.free_response: free_response_question,
})
text_module = Resource()
text_module_with_question = Resource()
visual_module = Resource()
test_block_module = Resource()
module = OneOfResource({
    model.ModuleType.text: text_module,
    model.ModuleType.visual: visual_module,
    model.ModuleType.test_block: test_block_module,
})
lecture = Resource()
started_lecture = Resource()
question_response = Resource()

user['id'] = 'integer'
user['first_name'] = 'string'
user['last_name'] = 'string'
user['middle_name'] = 'string'
user['university'] = 'string'
user['university_group'] = 'string'
user['email'] = 'string'
user['password'] = 'string'
user['admin'] = 'boolean'
user['sessions'] = Property(resource=session, many=True)
user['teaches'] = Property(resource=course, many=True)
user['studues'] = Property(resource=course, many=True)
user['created_lectures'] = Property(resource=lecture, many=True)
user['created_modules'] = Property(resource=module, many=True)
user['started_lectures'] = Property(resource=started_lecture, many=True)
user['question_responses'] = Property(resource=question_response, many=True)

session['id'] = 'string'
session['user_id'] = 'integer'
session['user'] = Property(resource=user)

course['id'] = 'integer'
course['title'] = 'string'
course['teachers'] = Property(resource=user, many=True)
course['students'] = Property(resource=user, many=True)
course['lectures'] = Property(resource=lecture, many=True)
course['modules'] = Property(resource=module, many=True)

for q in (multiple_choice_question, multiple_select_question, free_response_question):
    q['id'] = 'integer'

multiple_choice_question['type'] = Property(jsontype={'type': 'string', 'enum': ['multiple_choice']}, getter=lambda res: 'multiple_choice')
multiple_choice_question['correct_answer'] = Property(jsontype='integer', getter=lambda res: res.multiple_choice_question[0].correct_answer)
multiple_choice_question['variants'] = Property(jsontype={'type': 'array', 'items': {'type': 'string'}}, getter=lambda res: [i.text for i in res.multiple_choice_question_variants])

multiple_select_question_variant['correct'] = 'boolean'
multiple_select_question_variant['text'] = 'string'

multiple_select_question['type'] = Property(jsontype={'type': 'string', 'enum': ['multiple_select']}, getter=lambda res: 'multiple_select')
multiple_select_question['variants'] = Property(resource=multiple_select_question_variant, many=True, getter=lambda res: res.multiple_select_question_variants)

free_response_question['type'] = Property(jsontype={'type': 'string', 'enum': ['free_response']}, getter=lambda res: 'free_response')
free_response_question['correct_answer'] = Property(jsontype='string', getter=lambda res: res.free_response_question[0].correct_answer)
free_response_question['checker'] = Property(jsontype='string', getter=lambda res: res.free_response_question[0].checker.name)

for m in (text_module, text_module_with_question, visual_module, test_block_module):
    m['id'] = 'integer'
    m['title'] = 'string'
    m['created_at'] = Property(jsontype='integer', getter=lambda res: int(res.created_at.timestamp()))
    m['author_id'] = 'integer'
    m['course_id'] = 'integer'
    m['author'] = Property(resource=user)
    m['course'] = Property(resource=course)

for m in (text_module, text_module_with_question):
    m['type'] = Property(jsontype={'type': 'string', 'enum': ['text']}, getter=lambda res: 'text')
    m['text'] = Property(jsontype='string', getter=lambda res: res.text_module[0].text)

text_module['question'] = Property(resource=question, getter=lambda res: res.text_module[0].question, nullable=True)
text_module_with_question['question'] = Property(resource=question, getter=lambda res: res.text_module[0].question)

visual_module['type'] = Property(jsontype={'type': 'string', 'enum': ['visual']}, getter=lambda res: 'visual')

test_block_module['type'] = Property(jsontype={'type': 'string', 'enum': ['test_block']}, getter=lambda res: 'test_block')
test_block_module['test_block_modules'] = Property(resource=text_module_with_question, many=True)

lecture['id'] = 'integer'
lecture['title'] = 'string'
lecture['created_at'] = Property(jsontype='integer', getter=lambda res: int(res.created_at.timestamp()))
lecture['author_id'] = 'integer'
lecture['course_id'] = 'integer'
lecture['author'] = Property(resource=user)
lecture['course'] = Property(resource=course)
lecture['modules'] = Property(resource=module, many=True)
lecture['modules_without_questions'] = Property(resource=module, many=True)

started_lecture['id'] = 'integer'
started_lecture['lecture_id'] = 'integer'
started_lecture['started_at'] = Property(jsontype='integer', getter=lambda res: int(res.started_at.timestamp()))
started_lecture['lecturer_id'] = 'integer'
started_lecture['current_module_number'] = Property(jsontype='integer', nullable=True)
started_lecture['current_module_started'] = Property(jsontype='boolean', nullable=True)
started_lecture['lecture'] = Property(resource=lecture)
started_lecture['lecturer'] = Property(resource=user)
started_lecture['active'] = Property(jsontype='boolean')
started_lecture['current_module'] = Property(resource=module, nullable=True)
started_lecture['current_module_if_started'] = Property(resource=module, nullable=True, getter=lambda res: res.current_module if res.current_module_started is not False else None)

question_response['started_lecture_id'] = 'integer'
question_response['user_id'] = 'integer'
question_response['number'] = 'integer'
question_response['response'] = Property(jsontype='string', nullable=True)
question_response['correct'] = Property(jsontype='boolean', nullable=True)
question_response['started_lecture'] = Property(resource=started_lecture)
question_response['user'] = Property(resource=user)
question_response['question'] = Property(resource=question)
