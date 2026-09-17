const API_BASE =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";


export function getToken() {
  return localStorage.getItem(
    "nexus_token",
  );
}


export function setToken(token) {
  localStorage.setItem(
    "nexus_token",
    token,
  );
}


export function clearToken() {
  localStorage.removeItem(
    "nexus_token",
  );
}


async function parseResponse(
  response,
) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}


export async function apiRequest(
  path,
  options = {},
) {
  const token = getToken();

  const headers = {
    ...(options.headers || {}),
  };

  if (
    token &&
    !headers.Authorization
  ) {
    headers.Authorization =
      `Bearer ${token}`;
  }

  if (
    options.body &&
    !(
      options.body
      instanceof FormData
    ) &&
    !headers["Content-Type"]
  ) {
    headers["Content-Type"] =
      "application/json";
  }

  const response = await fetch(
    `${API_BASE}${path}`,
    {
      ...options,
      headers,
    },
  );

  if (response.status === 204) {
    return null;
  }

  const data =
    await parseResponse(
      response,
    );

  if (!response.ok) {
    if (
      response.status === 401
    ) {
      clearToken();
    }

    const detail =
      data?.detail;

    const message =
      typeof detail === "string"
        ? detail
        : detail
          ? JSON.stringify(
              detail,
            )
          : `Request failed with status ${response.status}`;

    throw new Error(
      message,
    );
  }

  return data;
}


export function mediaUrl(path) {
  if (!path) {
    return null;
  }

  if (
    path.startsWith(
      "http://",
    ) ||
    path.startsWith(
      "https://",
    )
  ) {
    return path;
  }

  return `${API_BASE}${path}`;
}