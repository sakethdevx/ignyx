class Router:
    def __init__(self, prefix=""):
        self.prefix = prefix.rstrip("/")
        self.routes = []

    def _add_route(self, method, path, handler):
        full_path = self.prefix + path
        self.routes.append((method, full_path, handler))

    def get(self, path):
        def decorator(func):
            self._add_route("GET", path, func)
            return func
        return decorator

    def post(self, path):
        def decorator(func):
            self._add_route("POST", path, func)
            return func
        return decorator

    def put(self, path):
        def decorator(func):
            self._add_route("PUT", path, func)
            return func
        return decorator

    def delete(self, path):
        def decorator(func):
            self._add_route("DELETE", path, func)
            return func
        return decorator

