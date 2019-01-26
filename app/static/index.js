Vue.component('error-box', {
  props: ['error'],
  template: `
    <div class="alert alert-danger alert-dismissible w-100" v-if="error != ''">
      {{ error }}
      <button type="button" class="close" v-on:click="$emit('error', '')">
        <span>&times;</span>
      </button>
    </div>
  `,
});

Vue.component('paginated-table', {
  props: ['url', 'head', 'row'],
  data: () => ({
    state: 'init',
    error: '',
    page: 1,
    pagesize: 10,
    total: null,
    items: [],
  }),
  created: function() {
    this.update();
  },
  computed: {
    totalpages: function() {
      return Math.floor((this.total + this.pagesize - 1) / this.pagesize);
    },
  },
  watch: {
    page: function(npage) {
      this.state = 'loading'
      this.update();
    }
  },
  methods: {
    update: async function() {
      let resp = await this.$apiCall('GET', this.url + '?page=' + this.page + '&pagesize=' + this.pagesize);
      if (resp.status == 'error') {
        this.error = resp.error;
        this.state = 'loaded';
      } else {
        this.page = resp.page;
        this.pagesize = resp.pagesize;
        this.total = resp.total;
        this.items = resp.items;
        this.state = 'loaded';
      }
    }
  },
  template: `
    <div v-if="state != 'init'">
      <error-box v-bind:error="error" v-on:error="error = $event"/>
      <nav>
        <ul class="pagination" v-if="totalpages > 1">
          <li class="page-item" v-bind:class="{active: p == page}" v-for="p in totalpages">
            <a href="#" class="page-link" v-on:click.prevent="page = p">{{ p }}</a>
          </li>
        </ul>
      </nav>
      <table class="table">
        <thead>
          <component v-bind:is="head" v-on:error="error = $event"/>
        </thead>
        <tbody>
          <component
            v-for="(item, idx) in items"
            v-bind:is="row"
            v-bind:key="idx"
            v-bind:item="item"
            v-on:error="error = $event"
          />
        </tbody>
      </table>
    </div>
  `,
});

Vue.component('page-login', {
  data: () => ({
    tab: 'login',
    error: '',
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    middle_name: '',
    university: '',
    university_group: '',
  }),
  methods: {
    login: async function() {
      if (!document.forms.formLogin.reportValidity()) {
        return;
      }
      let resp = await this.$apiCall('POST', '/sessions', {
        email: this.email,
        password: this.password,
      });
      if (resp.status == 'error') {
        this.error = resp.error;
      } else {
        this.$root.session = resp.id;
        this.$root.user = resp.user;
        localStorage.session = this.$root.session;
        localStorage.user = JSON.stringify(this.$root.user);
        this.$bus.$emit('page', '/courses');
      }
    },
    register: async function() {
      if (!document.forms.formRegister.reportValidity()) {
        return;
      }
      let resp = await this.$apiCall('POST', '/users', {
        first_name: this.first_name,
        last_name: this.last_name,
        middle_name: this.middle_name,
        university: this.university,
        university_group: this.university_group,
        email: this.email,
        password: this.password,
      });
      if (resp.status == 'error') {
        this.error = resp.error;
      } else {
        return await this.login();
      }
    },
  },
  template: `
    <div class="container">
      <h1 class="row">Войдите или зарегистрируйтесь</h1>
      <error-box class="row" v-bind:error="error" v-on:error="error = $event"/>
      <div class="row btn-toolbar mb-2">
        <div class="btn-group w-100">
          <button type="button" class="col w-100 btn btn-outline-secondary" v-bind:class="{active: tab == 'login'}" v-on:click="tab = 'login'">Войти</button>
          <button type="button" class="col w-100 btn btn-outline-secondary" v-bind:class="{active: tab == 'register'}" v-on:click="tab = 'register'">Зарегистрироваться</button>
        </div>
      </div>
      <form v-show="tab == 'login'" name="formLogin" v-on:submit.prevent="login()">
        <div class="row form-group">
          <label for="loginEmail">Email</label>
          <input type="email" class="form-control" id="loginEmail" v-model="email" required>
        </div>
        <div class="row form-group">
          <label for="loginPassword">Пароль</label>
          <input type="password" class="form-control" id="loginPassword" v-model="password" required>
        </div>
        <button type="submit" class="row btn btn-primary">Войти</button>
      </form>
      <form v-show="tab == 'register'" name="formRegister" v-on:submit.prevent="register()">
        <div class="row form-group">
          <label for="registerFirstName">Имя</label>
          <input type="text" class="form-control" id="registerFirstName" v-model="first_name" required>
        </div>
        <div class="row form-group">
          <label for="registerLastName">Фамилия</label>
          <input type="text" class="form-control" id="registerLastName" v-model="last_name" required>
        </div>
        <div class="row form-group">
          <label for="registerMiddleName">Отчество</label>
          <input type="text" class="form-control" id="registerMiddleName" v-model="middle_name">
        </div>
        <div class="row form-group">
          <label for="registerUniversity">Университет</label>
          <input type="text" class="form-control" id="registerUniversity" v-model="university">
        </div>
        <div class="row form-group">
          <label for="registerUniversityGroup">Группа</label>
          <input type="text" class="form-control" id="registerUniversityGroup" v-model="university_group">
        </div>
        <div class="row form-group">
          <label for="registerEmail">Email</label>
          <input type="email" class="form-control" id="registerEmail" v-model="email" required>
        </div>
        <div class="row form-group">
          <label for="registerPassword">Пароль</label>
          <input type="password" class="form-control" id="registerPassword" v-model="password" required>
        </div>
        <button type="submit" class="row btn btn-primary">Зарегистрироваться</button>
      </form>
    </div>
  `,
});

