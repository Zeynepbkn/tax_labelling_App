import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../api/apiClient";
import { useAuth } from "../contexts/AuthContext";
import LoadingSpinner from "../components/LoadingSpinner";
import { formatDocumentTextForReading } from "../utils/textFormatting";
import { PASSING_SCORE } from "../utils/labelingGuideContent";

const LABELING_ROUTE = "/etiketleme";

export default function QuizPage() {
  const { examPassed, refreshMe } = useAuth();
  const navigate = useNavigate();

  const [questions, setQuestions] = useState([]);
  const [practicalQuestions, setPracticalQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [practicalAnswers, setPracticalAnswers] = useState({});
  const [attempts, setAttempts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const goToLabeling = () => navigate(LABELING_ROUTE, { replace: true });

  useEffect(() => {
    let alive = true;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [res, practicalRes, attemptsRes] = await Promise.all([
          apiClient.get("/quiz/questions"),
          apiClient.get("/quiz/practical-questions"),
          apiClient.get("/quiz/my-attempts"),
        ]);
        if (!alive) return;
        setQuestions(res.data || []);
        setPracticalQuestions(practicalRes.data || []);
        setAttempts(attemptsRes.data || []);
      } catch (err) {
        const msg = err?.response?.data?.detail || "Sınav soruları alınamadı.";
        setError(typeof msg === "string" ? msg : "Sınav soruları alınamadı.");
      } finally {
        if (alive) setLoading(false);
      }
    }
    load();
    return () => {
      alive = false;
    };
  }, [examPassed, navigate, result, submitted]);

  const canSubmit = useMemo(() => {
    if (!questions.length) return false;
    const allChoicesAnswered = questions.every((q) => answers[q.id]);
    const allPracticalAnswered = practicalQuestions.every((item) => {
      const values = practicalAnswers[item.training_label_id] || [];
      return Array.from({ length: item.expected_question_count }).every((_, idx) => (values[idx] || "").trim());
    });
    return allChoicesAnswered && allPracticalAnswered;
  }, [questions, answers, practicalQuestions, practicalAnswers]);

  const onSubmit = async () => {
    setSubmitting(true);
    setSubmitted(true);
    setError(null);
    try {
      const payload = { answers: {} };
      for (const q of questions) payload.answers[q.id] = answers[q.id];
      payload.practical_answers = practicalQuestions.map((item) => ({
        training_label_id: item.training_label_id,
        questions: Array.from({ length: item.expected_question_count }).map(
          (_, idx) => practicalAnswers[item.training_label_id]?.[idx] || ""
        ),
      }));
      const res = await apiClient.post("/quiz/submit", payload);
      setResult(res.data);
      await refreshMe();
      const attemptsRes = await apiClient.get("/quiz/my-attempts");
      setAttempts(attemptsRes.data || []);
      // Geçen kullanıcıyı hemen yönlendirme; önce sonucu ve cevap anahtarını görsün,
      // hazır olunca sonuç kartındaki "Etiketlemeye Başla" butonuna kendisi bassın.
    } catch (err) {
      const msg = err?.response?.data?.detail || "Sınav gönderilemedi.";
      setError(typeof msg === "string" ? msg : "Sınav gönderilemedi.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <LoadingSpinner label="Sınav soruları yükleniyor..." />;

  const passingScore = result?.passing_score ?? PASSING_SCORE;
  const quizCompleted = result?.passed || examPassed;

  return (
    <div className="container grid">
      <div className="card">
        <div style={{ fontWeight: 900, fontSize: 20 }}>Mini Sınav</div>
        <div className="muted" style={{ marginTop: 6 }}>
          Tüm soruları cevaplayın ve sınavı gönderin. Geçme notu: {passingScore}.
        </div>
        <div className="card" style={{ marginTop: 12, lineHeight: 1.5 }}>
          Özelge metinlerinden soru veya soruları bağlamıyla çıkarın. Aynı belgede birden fazla talep varsa ortak
          bağlamı her soru için tekrar edin; soru kipi yoksa genellikle "nedir?" sorusuyla tamamlayın.
        </div>

        {error ? <div style={{ marginTop: 10, color: "var(--danger)", fontWeight: 700 }}>{error}</div> : null}

        {result ? (
          <div className="card" style={{ marginTop: 12 }}>
            <div style={{ fontWeight: 900 }}>
              Sonuç: {result.passed ? "Başarılı" : "Başarısız"} (Skor: {result.score})
            </div>
            <div className="row" style={{ gap: 8, flexWrap: "wrap", marginTop: 8 }}>
              <span className="badge">Çoktan seçmeli: {result.multiple_choice_score ?? "-"}</span>
              <span className="badge">Uygulamalı: {result.practical_score ?? "-"}</span>
              <span className="badge">Geçme notu: {result.passing_score}</span>
            </div>
            <div className="muted" style={{ marginTop: 6 }}>
              {result.message}
            </div>
            {result.passed ? (
              <div className="row" style={{ justifyContent: "flex-end", marginTop: 10 }}>
                <button className="btn primary" type="button" onClick={goToLabeling}>
                  Etiketlemeye Başla
                </button>
              </div>
            ) : (
              <div className="notice warning" style={{ marginTop: 12 }}>
                Doğru ve yanlış cevaplarını aşağıda görebilirsiniz. Doğru cevaplara göre aşağıdaki verdiğiniz cevapları
                tekrar düzeltin ve sınavı yeniden gönderin.
              </div>
            )}
            {result.choice_results?.length ? (
              <div className="card" style={{ marginTop: 12 }}>
                <div style={{ fontWeight: 900 }}>Çoktan Seçmeli Sonuçları</div>
                <ul style={{ margin: "8px 0 0", paddingLeft: 18 }}>
                  {result.choice_results.map((item) => (
                    <li key={item.question_id} style={{ marginBottom: 12 }}>
                      <div style={{ fontWeight: 800, color: item.correct ? "var(--success)" : "var(--danger)" }}>
                        {item.correct ? "Doğru" : "Yanlış"}: {item.question_text}
                      </div>
                      <div className="muted" style={{ marginTop: 4 }}>
                        Senin cevabın: {item.selected_option || "-"} - {item.selected_text || "-"}
                      </div>
                      {!item.correct ? (
                        <div style={{ marginTop: 4 }}>
                          Doğru cevap: <b>{item.correct_option}</b> - {item.correct_text}
                        </div>
                      ) : null}
                      {item.explanation ? <div className="muted" style={{ marginTop: 4 }}>{item.explanation}</div> : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {result.practical_results?.length ? (
              <div className="grid" style={{ marginTop: 12 }}>
                {result.practical_results.map((item) => (
                  <div className="card" key={item.training_label_id}>
                    <div style={{ fontWeight: 900 }}>
                      Uygulamalı Soru: Label {item.training_label_id} / Evrak {item.evrak_id} / Skor {item.score}
                    </div>
                    <ul style={{ margin: "8px 0 0", paddingLeft: 18 }}>
                      {item.feedback.map((fb, idx) => (
                        <li key={idx} style={{ marginBottom: 10 }}>
                          <div style={{ fontWeight: 800, color: fb.correct ? "var(--success)" : "var(--danger)" }}>
                            {fb.field}: {fb.correct ? "Doğru" : "Kontrol gerekli"}
                          </div>
                          <div>{fb.message}</div>
                          {!fb.correct ? (
                            <details style={{ marginTop: 6 }}>
                              <summary>Beklenen ve girilen metni göster</summary>
                              <TextDiff expected={fb.expected_preview || ""} received={fb.received_preview || ""} />
                            </details>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      {attempts.length ? (
        <div className="card">
          <div style={{ fontWeight: 900, fontSize: 18 }}>Önceki Denemeler</div>
          <div className="muted" style={{ marginTop: 6 }}>
            Burada yalnızca sizin sınav denemeleriniz gösterilir. Eski denemelerde cevap detayı yoksa sadece skor görünür.
          </div>
          <div className="grid" style={{ marginTop: 12 }}>
            {attempts.map((attempt) => (
              <div className="card" key={attempt.id}>
                <div className="row between">
                  <div style={{ fontWeight: 900 }}>
                    Deneme #{attempt.attempt_number ?? attempt.id} - {attempt.passed ? "Başarılı" : "Başarısız"}
                  </div>
                  <span className="badge">Skor: {attempt.score}</span>
                </div>
                <div className="muted" style={{ marginTop: 6 }}>
                  {attempt.attempted_at ? new Date(attempt.attempted_at).toLocaleString("tr-TR") : "-"}
                  {attempt.multiple_choice_score !== null && attempt.multiple_choice_score !== undefined
                    ? ` | Çoktan seçmeli: ${attempt.multiple_choice_score}`
                    : ""}
                  {attempt.practical_score !== null && attempt.practical_score !== undefined
                    ? ` | Uygulamalı: ${attempt.practical_score}`
                    : ""}
                </div>
                {!attempt.choice_results?.length && !attempt.practical_results?.length ? (
                  <div className="muted" style={{ marginTop: 8 }}>
                    Bu eski denemede cevap detayları kaydedilmemiş; sadece skor bilgisi var.
                  </div>
                ) : (
                  <details style={{ marginTop: 8 }}>
                    <summary>Yanlışları ve detayları göster</summary>
                    <AttemptDetails attempt={attempt} />
                  </details>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="grid">
        {questions.length === 0 ? (
          <div className="card">Aktif sınav sorusu bulunamadı.</div>
        ) : (
          questions.map((q) => (
            <div className="card" key={q.id}>
              <div style={{ fontWeight: 900 }}>{q.question_text}</div>
              <div className="grid" style={{ marginTop: 10 }}>
                {[
                  ["A", q.option_a],
                  ["B", q.option_b],
                  ["C", q.option_c],
                  ["D", q.option_d],
                ].map(([key, label]) => (
                  <label key={key} className="card" style={{ padding: 10, cursor: "pointer" }}>
                    <input
                      type="radio"
                      name={`q-${q.id}`}
                      value={key}
                      checked={answers[q.id] === key}
                      onChange={() => setAnswers((a) => ({ ...a, [q.id]: key }))}
                      style={{ marginRight: 8 }}
                    />
                    <span>
                      <b>{key})</b> {label}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      {practicalQuestions.length ? (
        <div className="card">
          <div style={{ fontWeight: 900, fontSize: 18 }}>Uygulamalı Soru Çıkarma</div>
          <div className="muted" style={{ marginTop: 6 }}>
            Aşağıdaki özelge metinlerinden beklenen soru veya soruları kutulara yazın. Sistem beklenen sorularla
            karşılaştırıp eksik bağlamı, fazla metni ve boşluk farklarını gösterecek.
          </div>
          <div className="grid" style={{ marginTop: 12 }}>
            {practicalQuestions.map((item) => (
              <div className="card" key={item.training_label_id}>
                <div className="row between">
                  <div style={{ fontWeight: 900 }}>
                    Label {item.training_label_id} / Evrak <span className="mono">{item.evrak_id}</span>
                  </div>
                  <span className="badge">Soru: {item.expected_question_count}</span>
                </div>
                {item.focus ? <div className="muted" style={{ marginTop: 8 }}>{item.focus}</div> : null}
                <pre className="card mono" style={{ overflow: "auto", whiteSpace: "pre-wrap", marginTop: 10, maxHeight: 260 }}>
                  {formatDocumentTextForReading(item.ozelge_metni)}
                </pre>
                <div className="grid" style={{ marginTop: 10 }}>
                  {Array.from({ length: item.expected_question_count }).map((_, idx) => (
                    <textarea
                      key={idx}
                      value={practicalAnswers[item.training_label_id]?.[idx] || ""}
                      onChange={(e) =>
                        setPracticalAnswers((prev) => {
                          const nextValues = [...(prev[item.training_label_id] || [])];
                          nextValues[idx] = e.target.value;
                          return { ...prev, [item.training_label_id]: nextValues };
                        })
                      }
                      placeholder={`Soru ${idx + 1}`}
                      style={{ minHeight: 96 }}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="card row between">
        <div className="muted">
          {quizCompleted
            ? "Sınavı geçtiniz. Etiketleme ekranına geçebilirsiniz."
            : result
              ? "Cevaplarınızı yukarıdaki doğru cevaplara göre düzeltin ve sınavı yeniden gönderin."
              : "Tüm çoktan seçmeli ve uygulamalı soru kutuları doldurulmadan gönderemezsiniz."}
        </div>
        {quizCompleted ? (
          <button className="btn primary" onClick={goToLabeling} type="button">
            Sınavı Bitir
          </button>
        ) : (
          <button className="btn primary" disabled={!canSubmit || submitting} onClick={onSubmit} type="button">
            {submitting ? "Gönderiliyor..." : result ? "Sınavı Tekrar Gönder" : "Sınavı Gönder"}
          </button>
        )}
      </div>
    </div>
  );
}

function AttemptDetails({ attempt }) {
  return (
    <div className="grid" style={{ marginTop: 10 }}>
      {attempt.choice_results?.length ? (
        <div className="card">
          <div style={{ fontWeight: 900 }}>Çoktan Seçmeli</div>
          <ul style={{ margin: "8px 0 0", paddingLeft: 18 }}>
            {attempt.choice_results.map((item) => (
              <li key={item.question_id} style={{ marginBottom: 10 }}>
                <div style={{ fontWeight: 800, color: item.correct ? "var(--success)" : "var(--danger)" }}>
                  {item.correct ? "Doğru" : "Yanlış"}: {item.question_text}
                </div>
                {!item.correct ? (
                  <>
                    <div>Senin cevabın: {item.selected_option || "-"} - {item.selected_text || "-"}</div>
                    <div>Doğru cevap: {item.correct_option} - {item.correct_text}</div>
                  </>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {attempt.practical_results?.map((item) => (
        <div className="card" key={item.training_label_id}>
          <div style={{ fontWeight: 900 }}>
            Uygulamalı Label {item.training_label_id} / Evrak {item.evrak_id} / Skor {item.score}
          </div>
          <ul style={{ margin: "8px 0 0", paddingLeft: 18 }}>
            {item.feedback.map((fb, idx) => (
              <li key={idx} style={{ marginBottom: 10 }}>
                <div style={{ fontWeight: 800, color: fb.correct ? "var(--success)" : "var(--danger)" }}>
                  {fb.field}: {fb.correct ? "Doğru" : "Kontrol gerekli"}
                </div>
                <div>{fb.message}</div>
                {!fb.correct ? (
                  <details style={{ marginTop: 6 }}>
                    <summary>Beklenen ve girilen metni göster</summary>
                    <TextDiff expected={fb.expected_preview || ""} received={fb.received_preview || ""} />
                  </details>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function TextDiff({ expected, received }) {
  const rows = buildTextDiff(expected, received);
  return (
    <div className="diffPanel">
      <div className="diffLegend">
        <span className="diffLegendItem diffChanged">Farklı karakter/kelime</span>
        <span className="diffLegendItem diffSpace">Boşluk farkı</span>
        <span className="diffLegendItem diffMissing">Beklenende var</span>
        <span className="diffLegendItem diffExtra">Girilen metinde fazla</span>
      </div>
      <div className="diffGrid">
        <DiffText title="Beklenen" side="expected" rows={rows} />
        <DiffText title="Girilen" side="received" rows={rows} />
      </div>
    </div>
  );
}

function DiffText({ title, side, rows }) {
  return (
    <div className="diffBox">
      <div className="diffTitle">{title}</div>
      <div className="diffText mono">
        {rows.length ? (
          rows.map((row, index) => {
            const value = side === "expected" ? row.expected : row.received;
            if (value === null || value === undefined) return null;
            const className = diffClassName(row, side);
            return (
              <mark className={className} key={`${side}-${index}`}>
                {visibleWhitespace(value)}
              </mark>
            );
          })
        ) : (
          <span className="muted">-</span>
        )}
      </div>
    </div>
  );
}

function diffClassName(row, side) {
  if (row.type === "equal") return "diffToken";
  if (row.type === "space") return "diffToken diffSpace";
  if (row.type === "changed") return "diffToken diffChanged";
  if (row.type === "missing") return side === "expected" ? "diffToken diffMissing" : "diffToken";
  if (row.type === "extra") return side === "received" ? "diffToken diffExtra" : "diffToken";
  return "diffToken";
}

function visibleWhitespace(value) {
  return String(value || "")
    .replace(/ /g, "·")
    .replace(/\t/g, "⇥")
    .replace(/\n/g, "↵\n");
}

function buildTextDiff(expected, received) {
  const expectedTokens = tokenizeDiffText(expected);
  const receivedTokens = tokenizeDiffText(received);
  const pairs = alignTokens(expectedTokens, receivedTokens);
  return pairs.map(([left, right]) => {
    if (left === null) return { type: "extra", expected: null, received: right.value };
    if (right === null) return { type: "missing", expected: left.value, received: null };
    if (left.value === right.value) return { type: "equal", expected: left.value, received: right.value };
    if (left.isSpace && right.isSpace) return { type: "space", expected: left.value, received: right.value };
    return { type: "changed", expected: left.value, received: right.value };
  });
}

function tokenizeDiffText(value) {
  const rawTokens = String(value || "").match(/\s+|[^\s]+/g) || [];
  return rawTokens.map((token) => ({
    value: token,
    isSpace: /^\s+$/.test(token),
    key: /^\s+$/.test(token) ? " " : token.toLocaleLowerCase("tr-TR"),
  }));
}

function alignTokens(expectedTokens, receivedTokens) {
  const rows = expectedTokens.length;
  const cols = receivedTokens.length;
  const table = Array.from({ length: rows + 1 }, () => Array(cols + 1).fill(0));
  for (let i = rows - 1; i >= 0; i -= 1) {
    for (let j = cols - 1; j >= 0; j -= 1) {
      table[i][j] =
        expectedTokens[i].key === receivedTokens[j].key
          ? table[i + 1][j + 1] + 1
          : Math.max(table[i + 1][j], table[i][j + 1]);
    }
  }

  const pairs = [];
  let i = 0;
  let j = 0;
  while (i < rows && j < cols) {
    if (expectedTokens[i].key === receivedTokens[j].key) {
      pairs.push([expectedTokens[i], receivedTokens[j]]);
      i += 1;
      j += 1;
    } else if (table[i + 1][j] >= table[i][j + 1]) {
      pairs.push([expectedTokens[i], null]);
      i += 1;
    } else {
      pairs.push([null, receivedTokens[j]]);
      j += 1;
    }
  }
  while (i < rows) {
    pairs.push([expectedTokens[i], null]);
    i += 1;
  }
  while (j < cols) {
    pairs.push([null, receivedTokens[j]]);
    j += 1;
  }
  return pairs;
}
