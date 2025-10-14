import type { Recommendation } from "../types";

interface RecommendationsProps {
  items: Recommendation[];
  selectedId: number | null;
  onSelect: (item: Recommendation) => void;
}

const Recommendations = ({ items, selectedId, onSelect }: RecommendationsProps) => {
  return (
    <section className="panel">
      <h2>Рекомендации</h2>
      {items.length === 0 ? (
        <p>Подходящие ответы появятся после анализа.</p>
      ) : (
        <ul className="recommendation-list">
          {items.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className={selectedId === item.id ? "active" : ""}
                onClick={() => onSelect(item)}
              >
                <header>
                  <span className="badge">{item.category}</span>
                  <span className="badge secondary">{item.subcategory}</span>
                  <span className="score">{Math.round(item.score * 100) / 100}</span>
                </header>
                <p className="question">{item.question}</p>
                <p className="audience">Аудитория: {item.audience ?? "не указано"}</p>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
};

export default Recommendations;