Vue.component('page-user', {
  data: function() {
    return {
      error: '',
      first_name: this.$root.user.first_name,
      last_name: this.$root.user.last_name,
      middle_name: this.$root.user.middle_name,
      university: this.$root.user.university,
      university_group: this.$root.user.university_group,
    };
  },
  methods: {
    change: async function() {
      if (!document.forms.formChangeUser.reportValidity()) {
        return;
      }
      let resp = await this.$apiCall('PATCH', '/users/self', {
        first_name: this.first_name,
        last_name: this.last_name,
        middle_name: this.middle_name,
        university: this.university,
        university_group: this.university_group,
      });
      if (resp.status == 'error') {
        this.error = resp.error;
      } else {
        this.$root.user.first_name = this.first_name;
        this.$root.user.last_name = this.last_name;
        this.$root.user.middle_name = this.middle_name;
        this.$root.user.university = this.university;
        this.$root.user.university_group = this.university_group;
      }
    },
  },
  template: `
    <div class="container">
      <h1 class="row">Личный кабинет</h1>
      <error-box class="row" v-bind:error="error" v-on:error="error = $event"/>
      <form name="formChangeUser" v-on:submit.prevent="change()">
        <div class="row form-group">
          <label for="changeUserFirstName">Имя</label>
          <input type="text" class="form-control" id="changeUserFirstName" v-model="first_name" required>
        </div>
        <div class="row form-group">
          <label for="changeUserLastName">Фамилия</label>
          <input type="text" class="form-control" id="changeUserLastName" v-model="last_name" required>
        </div>
        <div class="row form-group">
          <label for="changeUserMiddleName">Отчество</label>
          <input type="text" class="form-control" id="changeUserMiddleName" v-model="middle_name">
        </div>
        <div class="row form-group">
          <label for="changeUserUniversity">Университет</label>
          <input type="text" class="form-control" id="changeUserUniversity" v-model="university">
        </div>
        <div class="row form-group">
          <label for="changeUserUniversityGroup">Группа</label>
          <input type="text" class="form-control" id="changeUserUniversityGroup" v-model="university_group">
        </div>
        <button type="submit" class="row btn btn-primary">Изменить информацию</button>
      </form>
    </div>
  `,
});

Vue.component('page-courses-table-head', {
  template: `
    <tr>
      <th/>
      <th>Название</th>
    </tr>
  `,
});

Vue.component('page-courses-table-row', {
  props: ['item'],
  methods: {
    del: async function(id) {
      let resp = await this.$apiCall('DELETE', '/courses/' + id);
      if (resp.status == 'error') {
        this.$emit('error', resp.error);
      } else {
        this.$parent.update();
      }
    },
  },
  template: `
    <tr>
      <td class="shrink">
        <button type="button" class="btn btn-outline-danger mr-2" v-if="$root.user.admin" v-on:click="del(item.id)">
          <span class="fas fa-trash"/>
        </button>
      </td>
      <td>{{ item.title }}</td>
    </tr>
  `,
});

Vue.component('page-courses', {
  template: `
    <div class="container">
      <h1 class="row">Курсы</h1>
      <button
          type="button"
          class="row mb-2 btn btn-success"
          v-if="$root.user.admin"
          v-on:click="$bus.$emit('page', '/create-course')">
        Добавить курс
      </button>
      <paginated-table
        class="row"
        url="/users/self/courses"
        head="page-courses-table-head"
        row="page-courses-table-row"
      />
    </div>
  `,
});

Vue.component('page-create-course', {
  data: () => ({
    title: '',
    error: '',
  }),
  methods: {
    add: async function() {
      if (!document.forms.formAddCourse.reportValidity()) {
        return;
      }
      let resp = await this.$apiCall('POST', '/courses', {
        title: this.title,
      });
      if (resp.status == 'error') {
        this.error = resp.error;
      } else {
        this.$bus.$emit('page', '/courses');
      }
    },
  },
  template: `
    <div class="container">
      <h1 class="row">Добавить курс</h1>
      <error-box class="row" v-bind:error="error" v-on:error="error = $event"/>
      <form name="formAddCourse" v-on:submit.prevent="add()">
        <div class="row form-group">
          <label for="addCourseTitle">Название</label>
          <input type="text" class="form-control" id="addCourseTitle" v-model="title" required>
        </div>
        <button type="submit" class="row btn btn-primary">Добавить курс</button>
      </form>
    </div>
  `,
});

