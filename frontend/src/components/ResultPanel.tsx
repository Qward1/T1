interface ResultPanelProps {
  category: string;
  subcategory: string;
  confidence: number;
  error?: string | null;
  loading?: boolean;
}

const ResultPanel = ({ category, subcategory, confidence, error, loading }: ResultPanelProps) => {
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
            <span className="label">Подкатегория</span>
            <span>{subcategory || "—"}</span>
          </div>
          <div className="classification-row">
            <span className="label">Уверенность</span>
            <span>
              {Number.isFinite(confidence) ? `${Math.round(confidence * 100)}%` : "—"}
            </span>
          </div>
        </>
      )}
    </section>
  );
};

export default ResultPanel;
