import axios from "axios";

const hfVariables =
  typeof window !== "undefined" ? window.huggingface?.variables || {} : {};

const baseURL =
  hfVariables.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  "/api";

export const apiClient = axios.create({
  baseURL,
  timeout: 15000
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("ozelgelab_token");
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err?.response?.status;
    const method = err?.config?.method?.toUpperCase();
    const url = err?.config?.url;
    const detail = err?.response?.data?.detail;
    console.error("[api:error]", {
      method,
      url,
      status,
      code: err?.code,
      detail,
      message: err?.message
    });
    const isLoginAttempt = url === "/auth/login" || url === "/auth/login-form";
    if (status === 401 && !isLoginAttempt) {
      window.dispatchEvent(new CustomEvent("auth:unauthorized"));
    }
    return Promise.reject(err);
  }
);