Vue.component('table-lectures-head', {
  template: `
    <tr>
      <th/>
      <th>Курс</th>
      <th>Название</th>
      <th>Автор</th>
      <th>Создана</th>
    </tr>
  `,
});

Vue.component('table-lectures-row', {
  props: ['item'],
  methods: {
    view: function(id) {
      this.$bus.$emit('page', '/view-lecture/' + id);
    },
    start: function(id) {
      let resp = this.$apiCall('POST', '/started_lectures', {lecture_id: id});
      if (resp.status == 'error') {
        this.$emit('error', resp.error);
      } else {
        this.$bus.$emit('page', '/present-started-lecture/' + id);
      }
    },
  },
  template: `
    <tr>
      <td class="shrink">
        <button type="button" class="btn btn-outline-primary mr-2" v-on:click="view(item.id)">
          <span class="fas fa-eye"/>
        </button>
        <button type="button" class="btn btn-outline-success mr-2" v-on:click="start(item.id)">
          <span class="fas fa-play"/>
        </button>
      </td>
      <td>{{ item.course.title }}</td>
      <td>{{ item.title }}</td>
      <td>{{ item.author.last_name }} {{ item.author.first_name }} {{ item.author.middle_name }}</td>
      <td><abbr v-bind:title="$momentFormat(item.created_at)">{{ $momentFromNow(item.created_at) }}</abbr></td>
    </tr>
  `,
});

Vue.component('page-lectures', {
  template: `
    <div class="container">
      <h1 class="row">Лекции</h1>
      <button
          type="button"
          class="row mb-2 btn btn-success"
          v-on:click="$bus.$emit('page', '/create-lecture')">
        Добавить лекцию
      </button>
      <paginated-table
        class="row"
        url="/users/self/lectures"
        head="table-lectures-head"
        row="table-lectures-row"
      />
    </div>
  `,
});

Vue.component('table-modules-head', {
  template: `
    <tr>
      <th/>
      <th>Курс</th>
      <th>Название</th>
      <th>Автор</th>
      <th>Создан</th>
    </tr>
  `,
});

Vue.component('table-modules-row', {
  props: ['item'],
  methods: {
    view: function(id) {
      this.$bus.$emit('page', '/view-module/' + id);
    },
  },
  template: `
    <tr>
      <td class="shrink">
        <button type="button" class="btn btn-outline-primary mr-2" v-on:click="view(item.id)">
          <span class="fas fa-eye"/>
        </button>
      </td>
      <td>{{ item.course.title }}</td>
      <td>{{ item.title }}</td>
      <td>{{ item.author.last_name }} {{ item.author.first_name }} {{ item.author.middle_name }}</td>
      <td><abbr v-bind:title="$momentFormat(item.created_at)">{{ $momentFromNow(item.created_at) }}</abbr></td>
    </tr>
  `,
});

Vue.component('page-modules', {
  template: `
    <div class="container">
      <h1 class="row">Модули</h1>
      <button
          type="button"
          class="row mb-2 btn btn-success"
          v-on:click="$bus.$emit('page', '/create-module')">
        Добавить модуль
      </button>
      <paginated-table
        class="row"
        url="/users/self/modules"
        head="table-modules-head"
        row="table-modules-row"
      />
    </div>
  `,
});

Vue.component('table-started-lectures-head', {
  template: `
    <tr>
      <th/>
      <th>Курс</th>
      <th>Название</th>
      <th>Начата</th>
    </tr>
  `,
});

Vue.component('table-started-lectures-row', {
  props: ['item'],
  methods: {
    view: function(id) {
      this.$bus.$emit('page', '/present-started-lecture/' + id);
    },
  },
  template: `
    <tr>
      <td class="shrink">
        <button type="button" class="btn btn-outline-success mr-2" v-on:click="view(item.id)">
          <span class="fas fa-play"/>
        </button>
      </td>
      <td>{{ item.lecture.course.title }}</td>
      <td>{{ item.lecture.title }}</td>
      <td><abbr v-bind:title="$momentFormat(item.started_at)">{{ $momentFromNow(item.started_at) }}</abbr></td>
    </tr>
  `,
});

Vue.component('table-active-lectures-head', {
  template: `
    <tr>
      <th/>
      <th>Курс</th>
      <th>Название</th>
      <th>Лектор</th>
      <th>Начата</th>
    </tr>
  `,
});

