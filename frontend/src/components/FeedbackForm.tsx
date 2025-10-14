interface FeedbackFormProps {
  notes: string;
  onNotesChange: (value: string) => void;
  onSend: (isHelpful: boolean) => void;
  disabled: boolean;
  loading: boolean;
  status: "idle" | "success" | "error";
  message: string;
}

const FeedbackForm = ({
  notes,
  onNotesChange,
  onSend,
  disabled,
  loading,
  status,
  message,
}: FeedbackFormProps) => {
  return (
    <section className="panel">
      <h2>Обратная связь</h2>
      <textarea
        value={notes}
        onChange={(event) => onNotesChange(event.target.value)}
        placeholder="Добавьте комментарий для команды обучения модели..."
        rows={4}
        disabled={disabled}
      />
      <div className="feedback-actions">
        <button
          type="button"
          onClick={() => onSend(true)}
          disabled={disabled || loading}
          className="positive"
        >
          Полезно
        </button>
        <button
          type="button"
          onClick={() => onSend(false)}
          disabled={disabled || loading}
          className="negative"
        >
          Не помогло
        </button>
      </div>
      {status !== "idle" && <p className={`feedback-message ${status}`}>{message}</p>}
    </section>
  );
};

export default FeedbackForm;

