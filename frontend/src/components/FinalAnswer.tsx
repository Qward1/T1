interface FinalAnswerProps {
  value: string;
  onChange: (value: string) => void;
  onGenerate: () => void;
  onCopy: () => void;
  onSubmit: () => void;
  canGenerate: boolean;
  canSubmit: boolean;
  loading: boolean;
  submitting: boolean;
}

const FinalAnswer = ({
  value,
  onChange,
  onGenerate,
  onCopy,
  onSubmit,
  canGenerate,
  canSubmit,
  loading,
  submitting,
}: FinalAnswerProps) => {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Финальный ответ</h2>
        <div className="actions">
          <button type="button" onClick={onCopy} disabled={!value}>
            Копировать
          </button>
          <button type="button" onClick={onGenerate} disabled={!canGenerate || loading}>
            {loading ? "Генерация..." : "Сформировать"}
          </button>
          <button type="button" onClick={onSubmit} disabled={!canSubmit || submitting}>
            {submitting ? "Отправляем..." : "Отправить ответ"}
          </button>
        </div>
      </div>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Отредактируйте ответ перед отправкой клиенту..."
        rows={10}
      />
    </section>
  );
};

export default FinalAnswer;