Vue.component('table-active-lectures-row', {
  props: ['item'],
  methods: {
    view: function(id) {
      this.$bus.$emit('page', '/view-started-lecture/' + id);
    },
  },
  template: `
    <tr>
      <td class="shrink">
        <button type="button" class="btn btn-outline-primary mr-2" v-on:click="view(item.id)">
          <span class="fas fa-eye"/>
        </button>
      </td>
      <td>{{ item.lecture.course.title }}</td>
      <td>{{ item.lecture.title }}</td>
      <td>{{ item.lecture.author.last_name }} {{ item.lecture.author.first_name }} {{ item.lecture.author.middle_name }}</td>
      <td><abbr v-bind:title="$momentFormat(item.started_at)">{{ $momentFromNow(item.started_at) }}</abbr></td>
    </tr>
  `,
});

Vue.component('page-started-lectures', {
  template: `
    <div class="container">
      <h1 class="row">Активные лекции</h1>
      <paginated-table
        class="row"
        url="/users/self/active_lectures"
        head="table-active-lectures-head"
        row="table-active-lectures-row"
      />
      <h1 class="row">Начатые лекции</h1>
      <paginated-table
        class="row"
        url="/users/self/started_lectures"
        head="table-started-lectures-head"
        row="table-started-lectures-row"
      />
    </div>
  `,
});

Vue.component('page-create-module', {
  data: () => ({
    error: '',
    course_id: null,
    courses: [],
  }),
  created: async function() {
    let resp = await this.$apiCall('GET', '/users/self/creatable_courses');
    if (resp.status == 'error') {
      this.error = resp.error;
    } else {
      for (course of resp.items) {
        this.courses.push(course);
      }
    }
  },
  methods: {
    add: async function() {
      if (!document.forms.formAddModule.reportValidity()) {
        return;
      }
      let data = this.$refs.builder.to_json();
      data['course_id'] = this.course_id;
      let resp = await this.$apiCall('POST', '/modules', data);
      if (resp.status == 'error') {
        this.error = resp.error;
      } else {
        this.$bus.$emit('page', '/modules');
      }
    },
  },
  template: `
    <div class="container">
      <h1 class="row">Добавить модуль</h1>
      <error-box class="row" v-bind:error="error" v-on:error="error = $event"/>
      <form name="formAddModule" v-on:submit.prevent="add()">
        <div class="row">
          <module-builder ref="builder" v-on:error="error = $event"/>
        </div>
        <div class="row form-group">
          <label>Курс</label>
          <select class="custom-select" v-model="course_id" required>
            <option v-bind:value="course.id" v-for="course in courses">{{ course.title }}</option>
          </select>
        </div>
        <button type="submit" class="row btn btn-primary">Добавить модуль</button>
      </form>
    </div>
  `,
});

Vue.component('module-builder', {
  props: ['question_only', 'show_remove'],
  data: function() {
    return {
      title: '',
      type: 'text',
      t_text: '',
      t_question: this.question_only,
      tb_modules: [],
      tb_idx: 0,
    };
  },
  methods: {
    tb_add: function() {
      this.tb_modules.push(this.tb_idx);
      this.tb_idx = this.tb_idx + 1;
    },
    tb_remove: function(i) {
      this.tb_modules.splice(this.tb_modules.indexOf(i), 1);
    },
    to_json: function() {
      if (this.type == 'text') {
        let q = null;
        if (this.t_question) {
          q = this.$children.find((c) => (c.$options.name == 'question-builder')).to_json();
        }
        return {
          title: this.title,
          type: this.type,
          text: this.t_text,
          question: q,
        };
      } else if (this.type == 'test_block') {
        return {
          title: this.title,
          type: this.type,
          test_block_modules: this.$children.filter((c) => (c.$options.name == 'module-builder')).map((c) => c.to_json()),
        };
      }
    },
  },
  template: `
    <div class="vm-outline w-100 mb-1">
      <div class="form-group">
        <button type="button" class="btn btn-outline-danger mr-2 mb-2" v-if="question_only || show_remove" v-on:click="$emit('remove')">
          <span class="fas fa-trash"/>
        </button>
        <label>Название</label>
        <input type="text" class="form-control" v-model="title" required>
      </div>
      <div class="btn-toolbar mb-2" v-if="!question_only">
        <div class="btn-group w-100">
          <button type="button" class="w-100 btn btn-outline-secondary" v-bind:class="{active: type == 'text'}" v-on:click="type = 'text'">Текстовый</button>
          <button type="button" class="w-100 btn btn-outline-secondary" v-bind:class="{active: type == 'test_block'}" v-on:click="type = 'test_block'">Проверочный блок</button>
        </div>
      </div>
      <div class="form-group" v-if="type == 'text'">
        <label>Текст</label>
        <textarea class="form-control" v-model="t_text" rows="10"></textarea>
      </div>
      <div class="form-check" v-if="type == 'text'">
        <input class="form-check-input" type="checkbox" v-bind:disabled="question_only" v-model="t_question"/>
        <label>Вопрос</label>
      </div>
      <question-builder v-if="type == 'text' && t_question"/>
      <module-builder
        question_only="1"
        v-if="type == 'test_block'"
        v-for="idx in tb_modules"
        v-bind:key="idx"
        v-on:remove="tb_remove(idx)"
      />
      <div v-if="type == 'test_block'">
        <button type="button" class="btn btn-outline-success" v-on:click="tb_add()">
          <span class="fas fa-plus"/>
        </button>
      </div>
    </div>
  `,
});

