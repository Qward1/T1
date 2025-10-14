interface FinalAnswerProps {
  value: string;
  onChange: (value: string) => void;
  onGenerate: () => void;
  onCopy: () => void;
  canGenerate: boolean;
  loading: boolean;
}

const FinalAnswer = ({
  value,
  onChange,
  onGenerate,
  onCopy,
  canGenerate,
  loading,
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

