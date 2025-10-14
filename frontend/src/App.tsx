import { useEffect, useState } from "react";

import AnalyzeForm from "./components/AnalyzeForm";
import AnalyticsPanel from "./components/AnalyticsPanel";
import EntityEditor from "./components/EntityEditor";
import FeedbackForm from "./components/FeedbackForm";
import FinalAnswer from "./components/FinalAnswer";
import Recommendations from "./components/Recommendations";
import ResultPanel from "./components/ResultPanel";
import {
  analyze,
  feedback as sendLegacyFeedback,
  getAnalytics,
  respond,
  sendClassificationFeedback,
  sendTemplateFeedback,
  submitHistory,
} from "./lib/api";
import type {
  AnalyzeResponse,
  AnalyticsData,
  EntityMap,
  Recommendation,
} from "./types";

const resolveErrorMessage = (error: unknown) =>
  error instanceof Error ? error.message : "Unexpected error. Please try again.";

const App = () => {
  const [query, setQuery] = useState("");
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [entities, setEntities] = useState<EntityMap>({});
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<Recommendation | null>(null);
  const [finalAnswer, setFinalAnswer] = useState("");

  const [loadingAnalyze, setLoadingAnalyze] = useState(false);
  const [loadingRespond, setLoadingRespond] = useState(false);
  const [classificationLoading, setClassificationLoading] = useState(false);
  const [classificationError, setClassificationError] = useState<string | null>(null);

  const [feedbackNotes, setFeedbackNotes] = useState("");
  const [feedbackStatus, setFeedbackStatus] = useState<"idle" | "success" | "error">("idle");
  const [feedbackMessage, setFeedbackMessage] = useState("");
  const [feedbackSending, setFeedbackSending] = useState(false);

  const [historySubmitting, setHistorySubmitting] = useState(false);
  const [historyStatus, setHistoryStatus] = useState<"idle" | "success" | "error">("idle");
  const [historyMessage, setHistoryMessage] = useState("");

  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);

  const refreshAnalytics = async () => {
    setAnalyticsLoading(true);
    setAnalyticsError(null);
    try {
      const data = await getAnalytics();
      setAnalytics(data);
    } catch (error) {
      setAnalyticsError(resolveErrorMessage(error));
    } finally {
      setAnalyticsLoading(false);
    }
  };

  useEffect(() => {
    refreshAnalytics();
  }, []);

  const handleAnalyze = async () => {
    if (!query.trim()) {
      return;
    }

    setLoadingAnalyze(true);
    setClassificationError(null);
    setFeedbackStatus("idle");
    setFeedbackMessage("");
    setHistoryStatus("idle");
    setHistoryMessage("");
    setEntities({});

    try {
      const result = await analyze({ text: query.trim() });
      setAnalysis(result);
      setEntities(result.entities);
      setRecommendations(result.recommendations);
      setSelectedTemplate(result.recommendations[0] ?? null);
      setFinalAnswer("");
    } catch (error) {
      setAnalysis(null);
      setRecommendations([]);
      setSelectedTemplate(null);
      setFinalAnswer("");
      setClassificationError(resolveErrorMessage(error));
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
    setHistoryStatus("idle");
    setHistoryMessage("");
  };

  const handleGenerateAnswer = async () => {
    if (!selectedTemplate) {
      return;
    }

    setLoadingRespond(true);
    setFeedbackStatus("idle");
    setFeedbackMessage("");

    try {
      const result = await respond({ template: selectedTemplate.answer, entities });
      setFinalAnswer(result.answer);
    } catch (error) {
      setFeedbackStatus("error");
      setFeedbackMessage(resolveErrorMessage(error));
    } finally {
      setLoadingRespond(false);
    }
  };

  const handleAnswerChange = (value: string) => {
    setFinalAnswer(value);
  };

  const handleCopy = async () => {
    if (!finalAnswer) {
      return;
    }

    try {
      await navigator.clipboard.writeText(finalAnswer);
      setHistoryStatus("success");
      setHistoryMessage("Answer copied to clipboard.");
    } catch {
      setHistoryStatus("error");
      setHistoryMessage("Failed to copy answer. Please copy manually.");
    }
  };

  const handleClassificationFeedback = async (isCorrect: boolean) => {
    if (!analysis) {
      return;
    }

    setClassificationLoading(true);
    setClassificationError(null);
    try {
      const data = await sendClassificationFeedback({
        category: analysis.category,
        subcategory: analysis.subcategory,
        is_correct: isCorrect,
      });
      setAnalytics(data);
    } catch (error) {
      setClassificationError(resolveErrorMessage(error));
    } finally {
      setClassificationLoading(false);
    }
  };

  const handleTemplateFeedback = async (isPositive: boolean) => {
    if (!analysis || !finalAnswer) {
      return;
    }

    setFeedbackSending(true);
    setFeedbackStatus("idle");
    setFeedbackMessage("");

    try {
      const analyticsData = await sendTemplateFeedback({ is_positive: isPositive });
      setAnalytics(analyticsData);

      await sendLegacyFeedback({
        query,
        category: analysis.category,
        subcategory: analysis.subcategory,
        selected_template_id: selectedTemplate?.id ?? null,
        final_answer: finalAnswer,
        is_helpful: isPositive,
        notes: feedbackNotes || null,
      });

      setFeedbackStatus("success");
      setFeedbackMessage(
        isPositive
          ? "Template confirmed."
          : "Template flagged for improvement.",
      );
      setFeedbackNotes("");
    } catch (error) {
      setFeedbackStatus("error");
      setFeedbackMessage(resolveErrorMessage(error));
    } finally {
      setFeedbackSending(false);
    }
  };

  const handleSubmitHistory = async () => {
    if (!analysis || !finalAnswer.trim() || !query.trim()) {
      setHistoryStatus("error");
      setHistoryMessage("Provide both the customer request and the final answer.");
      return;
    }

    setHistorySubmitting(true);
    setHistoryStatus("idle");
    setHistoryMessage("");

    try {
      const data = await submitHistory({
        query,
        category: analysis.category,
        subcategory: analysis.subcategory,
        template_id: selectedTemplate?.id ?? null,
        final_answer: finalAnswer,
      });
      setAnalytics(data);
      setHistoryStatus("success");
      setHistoryMessage("Response saved to history.");
    } catch (error) {
      setHistoryStatus("error");
      setHistoryMessage(resolveErrorMessage(error));
    } finally {
      setHistorySubmitting(false);
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
        <AnalyticsPanel data={analytics} loading={analyticsLoading} error={analyticsError} />
      </div>

      <div className="column">
        <ResultPanel
          category={analysis?.category ?? ""}
          categoryConfidence={analysis?.category_confidence ?? Number.NaN}
          subcategory={analysis?.subcategory ?? ""}
          subcategoryConfidence={analysis?.subcategory_confidence ?? Number.NaN}
          products={analysis?.products ?? []}
          onFeedback={analysis ? handleClassificationFeedback : undefined}
          feedbackDisabled={classificationLoading}
          error={classificationError}
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
          onSubmit={handleSubmitHistory}
          canGenerate={Boolean(selectedTemplate)}
          canSubmit={Boolean(analysis && finalAnswer && query)}
          loading={loadingRespond}
          submitting={historySubmitting}
        />
        {historyStatus !== "idle" && (
          <p className={`feedback-message ${historyStatus}`}>{historyMessage}</p>
        )}
        <FeedbackForm
          notes={feedbackNotes}
          onNotesChange={setFeedbackNotes}
          onSend={handleTemplateFeedback}
          disabled={!analysis || !finalAnswer}
          loading={feedbackSending}
          status={feedbackStatus}
          message={feedbackMessage}
        />
      </div>
    </div>
  );
};

export default App;

