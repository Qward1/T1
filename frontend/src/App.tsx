import { useState } from "react";

import AnalyzeForm from "./components/AnalyzeForm";
import EntityEditor from "./components/EntityEditor";
import FeedbackForm from "./components/FeedbackForm";
import FinalAnswer from "./components/FinalAnswer";
import Recommendations from "./components/Recommendations";
import ResultPanel from "./components/ResultPanel";
import { analyze, feedback, respond } from "./lib/api";
import type { AnalyzeResponse, EntityMap, Recommendation } from "./types";

const App = () => {
  const [query, setQuery] = useState("");
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [entities, setEntities] = useState<EntityMap>({});
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<Recommendation | null>(null);
  const [finalAnswer, setFinalAnswer] = useState("");
  const [loadingAnalyze, setLoadingAnalyze] = useState(false);
  const [loadingRespond, setLoadingRespond] = useState(false);
  const [feedbackNotes, setFeedbackNotes] = useState("");
  const [feedbackStatus, setFeedbackStatus] = useState<"idle" | "success" | "error">("idle");
  const [feedbackMessage, setFeedbackMessage] = useState("");
  const [feedbackSending, setFeedbackSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resetFeedback = () => {
    setFeedbackNotes("");
    setFeedbackMessage("");
    setFeedbackStatus("idle");
    setFeedbackSending(false);
  };

  const handleAnalyze = async () => {
    if (!query.trim()) {
      return;
    }

    setLoadingAnalyze(true);
    setError(null);
    resetFeedback();
    setEntities({});

    try {
      const result = await analyze({ text: query.trim() });
      setAnalysis(result);
      setEntities(result.entities);
      setRecommendations(result.recommendations);
      setSelectedTemplate(result.recommendations[0] ?? null);
      setFinalAnswer("");
    } catch (exception) {
      const message =
        exception instanceof Error ? exception.message : "Не удалось выполнить анализ.";
      setError(message);
      setAnalysis(null);
      setRecommendations([]);
      setSelectedTemplate(null);
      setFinalAnswer("");
    } finally {
      setLoadingAnalyze(false);
    }
  };

  const handleEntityChange = (key: string, value: string) => {
    setEntities((current) => ({ ...current, [key]: value }));
  };

  const handleSelectRecommendation = (item: Recommendation) => {
    setSelectedTemplate(item);
    setFinalAnswer("");
    resetFeedback();
  };

  const handleGenerateAnswer = async () => {
    if (!selectedTemplate) {
      return;
    }

    setLoadingRespond(true);
    resetFeedback();

    try {
      const result = await respond({ template: selectedTemplate.answer, entities });
      setFinalAnswer(result.answer);
    } catch (exception) {
      const message =
        exception instanceof Error ? exception.message : "Не удалось сформировать ответ.";
      setFeedbackStatus("error");
      setFeedbackMessage(message);
    } finally {
      setLoadingRespond(false);
    }
  };

  const handleAnswerChange = (value: string) => {
    setFinalAnswer(value);
    if (feedbackStatus !== "idle") {
      setFeedbackStatus("idle");
      setFeedbackMessage("");
    }
  };

  const handleCopy = async () => {
    if (!finalAnswer) {
      return;
    }

    try {
      await navigator.clipboard.writeText(finalAnswer);
      setFeedbackStatus("success");
      setFeedbackMessage("Ответ скопирован в буфер обмена.");
    } catch {
      setFeedbackStatus("error");
      setFeedbackMessage("Не удалось скопировать ответ. Попробуйте вручную.");
    }
  };

  const handleSendFeedback = async (isHelpful: boolean) => {
    if (!finalAnswer || !analysis) {
      return;
    }

    setFeedbackSending(true);
    setFeedbackStatus("idle");
    setFeedbackMessage("");

    try {
      await feedback({
        query,
        category: analysis.category,
        subcategory: analysis.subcategory,
        selected_template_id: selectedTemplate?.id ?? null,
        final_answer: finalAnswer,
        is_helpful: isHelpful,
        notes: feedbackNotes || null,
      });
      setFeedbackStatus("success");
      setFeedbackMessage("Спасибо! Отзыв сохранён.");
    } catch (exception) {
      const message =
        exception instanceof Error ? exception.message : "Не удалось отправить отзыв.";
      setFeedbackStatus("error");
      setFeedbackMessage(message);
    } finally {
      setFeedbackSending(false);
    }
  };

  return (
    <div className="layout">
      <div className="column">
        <AnalyzeForm
          value={query}
          onChange={setQuery}
          onSubmit={handleAnalyze}
          loading={loadingAnalyze}
        />
        <EntityEditor entities={entities} onChange={handleEntityChange} disabled={!analysis} />
      </div>
      <div className="column">
        <ResultPanel
          category={analysis?.category ?? ""}
          categoryConfidence={analysis?.category_confidence ?? Number.NaN}
          subcategory={analysis?.subcategory ?? ""}
          subcategoryConfidence={analysis?.subcategory_confidence ?? Number.NaN}
          error={error}
          loading={loadingAnalyze}
        />
        <Recommendations
          items={recommendations}
          selectedId={selectedTemplate?.id ?? null}
          onSelect={handleSelectRecommendation}
        />
        <FinalAnswer
          value={finalAnswer}
          onChange={handleAnswerChange}
          onGenerate={handleGenerateAnswer}
          onCopy={handleCopy}
          canGenerate={Boolean(selectedTemplate)}
          loading={loadingRespond}
        />
        <FeedbackForm
          notes={feedbackNotes}
          onNotesChange={setFeedbackNotes}
          onSend={handleSendFeedback}
          disabled={!finalAnswer || feedbackStatus === "success"}
          loading={feedbackSending}
          status={feedbackStatus}
          message={feedbackMessage}
        />
      </div>
    </div>
  );
};

export default App;

