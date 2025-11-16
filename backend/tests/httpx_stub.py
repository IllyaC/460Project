import json
import sys
import types
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit


class _Headers:
    def __init__(self, data: Any | None = None) -> None:
        self._items: list[tuple[str, str]] = []
        if data:
            self.update(data)

    def update(self, data: Any) -> None:
        if isinstance(data, _Headers):
            self._items.extend(data._items)
        elif isinstance(data, Mapping):
            for key, value in data.items():
                self.add(key, value)
        elif isinstance(data, Iterable):
            for key, value in data:
                self.add(key, value)

    def add(self, key: str, value: Any) -> None:
        self._items.append((str(key), str(value)))

    def get(self, key: str, default: Any = None) -> Any:
        key_lower = key.lower()
        for existing_key, value in reversed(self._items):
            if existing_key.lower() == key_lower:
                return value
        return default

    def setdefault(self, key: str, value: Any) -> Any:
        current = self.get(key)
        if current is None:
            self.add(key, value)
            return value
        return current

    def multi_items(self) -> list[tuple[str, str]]:
        return list(self._items)

    def items(self) -> Iterable[tuple[str, str]]:
        return self.multi_items()

    def copy(self) -> "_Headers":
        copied = _Headers()
        copied._items = self._items[:]
        return copied

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        key_lower = key.lower()
        return any(existing.lower() == key_lower for existing, _ in self._items)


class _URL:
    def __init__(self, value: str) -> None:
        if isinstance(value, _URL):
            value = str(value)
        self._raw = value
        parts = urlsplit(value)
        self.scheme = parts.scheme
        self._netloc = parts.netloc.encode("ascii")
        self.path = parts.path or "/"
        query = parts.query
        self._query = query.encode("ascii") if query else b""
        raw_path = parts.path or "/"
        if query:
            raw_path = f"{raw_path}?{query}"
        self.raw_path = raw_path.encode("ascii")

    @property
    def netloc(self) -> bytes:
        return self._netloc

    @property
    def query(self) -> bytes:
        return self._query

    def __str__(self) -> str:
        return self._raw


class ByteStream:
    def __init__(self, content: bytes) -> None:
        self._content = content
        self._consumed = False

    def read(self) -> bytes:
        if self._consumed:
            return b""
        self._consumed = True
        return self._content


class Request:
    def __init__(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | Iterable[tuple[str, str]] | None = None,
        stream: ByteStream | None = None,
    ) -> None:
        self.method = method.upper()
        self.url = _URL(url)
        self.headers = _Headers(headers)
        self._stream = stream or ByteStream(b"")

    def read(self) -> bytes:
        return self._stream.read()


class Response:
    def __init__(
        self,
        status_code: int,
        *,
        headers: Mapping[str, str] | Iterable[tuple[str, str]] | None = None,
        content: bytes | str | None = None,
        stream: ByteStream | None = None,
        request: Request | None = None,
    ) -> None:
        self.status_code = status_code
        self.headers = _Headers(headers)
        self.request = request
        if stream is not None:
            self._content = stream.read()
        elif content is None:
            self._content = b""
        elif isinstance(content, str):
            self._content = content.encode("utf-8")
        else:
            self._content = content
        self.reason_phrase = ""

    def read(self) -> bytes:
        return self._content

    @property
    def text(self) -> str:
        return self._content.decode("utf-8")

    def json(self) -> Any:
        if not self._content:
            return None
        return json.loads(self.text)


class BaseTransport:
    def handle_request(self, request: Request) -> Response:
        raise NotImplementedError


class _Cookies(dict[str, str]):
    def __str__(self) -> str:
        return "; ".join(f"{k}={v}" for k, v in self.items())


def _encode_params(params: Any) -> str:
    if params is None:
        return ""
    if isinstance(params, (list, tuple)):
        return urlencode(params)
    if isinstance(params, Mapping):
        return urlencode(list(params.items()))
    return str(params)