Vue.component('question-builder', {
  data: () => ({
    type: 'multiple_choice',
    mc_variants: [],
    mc_correct: 0,
    ms_variants: [],
    fr_checker: '',
    fr_correct: '',
  }),
  methods: {
    to_json: function() {
      if (this.type == 'multiple_choice') {
        return {
          type: 'multiple_choice',
          correct_answer: this.mc_correct,
          variants: [...this.mc_variants].map((e) => e.text),
        };
      } else if (this.type == 'multiple_select') {
        return {
          type: 'multiple_select',
          variants: this.ms_variants,
          variants: [...this.ms_variants].map((e) => ({text: e.text, correct: e.correct})),
        };
      } else if (this.type == 'free_response') {
        return {
          type: 'free_response',
          correct_answer: this.fr_correct,
          checker: this.fr_checker,
        };
      }
    },
  },
  template: `
    <div class="vm-outline w-100">
      <div class="btn-toolbar mb-2">
        <div class="btn-group w-100">
          <button type="button" class="w-100 btn btn-outline-secondary" v-bind:class="{active: type == 'multiple_choice'}" v-on:click="type = 'multiple_choice'">Выбор варианта</button>
          <button type="button" class="w-100 btn btn-outline-secondary" v-bind:class="{active: type == 'multiple_select'}" v-on:click="type = 'multiple_select'">Выбор множества вариантов</button>
          <button type="button" class="w-100 btn btn-outline-secondary" v-bind:class="{active: type == 'free_response'}" v-on:click="type = 'free_response'">Свободный ответ</button>
        </div>
      </div>
      <div class="input-group mb-2" v-if="type == 'multiple_choice'" v-for="(answer, idx) in mc_variants">
        <button type="button" class="btn btn-outline-danger mr-2" v-on:click="mc_variants.splice(idx, 1)">
          <span class="fas fa-trash"/>
        </button>
        <div class="input-group-prepend">
          <div class="input-group-text">
            <input type="radio" v-bind:value="idx" v-model="mc_correct"/>
          </div>
        </div>
        <input type="text" class="form-control" v-model="answer.text" required/>
      </div>
      <div v-if="type == 'multiple_choice'">
        <button type="button" class="btn btn-outline-success" v-on:click="mc_variants.push({text: ''})">
          <span class="fas fa-plus"/>
        </button>
      </div>
      <div class="input-group mb-2" v-if="type == 'multiple_select'" v-for="(answer, idx) in ms_variants">
        <button type="button" class="btn btn-outline-danger mr-2" v-on:click="ms_variants.splice(idx, 1)">
          <span class="fas fa-trash"/>
        </button>
        <div class="input-group-prepend">
          <div class="input-group-text">
            <input type="checkbox" v-model="answer.correct"/>
          </div>
        </div>
        <input type="text" class="form-control" v-model="answer.text" required/>
      </div>
      <div v-if="type == 'multiple_select'">
        <button type="button" class="btn btn-outline-success" v-on:click="ms_variants.push({text: '', correct: false})">
          <span class="fas fa-plus"/>
        </button>
      </div>
      <div class="form-group" v-if="type == 'free_response'">
        <label>Правильный ответ</label>
        <input type="text" class="form-control" v-model="fr_correct" required/>
      </div>
      <div class="form-group" v-if="type == 'free_response'">
        <label>Метод проверки</label>
        <select class="custom-select" v-model="fr_checker" required>
          <option value="exact_match">Точное совпадение</option>
        </select>
      </div>
    </div>
  `,
});

Vue.component('page-create-lecture', {
  data: () => ({
    error: '',
    course_id: null,
    courses: [],
  }),
  created: async function() {
    let resp = await this.$apiCall('GET', '/users/self/creatable_courses');
    if (resp.status == 'error') {
      this.error = resp.error;
    } else {
      for (course of resp.items) {
        this.courses.push(course);
      }
    }
  },
  methods: {
    add: async function() {
      if (!document.forms.formAddLecture.reportValidity()) {
        return;
      }
      let data = this.$refs.builder.to_json();
      data['course_id'] = this.course_id;
      let resp = await this.$apiCall('POST', '/lectures', data);
      if (resp.status == 'error') {
        this.error = resp.error;
      } else {
        this.$bus.$emit('page', '/lectures');
      }
    },
  },
  template: `
    <div class="container">
      <h1 class="row">Добавить лекцию</h1>
      <error-box class="row" v-bind:error="error" v-on:error="error = $event"/>
      <form name="formAddLecture" v-on:submit.prevent="add()">
        <div class="row">
          <lecture-builder ref="builder" v-on:error="error = $event"/>
        </div>
        <div class="row form-group">
          <label>Курс</label>
          <select class="custom-select" v-model="course_id" required>
            <option v-bind:value="course.id" v-for="course in courses">{{ course.title }}</option>
          </select>
        </div>
        <button type="submit" class="row btn btn-primary">Добавить лекцию</button>
      </form>
    </div>
  `,
});

