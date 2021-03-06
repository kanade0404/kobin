import os
from unittest import TestCase
from unittest.mock import patch
from kobin import (
    Kobin, Response,
    load_config_from_module, load_config_from_pyfile
)
from kobin.app import (
    template_router_reverse, load_jinja2_env, load_config,
    _get_exception_message
)


class KobinTests(TestCase):
    def setUp(self):
        self.app = Kobin()
        self.dummy_start_response = lambda x, y: None

        @self.app.route('/')
        def dummy_func():
            return Response('hello')

        @self.app.route('/test/{typed_id}')
        def typed_url_var(typed_id: int):
            body = "type: {}, value: {}".format(type(typed_id), typed_id)
            return Response(body)

        @self.app.route('/test/raise500')
        def raise500(typed_id: int):
            1 / 0
            return Response("Don't reach here")

    def test_route(self):
        test_env = {'REQUEST_METHOD': 'GET', 'PATH_INFO': '/'}
        response = self.app._handle(test_env)
        actual = response.body
        expected = [b'hello']
        self.assertEqual(actual, expected)

    def test_typed_url_var(self):
        test_env = {'REQUEST_METHOD': 'GET', 'PATH_INFO': '/test/10'}
        response = self.app._handle(test_env)
        actual = response.body
        expected = [b"type: <class 'int'>, value: 10"]
        self.assertEqual(actual, expected)

    def test_404_not_found(self):
        test_env = {'REQUEST_METHOD': 'GET', 'PATH_INFO': '/this_is_not_found'}
        response = self.app._handle(test_env)
        actual = response._status_code
        expected = 404
        self.assertEqual(actual, expected)

    def test_404_when_cast_error(self):
        test_env = {'REQUEST_METHOD': 'GET', 'PATH_INFO': '/test/not-integer'}
        response = self.app._handle(test_env)
        actual = response._status_code
        expected = 404
        self.assertEqual(actual, expected)

    def test_response_status_when_500_raised(self):
        test_env = {'REQUEST_METHOD': 'GET', 'PATH_INFO': '/test/raise500'}
        response = self.app._handle(test_env)
        actual = response._status_code
        expected = 500
        self.assertEqual(actual, expected)

    def test_response_body_when_500_raised_and_enable_debugging(self):
        self.app.config['DEBUG'] = True
        test_env = {'REQUEST_METHOD': 'GET', 'PATH_INFO': '/test/raise500'}
        response = self.app._handle(test_env)
        actual = response.body
        expected = [b'Internal Server Error']
        self.assertNotEqual(actual, expected)

    def test_response_body_when_500_raised_and_disable_debugging(self):
        test_env = {'REQUEST_METHOD': 'GET', 'PATH_INFO': '/test/raise500'}
        response = self.app._handle(test_env)
        actual = response.body
        expected = [b'Internal Server Error']
        self.assertEqual(actual, expected)

    def test_handled_body_message_when_404_not_found(self):
        test_env = {'REQUEST_METHOD': 'GET', 'PATH_INFO': '/this_is_not_found'}
        response = self.app._handle(test_env)
        actual = response.body
        expected = [b"Not found: /this_is_not_found"]
        self.assertEqual(actual, expected)

    def test_wsgi(self):
        test_env = {'REQUEST_METHOD': 'GET', 'PATH_INFO': '/'}
        actual = self.app(test_env, self.dummy_start_response)
        expected = [b'hello']
        self.assertEqual(actual, expected)


class KobinHookTests(TestCase):
    def setUp(self):
        self.app = Kobin()
        self.dummy_start_response = lambda x, y: None
        self.before_counter = 0

        @self.app.route('/')
        def dummy_func():
            return Response('hello')

        @self.app.before_request
        def before():
            self.before_counter += 1

        @self.app.before_request
        def before2():
            self.before_counter += 1

        @self.app.after_request
        def after(response):
            response.headers.add_header('Foo1', 'Bar1')
            return response

        @self.app.after_request
        def after2(response):
            response.headers.add_header('Foo2', 'Bar2')
            return response

    def test_before_request(self):
        test_env = {'REQUEST_METHOD': 'GET', 'PATH_INFO': '/'}
        self.app.before_counter = 0
        self.app._handle(test_env)
        self.assertEqual(self.before_counter, 2)

    def test_after_request(self):
        test_env = {'REQUEST_METHOD': 'GET', 'PATH_INFO': '/'}
        response = self.app._handle(test_env)
        self.assertIn(('Foo1', 'Bar1'), response.headerlist)
        self.assertIn(('Foo2', 'Bar2'), response.headerlist)