class Client:
    def __init__(
        self,
        *,
        base_url: str = "",
        headers: Mapping[str, str] | None = None,
        transport: BaseTransport | None = None,
        follow_redirects: bool | None = None,
        cookies: Mapping[str, str] | None = None,
    ) -> None:
        self.base_url = base_url or ""
        self._headers = _Headers(headers)
        self._transport = transport or BaseTransport()
        self.follow_redirects = follow_redirects
        self.cookies = _Cookies()
        if cookies:
            self.cookies.update({str(k): str(v) for k, v in cookies.items()})

    def _merge_url(self, url: str | _URL) -> str:
        target = str(url)
        if target.startswith("http://") or target.startswith("https://"):
            return target
        if self.base_url:
            return urljoin(self.base_url, target)
        return target

    def _prepare_headers(self, headers: Mapping[str, str] | None) -> _Headers:
        combined = self._headers.copy()
        if headers:
            combined.update(headers)
        if self.cookies:
            combined.add("cookie", str(self.cookies))
        return combined

    def request(
        self,
        method: str,
        url: str,
        *,
        content: bytes | str | None = None,
        data: Mapping[str, Any] | Sequence[tuple[str, Any]] | str | None = None,
        files: Any = None,
        json: Any = None,
        params: Any = None,
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, str] | None = None,
        auth: Any = None,
        follow_redirects: Any = None,
        timeout: Any = None,
        extensions: Any = None,
    ) -> Response:
        url_str = self._merge_url(url)
        if params:
            suffix = _encode_params(params)
            connector = "&" if urlsplit(url_str).query else "?"
            url_str = f"{url_str}{connector}{suffix}"
        body: bytes = b""
        if json is not None:
            body = json_dumps(json)
            headers = {**(headers or {}), "content-type": "application/json"}
        elif content is not None:
            body = content.encode("utf-8") if isinstance(content, str) else content
        elif data is not None:
            if isinstance(data, (list, tuple)):
                body = urlencode(data).encode()
            elif isinstance(data, Mapping):
                body = urlencode(list(data.items())).encode()
            else:
                body = str(data).encode()
        elif files is not None:
            raise NotImplementedError("File uploads not supported in stub httpx client")
        final_headers = self._prepare_headers(headers)
        if cookies:
            cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
            final_headers.add("cookie", cookie_header)
        request = Request(method=method, url=url_str, headers=final_headers.multi_items(), stream=ByteStream(body))
        response = self._transport.handle_request(request)
        response.request = request
        return response

    def get(self, url: str, **kwargs: Any) -> Response:
        return self.request("GET", url, **kwargs)

    def options(self, url: str, **kwargs: Any) -> Response:
        return self.request("OPTIONS", url, **kwargs)

    def head(self, url: str, **kwargs: Any) -> Response:
        return self.request("HEAD", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> Response:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> Response:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> Response:
        return self.request("DELETE", url, **kwargs)

    def close(self) -> None:  # pragma: no cover - compatibility only
        return None

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def json_dumps(data: Any) -> bytes:
    return json.dumps(data).encode("utf-8")


class _UseClientDefault:
    pass


USE_CLIENT_DEFAULT = _UseClientDefault()


class _TypesModule(types.ModuleType):
    URLTypes = str
    RequestContent = bytes | str | None
    RequestFiles = Any
    QueryParamTypes = Any
    HeaderTypes = Mapping[str, str] | Iterable[tuple[str, str]] | None
    CookieTypes = Mapping[str, str] | Iterable[tuple[str, str]] | None
    AuthTypes = Any
    TimeoutTypes = Any


class _ClientModule(types.ModuleType):
    UseClientDefault = _UseClientDefault
    USE_CLIENT_DEFAULT = USE_CLIENT_DEFAULT


def install_httpx_stub() -> None:
    if "httpx" in sys.modules:
        return
    module = types.ModuleType("httpx")
    module.Client = Client
    module.BaseTransport = BaseTransport
    module.Request = Request
    module.Response = Response
    module.ByteStream = ByteStream
    module.Headers = _Headers
    module.URL = _URL
    module.__all__ = [
        "Client",
        "BaseTransport",
        "Request",
        "Response",
        "ByteStream",
    ]
    types_module = _TypesModule("httpx._types")
    client_module = _ClientModule("httpx._client")
    sys.modules["httpx._types"] = types_module
    sys.modules["httpx._client"] = client_module
    module._types = types_module  # type: ignore[attr-defined]
    module._client = client_module  # type: ignore[attr-defined]
    sys.modules["httpx"] = module
