from typing import Callable, Dict, List, Tuple, Iterable, TypeVar, Any
from types import ModuleType
from jinja2 import Environment  # type: ignore

from .routes import Router
from .environs import BaseResponse, Response


WSGIEnvironValue = TypeVar('WSGIEnvironValue')
WSGIEnviron = Dict[str, WSGIEnvironValue]
StartResponse = Callable[[bytes, List[Tuple[str, str]]], None]

ViewFunction = Callable[..., BaseResponse]
WSGIResponse = Iterable[bytes]


class Kobin:
    router: Router
    config: Config
    before_request_callback: Callable[[], None]
    after_request_callback: Callable[[BaseResponse], BaseResponse]

    def __init__(self, config: Config = ...) -> None: ...
    def route(self, rule: str = ..., method: str = ..., name: str = ...,
              callback: ViewFunction = ...) -> ViewFunction: ...
    def before_request(self, callback: Callable[[], None]) -> Callable[[], None]: ...
    def after_request(self, callback: Callable[[BaseResponse], BaseResponse]) -> \
            Callable[[BaseResponse], BaseResponse]: ...
    def _handle(self, environ: WSGIEnviron) -> BaseResponse: ...
    def wsgi(self, environ: WSGIEnviron, start_response: StartResponse) -> WSGIResponse: ...
    def __call__(self, environ: WSGIEnviron, start_response: StartResponse) -> WSGIResponse: ...

def _get_traceback_message(e: BaseException) -> str: ...
def _handle_unexpected_exception(e: BaseException, debug: bool) -> Response: ...

class Config(dict):
    _template_env: Environment

    def __init__(self, **kwargs: Dict[str, Any]) -> None: ...
    def template_env(self) -> Environment: ...

def load_config_from_pyfile(filepath: str) -> Config: ...
def load_config_from_module(module: ModuleType) -> Config: ...
def current_app() -> Kobin: ...
def current_config() -> Config: ...