class HandleUnexpectedExceptionTests(TestCase):
    def test_get_exception_message_when_debugging(self):
        try:
            1 / 0
        except BaseException as e:
            actual = _get_exception_message(e, True)
        else:
            actual = "Exception is not raised."
        cause_of_exception = '1 / 0'
        self.assertIn(cause_of_exception, actual)

    def test_get_exception_message_when_not_debugging(self):
        try:
            1 / 0
        except BaseException as e:
            actual = _get_exception_message(e, False)
        else:
            actual = "Exception is not raised."
        expected = 'Internal Server Error'
        self.assertEqual(actual, expected)


class KobinAfterHookTests(TestCase):
    def setUp(self):
        self.app = Kobin()
        self.dummy_start_response = lambda x, y: None
        self.before_counter = 0

        @self.app.route('/')
        def dummy_func():
            return Response('hello')

        @self.app.after_request
        def after_do_not_return_response(response):
            pass

    def test_after_request(self):
        test_env = {'REQUEST_METHOD': 'GET', 'PATH_INFO': '/'}
        response = self.app._handle(test_env)
        self.assertEqual('200 OK', response.status)


class KobinFrozenTests(TestCase):
    def setUp(self):
        self.app = Kobin(config={'DEBUG': True})
        self.before_counter = 0

        @self.app.route('/')
        def dummy_func():
            return Response('hello')

    def test_can_change_state_before_running(self):
        test_env = {'REQUEST_METHOD': 'GET', 'PATH_INFO': '/'}

        def dummy_start_response(s, h):
            pass

        self.app(test_env, dummy_start_response)
        self.app.config = {'foo': 'bar'}
        self.assertNotIn('foo', self.app.config)


class ConfigTests(TestCase):
    def setUp(self):
        self.base_path = os.path.dirname(os.path.abspath(__file__))

    @patch('kobin.app._current_app')
    def test_lazy_reverse_router(self, app_mock):
        app = Kobin()

        @app.route('/', 'GET', 'top')
        def top():
            return Response('Hello')

        app_mock.return_value = app
        actual = template_router_reverse('top')

        expected = '/'
        self.assertEqual(actual, expected)

    @patch('kobin.app._current_app')
    def test_lazy_reverse_router_not_found(self, app_mock):
        app = Kobin()
        app_mock.return_value = app
        actual = template_router_reverse('top')
        expected = ''
        self.assertEqual(actual, expected)

    def test_load_jinja2_env_with_globals(self):
        env = load_jinja2_env('.', global_variables={'foo': 'bar'})
        self.assertEqual('bar', env.globals['foo'])

    def test_load_jinja2_env_with_filters(self):
        def foo_filter(x):
            return x * 2

        env = load_jinja2_env('.', global_filters={'foo': foo_filter})
        self.assertEqual(foo_filter, env.filters['foo'])

    def test_constructor(self):
        config = load_config()
        self.assertIn('DEBUG', config.keys())

    def test_load_from_module(self):
        from tests import dummy_config
        config = load_config_from_module(dummy_config)
        self.assertIn('UPPER_CASE', config)

    def test_load_from_pyfile(self):
        dummy_config = os.path.join(self.base_path, 'dummy_config.py')
        config = load_config_from_pyfile(dummy_config)
        self.assertIn('UPPER_CASE', config)

    def test_config_has_not_lower_case_variable(self):
        dummy_config = os.path.join(self.base_path, 'dummy_config.py')
        config = load_config_from_pyfile(dummy_config)
        self.assertNotIn('lower_case', config)

    def test_failure_for_loading_config(self):
        dummy_config = os.path.join(self.base_path, 'no_exists.py')
        self.assertRaises(FileNotFoundError, load_config_from_pyfile, dummy_config)