Vue.component('lecture-builder', {
  data: () => ({
    title: '',
    modules: [],
    idx: 0,
  }),
  methods: {
    add: function() {
      this.modules.push(this.idx);
      this.idx = this.idx + 1;
    },
    remove: function(i) {
      this.modules.splice(this.modules.indexOf(i), 1);
    },
    to_json: function() {
      return {
        title: this.title,
        modules: this.$children.filter((c) => (c.$options.name == 'module-builder')).map((c) => c.to_json()),
      };
    },
  },
  template: `
    <div class="vm-outline w-100 mb-1">
      <div class="form-group">
        <label>Название</label>
        <input type="text" class="form-control" v-model="title" required>
      </div>
      <module-builder
        show_remove="1"
        v-for="idx in modules"
        v-bind:key="idx"
        v-on:remove="remove(idx)"
      />
      <button type="button" class="btn btn-outline-success" v-on:click="add()">
        <span class="fas fa-plus"/>
      </button>
    </div>
  `,
});

Vue.component('module-viewer', {
  props: ['data'],
  computed: {
    textHtml: function() {
      function escapeHtml(c) {
        let map = {
          '&': '&amp;',
          '<': '&lt;',
          '>': '&gt;',
          '"': '&quot;',
          "'": '&#39;',
          '/': '&#x2f;',
        };
        if (c in map) {
          return map[c];
        } else {
          return c;
        }
      }
      function parseText(s) {
        let out = '';
        let state = 'out';
        for (let i = 0; i < s.length;) {
          if (state == 'out') {
            if (s[i] == '\\') {
              if (i+1 < s.length && s[i+1] == '$') {
                out += '<p>$';
                state = 'in';
                i += 2;
              } else {
                out += '<p>\\';
                state = 'in';
                i += 1;
              }
            } else if (s[i] == '\n') {
              i += 1;
            } else if (s[i] == '$') {
              if (i+1 >= s.length) {
                out += '<p>$';
                state = 'in';
                i += 1;
              } else if (s[i+1] == '$') {
                let latex = parseDisplayLatex(s, i + 2);
                i = latex.i;
                latex = latex.latex;
                out += latex;
              } else {
                let latex = parseInlineLatex(s, i + 1);
                i = latex.i;
                latex = latex.latex;
                out += '<p>' + latex;
                state = 'in';
              }
            } else {
              out += '<p>' + escapeHtml(s[i]);
              state = 'in';
              i += 1;
            }
          } else {
            if (s[i] == '\\') {
              if (i+1 < s.length && s[i+1] == '$') {
                out += '$';
                i += 2;
              } else {
                out += '\\';
                i += 1;
              }
            } else if (s[i] == '\n') {
              if (i+1 < s.length && s[i+1] == '\n') {
                out += '</p>';
                state = 'out';
                i += 2;
              } else {
                out += ' ';
                i += 1;
              }
            } else if (s[i] == '$') {
              if (i+1 >= s.length) {
                out += '$';
                i += 1;
              } else if (s[i+1] == '$') {
                let latex = parseDisplayLatex(s, i + 2);
                i = latex.i;
                latex = latex.latex;
                out += '</p>' + latex;
                state = 'out';
              } else {
                let latex = parseInlineLatex(s, i + 1);
                i = latex.i;
                latex = latex.latex;
                out += latex;
              }
            } else {
              out += escapeHtml(s[i]);
              i += 1;
            }
          }
        }
        if (state == 'in') {
          out += '</p>'
        }
        return out;
      }
      function parseInlineLatex(s, i) {
        let out = '';
        while (i < s.length) {
          if (s[i] == '\\') {
            if (i+1 < s.length && s[i+1] == '$') {
              out += '$';
              i += 2;
            } else {
              out += '\\';
              i += 1;
            }
          } else if (s[i] == '$') {
            i += 1;
            break;
          } else {
            out += s[i];
            i += 1;
          }
        }
        out = katex.renderToString(out, {
          throwOnError: false,
        });
        out = ' <span>' + out + '</span> ';
        return {latex: out, i: i};
      }
      function parseDisplayLatex(s, i) {
        let out = '';
        while (i < s.length) {
          if (s[i] == '\\') {
            if (i+2 < s.length && s[i+1] == '$' && s[i+2] == '$') {
              out += '$$';
              i += 3;
            } else {
              out += '\\';
              i += 1;
            }
          } else if (s[i] == '$') {
            if (i+1 < s.length && s[i+1] == '$') {
              i += 2;
              break;
            } else {
              out += '$';
              i += 1;
            }
          } else {
            out += s[i];
            i += 1;
          }
        }
        out = katex.renderToString(out, {
          throwOnError: false,
          displayMode: true,
        });
        return {latex: out, i: i};
      }
      return parseText(this.data.text);
    }
  },
  template: `
    <div class="vm-outline w-100 mb-1">
      <h1 v-if="data != null">{{ data.title }}</h1>
      <p v-if="data != null" v-html="textHtml"/>
    </div>
  `,
});

