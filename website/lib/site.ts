export const siteConfig = {
  basePath: process.env.NEXT_PUBLIC_BASE_PATH ?? "",
  githubUrl: "https://github.com/sakethdevx/ignyx",
};

export function withBasePath(path: string) {
  if (!path) {
    return siteConfig.basePath || "/";
  }

  if (path.startsWith("http://") || path.startsWith("https://") || path.startsWith("mailto:")) {
    return path;
  }

  if (path.startsWith("#")) {
    return path;
  }

  return `${siteConfig.basePath}${path}`;
}

export function docsPath(path = "/") {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return withBasePath(`/docs${normalized === "/" ? "/" : normalized}`);
}
