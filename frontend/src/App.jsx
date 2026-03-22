import { useEffect, useMemo, useState } from "react";
import { resourceApi, taskApi } from "./services/api";

function Section({ title, children }) {
  return (
    <section className="card">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

export default function App() {
  const [subscriptions, setSubscriptions] = useState([]);
  const [analytics, setAnalytics] = useState({ monthly_total: 0, yearly_total: 0 });
  const [categoryBreakdown, setCategoryBreakdown] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [upcoming, setUpcoming] = useState([]);
  const [budgetStatus, setBudgetStatus] = useState(null);
  const [subscriptionForm, setSubscriptionForm] = useState({
    name: "",
    provider: "",
    category: "",
    price: "",
    currency: "EUR",
    billing_cycle: "monthly",
    renewal_date: "",
    status: "active",
    notes: "",
  });
  const [budgetForm, setBudgetForm] = useState({ month: new Date().toISOString().slice(0, 7), target_amount: "" });
  const [error, setError] = useState("");

  const dashboard = useMemo(() => {
    const active = subscriptions.filter((subscription) => subscription.status === "active").length;
    const yearlySubscriptions = subscriptions.filter((subscription) => subscription.billing_cycle === "yearly").length;
    const uniqueCategories = new Set(subscriptions.map((subscription) => subscription.category.toLowerCase())).size;
    return {
      subscriptionCount: subscriptions.length,
      active,
      yearlySubscriptions,
      uniqueCategories,
      monthlyTotal: analytics.monthly_total || 0,
      yearlyTotal: analytics.yearly_total || 0,
    };
  }, [subscriptions, analytics]);

  async function loadData() {
    try {
      setError("");
      const [subscriptionData, totalsData, categoryData, recommendationData, upcomingData, budgetData] = await Promise.all([
        taskApi.list(),
        resourceApi.totals(),
        resourceApi.categoryBreakdown(),
        resourceApi.recommendations(),
        resourceApi.upcomingCosts(),
        resourceApi.budgetStatus(),
      ]);
      setSubscriptions(subscriptionData);
      setAnalytics(totalsData);
      setCategoryBreakdown(categoryData);
      setRecommendations(recommendationData);
      setUpcoming(upcomingData.upcoming || []);
      setBudgetStatus(budgetData);
    } catch (err) {
      setError(String(err.message || err));
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function submitSubscription(event) {
    event.preventDefault();
    await taskApi.create({
      ...subscriptionForm,
      price: Number(subscriptionForm.price),
      renewal_date: subscriptionForm.renewal_date || null,
      notes: subscriptionForm.notes || null,
    });
    setSubscriptionForm({
      name: "",
      provider: "",
      category: "",
      price: "",
      currency: "EUR",
      billing_cycle: "monthly",
      renewal_date: "",
      status: "active",
      notes: "",
    });
    await loadData();
  }

  async function submitBudget(event) {
    event.preventDefault();
    await resourceApi.upsertBudget({ month: budgetForm.month, target_amount: Number(budgetForm.target_amount) });
    setBudgetForm({ ...budgetForm, target_amount: "" });
    await loadData();
  }

  return (
    <main className="layout">
      <header className="hero">
        <h1>Personal Finance and Subscription Tracker</h1>
        <p>Manage recurring subscriptions manually and review spending insights from isolated microservices.</p>
      </header>

      {error ? <p className="error">{error}</p> : null}

      <Section title="Dashboard">
        <div className="stats">
          <article><strong>{dashboard.subscriptionCount}</strong><span>Subscriptions</span></article>
          <article><strong>{dashboard.active}</strong><span>Active</span></article>
          <article><strong>{dashboard.uniqueCategories}</strong><span>Categories</span></article>
          <article><strong>EUR {dashboard.monthlyTotal.toFixed(2)}</strong><span>Monthly Total</span></article>
          <article><strong>EUR {dashboard.yearlyTotal.toFixed(2)}</strong><span>Yearly Total</span></article>
        </div>
      </Section>

      <Section title="Subscriptions">
        <form className="form" onSubmit={submitSubscription}>
          <input
            required
            placeholder="Subscription name"
            value={subscriptionForm.name}
            onChange={(event) => setSubscriptionForm({ ...subscriptionForm, name: event.target.value })}
          />
          <input
            required
            placeholder="Provider"
            value={subscriptionForm.provider}
            onChange={(event) => setSubscriptionForm({ ...subscriptionForm, provider: event.target.value })}
          />
          <input
            required
            placeholder="Category"
            value={subscriptionForm.category}
            onChange={(event) => setSubscriptionForm({ ...subscriptionForm, category: event.target.value })}
          />
          <input
            required
            type="number"
            min="0"
            step="0.01"
            placeholder="Price"
            value={subscriptionForm.price}
            onChange={(event) => setSubscriptionForm({ ...subscriptionForm, price: event.target.value })}
          />
          <input
            placeholder="Currency"
            value={subscriptionForm.currency}
            onChange={(event) => setSubscriptionForm({ ...subscriptionForm, currency: event.target.value.toUpperCase() })}
          />
          <input
            type="date"
            value={subscriptionForm.renewal_date}
            onChange={(event) => setSubscriptionForm({ ...subscriptionForm, renewal_date: event.target.value || null })}
          />
          <select
            value={subscriptionForm.billing_cycle}
            onChange={(event) => setSubscriptionForm({ ...subscriptionForm, billing_cycle: event.target.value })}
          >
            <option value="monthly">Monthly</option>
            <option value="yearly">Yearly</option>
          </select>
          <select
            value={subscriptionForm.status}
            onChange={(event) => setSubscriptionForm({ ...subscriptionForm, status: event.target.value })}
          >
            <option value="active">Active</option>
            <option value="paused">Paused</option>
            <option value="canceled">Canceled</option>
          </select>
          <input
            placeholder="Notes (optional)"
            value={subscriptionForm.notes}
            onChange={(event) => setSubscriptionForm({ ...subscriptionForm, notes: event.target.value })}
          />
          <button type="submit">Add Subscription</button>
        </form>
        <ul className="list">
          {subscriptions.map((item) => (
            <li key={item.id}>
              <div>
                <strong>{item.name} ({item.provider})</strong>
                <p>{item.category} | EUR {Number(item.price).toFixed(2)} | {item.billing_cycle}</p>
                <p>{item.status} | renews {item.renewal_date || "not set"}</p>
              </div>
              <button onClick={() => taskApi.remove(item.id).then(loadData)}>Delete</button>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Analytics">
        <form className="form" onSubmit={submitBudget}>
          <input
            required
            type="month"
            value={budgetForm.month}
            onChange={(event) => setBudgetForm({ ...budgetForm, month: event.target.value })}
          />
          <input
            required
            type="number"
            min="0"
            step="0.01"
            placeholder="Budget target"
            value={budgetForm.target_amount}
            onChange={(event) => setBudgetForm({ ...budgetForm, target_amount: event.target.value })}
          />
          <button type="submit">Save Budget</button>
        </form>

        {budgetStatus ? (
          <p>
            Budget status ({budgetStatus.month}): {budgetStatus.status} | total EUR {Number(budgetStatus.monthly_total || 0).toFixed(2)}
          </p>
        ) : null}

        <h3>Category Breakdown (Monthly)</h3>
        <ul className="list">
          {categoryBreakdown.map((item) => (
            <li key={item.category}>
              <div>
                <strong>{item.category}</strong>
                <p>EUR {Number(item.monthly_total).toFixed(2)}</p>
              </div>
            </li>
          ))}
        </ul>

        <h3>Recommendations</h3>
        <ul className="list">
          {recommendations.map((item, idx) => (
            <li key={`${item.message}-${idx}`}>
              <div>
                <strong>Suggestion</strong>
                <p>{item.message}</p>
              </div>
            </li>
          ))}
        </ul>

        <h3>Upcoming Renewals</h3>
        <ul className="list">
          {upcoming.map((item) => (
            <li key={`${item.provider}-${item.name}-${item.renewal_date}`}>
              <div>
                <strong>{item.name}</strong>
                <p>{item.provider} | {item.renewal_date} | EUR {Number(item.amount).toFixed(2)}</p>
              </div>
            </li>
          ))}
        </ul>
      </Section>
    </main>
  );
}