Vue.component('page-view-module', {
  data: () => ({
    error: '',
    module: null,
  }),
  created: async function() {
    let module_id = document.location.pathname.replace(/^\/view-module\//, '');
    let resp = await this.$apiCall('GET', '/modules/' + module_id);
    if (resp.status == 'error') {
      this.error = resp.error;
    } else {
      if (resp.type == 'text' && resp.question == null) {
        this.module = resp;
      } else {
        this.error = 'only text modules without questions are supported right now';
      }
    }
  },
  template: `
    <div class="container">
      <div class="row">
        <error-box v-bind:error="error" v-on:error="error = $event"/>
        <module-viewer v-bind:data="module"/>
      </div>
    </div>
  `,
});

Vue.component('lecture-viewer', {
  props: ['title', 'modules'],
  template: `
    <div class="vm-outline w-100 mb-1">
      <h1>{{ title }}</h1>
      <module-viewer v-for="m in modules" v-bind:key="m.id" v-bind:data="m"/>
    </div>
  `,
});

Vue.component('page-view-lecture', {
  data: () => ({
    error: '',
    title: '',
    modules: '',
  }),
  created: async function() {
    let lecture_id = document.location.pathname.replace(/^\/view-lecture\//, '');
    let resp = await this.$apiCall('GET', '/lectures/' + lecture_id + '/student');
    if (resp.status == 'error') {
      this.error = resp.error;
    } else {
      this.title = resp.title;
      this.modules = resp.modules_without_questions;
    }
  },
  template: `
    <div class="container">
      <div class="row">
        <error-box v-bind:error="error" v-on:error="error = $event"/>
        <lecture-viewer v-bind:title="title" v-bind:modules="modules"/>
      </div>
    </div>
  `,
});

Vue.component('page-view-started-lecture', {
  data: () => ({
    error: '',
    title: '',
    module_started: null,
    module: null,
  }),
  created: function() {
    let started_lecture_id = parseInt(document.location.pathname.replace(/^\/view-started-lecture\//, ''));
    this.$sio.on('message', (data) => {
      if (data.status == 'error') {
        this.error = data.error;
        return;
      }
      this.title = data.lecture.title;
      this.module_started = data.current_module_started;
      this.module = data.current_module_if_started;
    });
    this.$sioCall('join', {id: started_lecture_id});
  },
  destroyed: function() {
    this.$sioCall('leave');
    this.$sio.removeAllListeners();
  },
  template: `
    <div class="container">
      <div class="row">
        <error-box v-bind:error="error" v-on:error="error = $event"/>
        <h1>{{ title }}</h1>
        <module-viewer v-if="module_started !== false" v-bind:data="module"/>
      </div>
    </div>
  `,
});

Vue.component('page-present-started-lecture', {
  data: () => ({
    error: '',
    title: '',
    module_started: null,
    module: null,
  }),
  created: function() {
    let started_lecture_id = parseInt(document.location.pathname.replace(/^\/present-started-lecture\//, ''));
    this.$sio.on('message', (data) => {
      if (data.status == 'error') {
        this.error = data.error;
        return;
      }
      this.title = data.lecture.title;
      this.module_started = data.current_module_started;
      this.module = data.current_module;
    });
    this.$sioCall('present', {id: started_lecture_id});
  },
  destroyed: function() {
    this.$sioCall('leave');
    this.$sio.removeAllListeners();
  },
  methods: {
    prevModule: function() {
      this.$sioCall('prev-module');
    },
    nextModule: function() {
      this.$sioCall('next-module');
    },
  },
  template: `
    <div class="container">
      <div class="row">
        <error-box v-bind:error="error" v-on:error="error = $event"/>
        <h1>{{ title }}</h1>
        <div class="btn-group w-100 mb-2">
          <button type="button" class="btn btn-outline-primary w-100" v-on:click="prevModule()">
            <span class="fas fa-arrow-left"/>
          </button>
          <button type="button" class="btn btn-outline-success w-100" v-bind:disabled="module_started !== false">
            <span class="fas fa-play"/>
          </button>
          <button type="button" class="btn btn-outline-danger w-100" v-bind:disabled="module_started !== true">
            <span class="fas fa-stop"/>
          </button>
          <button type="button" class="btn btn-outline-primary w-100" v-on:click="nextModule()">
            <span class="fas fa-arrow-right"/>
          </button>
        </div>
        <module-viewer v-if="module_started !== false" v-bind:data="module"/>
      </div>
    </div>
  `,
});

Vue.component('app', {
  data: () => ({
    page: null,
  }),
  created: function() {
    window.addEventListener('popstate', () => {
      this.page = document.location.pathname.replace(/^\/([^\/]*).*/, 'page-$1');
    });
    this.$bus.$on('page', (p) => this.setpage(p));
    if (this.$root.session == null) {
      this.setpage('/login');
    } else {
      let pagename = document.location.pathname.replace(/^\/([^\/]*).*/, 'page-$1');
      if (this.$options.components[pagename] != null) {
        this.page = pagename;
      } else {
        history.replaceState(null, '', '/courses');
        this.page = 'page-courses';
      }
    }
  },
  methods: {
    setpage: function(page) {
      if (this.page != page) {
        history.pushState(null, '', page);
        this.page = page.replace(/^\/([^\/]*).*/, 'page-$1');
      }
    },
    logout: function() {
      this.$root.session = null;
      this.$root.user = null;
      delete localStorage.session;
      delete localStorage.user;
      this.setpage('/login');
    },
  },
  template: `
    <div>
      <header>
        <nav class="navbar navbar-expand-lg navbar-light bg-light mb-2">
          <span class="navbar-brand">VisualMath.ru</span>
          <button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbarSupportedContent">
            <span class="navbar-toggler-icon"></span>
          </button>
          <div class="collapse navbar-collapse" id="navbarSupportedContent">
            <ul class="navbar-nav" v-if="$root.user != null">
              <li class="nav-item">
                <a href="#" class="nav-link" v-bind:class="{active: page == 'page-courses'}" v-on:click.prevent="setpage('/courses')">Курсы</a>
              </li>
              <li class="nav-item">
                <a href="#" class="nav-link" v-bind:class="{active: page == 'page-modules'}" v-on:click.prevent="setpage('/modules')">Модули</a>
              </li>
              <li class="nav-item">
                <a href="#" class="nav-link" v-bind:class="{active: page == 'page-lectures'}" v-on:click.prevent="setpage('/lectures')">Лекции</a>
              </li>
              <li class="nav-item">
                <a href="#" class="nav-link" v-bind:class="{active: page == 'page-started-lectures'}" v-on:click.prevent="setpage('/started-lectures')">Активные лекции</a>
              </li>
              <li class="nav-item">
                <a href="#" class="nav-link" v-bind:class="{active: page == 'page-user'}" v-on:click.prevent="setpage('/user')">Личный кабинет</a>
              </li>
              <li class="nav-item">
                <a href="//vmgraphs.bennydictor.tk/index.html" class="nav-link">Графы</a>
              </li>
              <li class="nav-item">
                <a href="#" class="nav-link" v-on:click.prevent="logout()">Выйти</a>
              </li>
            </ul>
            <ul class="navbar-nav" v-if="$root.user == null">
              <li class="nav-item">
                <a href="//vmgraphs.bennydictor.tk/index.html" class="nav-link">Графы</a>
              </li>
            </ul>
          </div>
        </nav>
      </header>
      <component
        v-bind:is="page"
      />
    </div>
  `,
});

window.addEventListener('load', () => {
  Vue.prototype.$apiCall = async function(method, url, body) {
    const API_PREFIX = '/api';
    let fetch_data = {
      method: method,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      }
    };
    if (this.$root.session != null) {
      fetch_data.headers['Authorization'] = this.$root.session;
    }
    if (method != 'GET') {
      fetch_data.body = JSON.stringify(body);
    }

    let res;
    try {
      res = await fetch(API_PREFIX + url, fetch_data);
    } catch (e) {
      return {'status': 'error', 'error': '' + e};
    }
    try {
      return await res.json();
    } catch (e) {
      if (!res.ok) {
        return {'status': 'error', 'error': '' + res.status + ' ' + res.statusText};
      } else {
        return {'status': 'error', 'error': 'invalid json: ' + e};
      }
    }
  };

  Vue.prototype.$sio = io();
  Vue.prototype.$sioCall = function(event, data) {
    if (data === undefined) {
      data = {};
    }
    data['authorization'] = this.$root.session;
    this.$sio.emit(event, data);
  };

  moment.locale('ru');
  Vue.prototype.$momentFromNow = (t) => {
    let d = moment.unix(t);
    return d.fromNow();
  }
  Vue.prototype.$momentFormat = (t) => {
    let d = moment.unix(t);
    return d.format();
  }
  Vue.prototype.$bus = new Vue();

  let session = null;
  let user = null;
  if (localStorage.session != null) {
    session = localStorage.session;
    user = JSON.parse(localStorage.user);
  }
  new Vue({
    el: '#app',
    data: {
      session: session,
      user: user,
    },
  });
});

// vim:set shiftwidth=2:
