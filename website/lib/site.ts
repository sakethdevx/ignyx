export const siteConfig = {
  basePath: process.env.NEXT_PUBLIC_BASE_PATH ?? "",
  githubUrl: "https://github.com/sakethdevx/ignyx",
  docsSiteUrl:
    process.env.NEXT_PUBLIC_DOCS_SITE_URL ?? "https://sakethdevx.github.io/ignyx/docs",
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
  return `/docs${normalized === "/" ? "/" : normalized}`;
}

export function externalDocsUrl(path = "/") {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  const trimmedBase = siteConfig.docsSiteUrl.replace(/\/$/, "");
  return normalized === "/" ? `${trimmedBase}/` : `${trimmedBase}${normalized}`;
}

export function marketingDocsHref(path = "/") {
  if (siteConfig.basePath) {
    return externalDocsUrl(path);
  }

  return docsPath(path);
}
