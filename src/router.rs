use matchit::Router as MatchitRouter;
use std::collections::HashMap;
// use std::sync::Arc; // Removed unused

/// HTTP methods we support
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Method {
    Get,
    Post,
    Put,
    Delete,
    Patch,
    Head,
    Options,
}

impl Method {
    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_uppercase().as_str() {
            "GET" => Some(Method::Get),
            "POST" => Some(Method::Post),
            "PUT" => Some(Method::Put),
            "DELETE" => Some(Method::Delete),
            "PATCH" => Some(Method::Patch),
            "HEAD" => Some(Method::Head),
            "OPTIONS" => Some(Method::Options),
            _ => None,
        }
    }
}

/// Stores the route handler index and any matched path parameters.
pub struct RouteMatch {
    pub handler_index: usize,
    pub params: HashMap<String, String>,
}

/// Radix-tree router using matchit.
/// We maintain a separate matchit::Router per HTTP method.
pub struct Router {
    trees: HashMap<Method, MatchitRouter<usize>>,
    handler_count: usize,
}

impl Router {
    pub fn new() -> Self {
        Self {
            trees: HashMap::new(),
            handler_count: 0,
        }
    }

    /// Insert a route. Returns the handler index assigned.
    pub fn insert(&mut self, method: Method, path: &str) -> Result<usize, String> {
        let index = self.handler_count;
        self.handler_count += 1;

        let tree = self.trees.entry(method).or_default();
        tree.insert(path, index)
            .map_err(|e| format!("Failed to insert route: {e}"))?;

        Ok(index)
    }

    /// Match a request path against registered routes.
    pub fn find(&self, method: Method, path: &str) -> Option<RouteMatch> {
        let tree = self.trees.get(&method)?;
        let matched = tree.at(path).ok()?;

        let params: HashMap<String, String> = matched
            .params
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect();

        Some(RouteMatch {
            handler_index: *matched.value,
            params,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_basic_routing() {
        let mut router = Router::new();
        let idx = router.insert(Method::Get, "/hello").unwrap();
        assert_eq!(idx, 0);

        let m = router.find(Method::Get, "/hello").unwrap();
        assert_eq!(m.handler_index, 0);
        assert!(m.params.is_empty());
    }

    #[test]
    fn test_path_params() {
        let mut router = Router::new();
        router.insert(Method::Get, "/users/{id}").unwrap();

        let m = router.find(Method::Get, "/users/42").unwrap();
        assert_eq!(m.handler_index, 0);
        assert_eq!(m.params.get("id").unwrap(), "42");
    }

    #[test]
    fn test_method_isolation() {
        let mut router = Router::new();
        router.insert(Method::Get, "/test").unwrap();
        router.insert(Method::Post, "/test").unwrap();

        assert!(router.find(Method::Get, "/test").is_some());
        assert!(router.find(Method::Post, "/test").is_some());
        assert!(router.find(Method::Delete, "/test").is_none());
    }
}
