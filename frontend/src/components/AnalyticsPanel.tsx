import type { AnalyticsData } from "../types";

interface AnalyticsPanelProps {
  data: AnalyticsData | null;
  loading: boolean;
  error: string | null;
}

const formatPercent = (value: number) =>
  Number.isFinite(value) ? `${Math.round(value * 100)}%` : "—";

const AnalyticsPanel = ({ data, loading, error }: AnalyticsPanelProps) => {
  return (
    <section className="panel">
      <h2>Аналитика</h2>
      {loading ? (
        <p>Обновляем статистику...</p>
      ) : error ? (
        <p>Не удалось загрузить аналитику: {error}</p>
      ) : !data ? (
        <p>Данные аналитики появятся после первых запросов.</p>
      ) : (
        <>
          <div className="analytics-section">
            <h3>Точность классификации</h3>
            {data.classification.length === 0 ? (
              <p>Пока нет оценок по категориям.</p>
            ) : (
              <table className="analytics-table">
                <thead>
                  <tr>
                    <th>Категория</th>
                    <th>Подкатегория</th>
                    <th>Верно</th>
                    <th>Неверно</th>
                    <th>Точность</th>
                  </tr>
                </thead>
                <tbody>
                  {data.classification.map((item) => (
                    <tr key={`${item.category}__${item.subcategory}`}>
                      <td>{item.category}</td>
                      <td>{item.subcategory}</td>
                      <td>{item.correct}</td>
                      <td>{item.incorrect}</td>
                      <td>{formatPercent(item.accuracy)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="analytics-section">
            <h3>Оценка шаблонов</h3>
            <p>
              Да: <strong>{data.template.positive}</strong> · Нет:{" "}
              <strong>{data.template.negative}</strong> · Точность:{" "}
              <strong>{formatPercent(data.template.accuracy)}</strong>
            </p>
          </div>

          <div className="analytics-section">
            <h3>История запросов</h3>
            {data.history.length === 0 ? (
              <p>История пока пуста.</p>
            ) : (
              <ul className="history-list">
                {data.history.map((item) => (
                  <li key={item.id}>
                    <header>
                      <span className="label">Запрос:</span> {item.query}
                    </header>
                    <div>
                      <span className="label">Категория:</span> {item.category || "—"} ·{" "}
                      <span className="label">Подкатегория:</span> {item.subcategory || "—"}
                    </div>
                    <div>
                      <span className="label">Ответ:</span> {item.final_answer || "—"}
                    </div>
                    <div className="history-timestamp">{item.created_at}</div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </section>
  );
};

export default AnalyticsPanel;

