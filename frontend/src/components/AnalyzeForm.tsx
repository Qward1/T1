import { type FormEvent } from "react";

interface AnalyzeFormProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  loading: boolean;
}

const AnalyzeForm = ({ value, onChange, onSubmit, loading }: AnalyzeFormProps) => {
  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <form className="panel" onSubmit={handleSubmit}>
      <h2>Запрос клиента</h2>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Вставьте текст обращения клиента..."
        rows={8}
        required
        disabled={loading}
      />
      <button type="submit" disabled={loading}>
        {loading ? "Анализ..." : "Анализировать"}
      </button>
    </form>
  );
};

export default AnalyzeForm;
