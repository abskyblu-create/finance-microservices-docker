const API1_URL = import.meta.env.VITE_API1_URL || "http://localhost:8001";
const API2_URL = import.meta.env.VITE_API2_URL || "http://localhost:8002";

async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export const taskApi = {
  list: () => request(`${API1_URL}/subscriptions`),
  create: (payload) => request(`${API1_URL}/subscriptions`, { method: "POST", body: JSON.stringify(payload) }),
  remove: (id) => request(`${API1_URL}/subscriptions/${id}`, { method: "DELETE" }),
  update: (id, payload) => request(`${API1_URL}/subscriptions/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
};

export const resourceApi = {
  totals: () => request(`${API2_URL}/analytics/totals`),
  categoryBreakdown: () => request(`${API2_URL}/analytics/category-breakdown`),
  recommendations: () => request(`${API2_URL}/analytics/recommendations`),
  upcomingCosts: () => request(`${API2_URL}/analytics/upcoming-costs`),
  budgetStatus: () => request(`${API2_URL}/analytics/budget-status`),
  upsertBudget: (payload) => request(`${API2_URL}/analytics/budget`, { method: "POST", body: JSON.stringify(payload) }),
};
