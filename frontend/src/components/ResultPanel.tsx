interface ResultPanelProps {
  category: string;
  categoryConfidence: number;
  subcategory: string;
  subcategoryConfidence: number;
  products: string[];
  onFeedback?: (isCorrect: boolean) => void;
  feedbackDisabled?: boolean;
  error?: string | null;
  loading?: boolean;
}

const formatPercent = (value: number) =>
  Number.isFinite(value) ? `${Math.round(value * 100)}%` : "—";

const ResultPanel = ({
  category,
  categoryConfidence,
  subcategory,
  subcategoryConfidence,
  products,
  onFeedback,
  feedbackDisabled = false,
  error,
  loading,
}: ResultPanelProps) => {
  if (error) {
    return (
      <section className="panel danger">
        <h2>Ошибка</h2>
        <p>{error}</p>
      </section>
    );
  }

  return (
    <section className="panel">
      <h2>Классификация</h2>
      {loading ? (
        <p>Анализируем запрос...</p>
      ) : (
        <>
          <div className="classification-row">
            <span className="label">Категория</span>
            <span>{category || "—"}</span>
          </div>
          <div className="classification-row">
            <span className="label">Уверенность</span>
            <span>{formatPercent(categoryConfidence)}</span>
          </div>
          <div className="classification-row">
            <span className="label">Подкатегория</span>
            <span>{subcategory || "—"}</span>
          </div>
          <div className="classification-row">
            <span className="label">Уверенность</span>
            <span>{formatPercent(subcategoryConfidence)}</span>
          </div>
          <div className="classification-row">
            <span className="label">Продукты</span>
            <span>{products.length ? products.join(", ") : "не обнаружены"}</span>
          </div>
          {onFeedback && (
            <div className="feedback-actions">
              <button
                type="button"
                onClick={() => onFeedback(true)}
                disabled={feedbackDisabled}
                className="positive"
              >
                Верно
              </button>
              <button
                type="button"
                onClick={() => onFeedback(false)}
                disabled={feedbackDisabled}
                className="negative"
              >
                Неверно
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
};

export default ResultPanel;

