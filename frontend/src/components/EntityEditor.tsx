import { type ChangeEvent } from "react";

import type { EntityMap } from "../types";

interface EntityEditorProps {
  entities: EntityMap;
  onChange: (key: string, value: string) => void;
  disabled?: boolean;
}

const EntityEditor = ({ entities, onChange, disabled = false }: EntityEditorProps) => {
  const handleChange = (event: ChangeEvent<HTMLInputElement>, key: string) => {
    onChange(key, event.target.value);
  };

  const entries = Object.entries(entities);

  return (
    <section className="panel">
      <h2>Сущности</h2>
      {entries.length === 0 ? (
        <p>Сущности появятся после анализа запроса.</p>
      ) : (
        <div className="entity-grid">
          {entries.map(([key, value]) => (
            <label key={key} className="entity-item">
              <span className="label">{key}</span>
              <input
                value={value}
                onChange={(event) => handleChange(event, key)}
                disabled={disabled}
              />
            </label>
          ))}
        </div>
      )}
    </section>
  );
};

export default EntityEditor;
