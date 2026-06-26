import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiClient } from '../api/apiClient';
import { useAuth } from '../contexts/AuthContext';
import LoadingSpinner from '../components/LoadingSpinner';
import QuestionBox from '../components/QuestionBox';
import WarningModal from '../components/WarningModal';
import { hasAtLeastOneQuestion, isNonEmptyText } from '../utils/validators';
import { formatDocumentTextForReading } from '../utils/textFormatting';
import { cleanLabelingFieldText } from '../utils/labelingText';
import { useTimer } from '../components/Timer';
import { PASSING_SCORE, QUICK_GUIDE_SECTIONS } from '../utils/labelingGuideContent';

function parseWarnings(err) {
  const detail = err?.response?.data?.detail;
  if (detail && typeof detail === 'object' && Array.isArray(detail.warnings))
    return detail.warnings;
  return null;
}

function parseBlockingErrors(err) {
  const detail = err?.response?.data?.detail;
  if (detail && typeof detail === 'object' && Array.isArray(detail.errors))
    return detail.errors;
  return null;
}

export default function LabelingPage() {
  const { examPassed, role } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const editParam = searchParams.get('duzenle') || '';

  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editingRecordId, setEditingRecordId] = useState(null);
  const [readyToLabel, setReadyToLabel] = useState(false);

  const [questions, setQuestions] = useState(['']);
  const [cevap, setCevap] = useState('');
  const [saving, setSaving] = useState(false);

  const [warningsOpen, setWarningsOpen] = useState(false);
  const [warnings, setWarnings] = useState([]);
  const [pendingForce, setPendingForce] = useState(false);
  const [validationWarningsOpen, setValidationWarningsOpen] = useState(false);
  const [validationWarnings, setValidationWarnings] = useState([]);
  const [validationBlockedAfterForce, setValidationBlockedAfterForce] = useState(false);

  /** Düzenleme: API’den gelen önceki tamamlama süresi (sn); yeni belgede kullanılmaz */
  const [editSavedDurationSeconds, setEditSavedDurationSeconds] = useState(0);

  const resetKey =
    editingRecordId != null
      ? `edit-${editingRecordId}`
      : doc?.document_id || doc?.id || 'none';
  const timerInitialSeconds =
    editingRecordId != null ? editSavedDurationSeconds : 0;
  const timer = useTimer(
    resetKey,
    timerInitialSeconds,
    readyToLabel && !loading && !!doc,
  );
  const readableDocumentText = useMemo(
    () => formatDocumentTextForReading(doc?.display_text),
    [doc?.display_text],
  );

  const loadNext = useCallback(async () => {
    setLoading(true);
    setError(null);
    setEditingRecordId(null);
    setEditSavedDurationSeconds(0);
    try {
      const res = await apiClient.get('/documents/next');
      setDoc(res.data);
      setQuestions(['']);
      setCevap('');
      setWarnings([]);
      setWarningsOpen(false);
      setPendingForce(false);
      setValidationWarnings([]);
      setValidationWarningsOpen(false);
      setValidationBlockedAfterForce(false);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Uygun belge bulunamadı.';
      setError(typeof msg === 'string' ? msg : 'Uygun belge bulunamadı.');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadForEdit = useCallback(async (recordId) => {
    setLoading(true);
    setError(null);
    setEditingRecordId(null);
    setEditSavedDurationSeconds(0);
    setWarnings([]);
    setWarningsOpen(false);
    setPendingForce(false);
    setValidationWarnings([]);
    setValidationWarningsOpen(false);
    setValidationBlockedAfterForce(false);
    try {
      const recRes = await apiClient.get(`/labeling/records/${recordId}`);
      const r = recRes.data;
      const docRes = await apiClient.get(
        `/documents/${encodeURIComponent(r.evrak_id)}`,
      );
      const d = docRes.data;
      const baseline =
        typeof r.belgeyi_tamamlama_suresi_seconds === 'number'
          ? r.belgeyi_tamamlama_suresi_seconds
          : 0;
      setDoc({
        document_id: d.id,
        evrak_id: d.evrak_id,
        display_text: d.display_text,
        display_source: d.display_source,
        konu: d.konu,
        tarih: d.tarih,
        basvuru_tarihi: d.basvuru_tarihi,
        vergi_turu: d.vergi_turu,
        vergi_donemi: d.vergi_donemi,
      });
      const ordered = (r.questions || [])
        .slice()
        .sort((a, b) => a.question_order - b.question_order);
      const texts = ordered.map((q) => q.question_text || '');
      setQuestions(texts.length ? texts : ['']);
      setCevap(r.cevap || '');
      setEditSavedDurationSeconds(baseline);
      setEditingRecordId(recordId);
    } catch (err) {
      const msg =
        err?.response?.data?.detail || 'Kayıt veya belge yüklenemedi.';
      setError(typeof msg === 'string' ? msg : 'Kayıt veya belge yüklenemedi.');
      setDoc(null);
      setEditingRecordId(null);
      setEditSavedDurationSeconds(0);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!examPassed && role !== 'admin') return;
    const idNum = Number(editParam);
    if (editParam && Number.isFinite(idNum) && idNum > 0) {
      loadForEdit(idNum);
      return;
    }
    loadNext();
  }, [examPassed, role, editParam, loadForEdit, loadNext]);

  const submit = useCallback(
    async (force_submit) => {
      if (!doc) return;
      setSaving(true);
      setError(null);
      try {
        const qPayload = questions.map((q) => cleanLabelingFieldText(q));
        const base = {
          questions: qPayload,
          cevap: cleanLabelingFieldText(cevap),
          belgeyi_tamamlama_suresi: timer.seconds,
          force_submit: !!force_submit,
        };
        let res;
        if (editingRecordId != null) {
          res = await apiClient.patch(
            `/labeling/records/${editingRecordId}`,
            base,
          );
          navigate('/panel', { replace: true });
        } else {
          res = await apiClient.post('/labeling/submit', {
            document_id: doc.document_id,
            ...base,
          });
          await loadNext();
        }
        return res.data;
      } catch (err) {
        const ws = parseWarnings(err);
        if (ws && ws.length) {
          setWarnings(ws);
          setWarningsOpen(true);
          setPendingForce(true);
          return null;
        }
        const blockingErrors = parseBlockingErrors(err);
        if (blockingErrors && blockingErrors.length) {
          setValidationWarnings(blockingErrors);
          setValidationBlockedAfterForce(!!force_submit);
          setValidationWarningsOpen(true);
          return null;
        }
        const msg = err?.response?.data?.detail || 'Kayıt başarısız.';
        setError(typeof msg === 'string' ? msg : 'Kayıt başarısız.');
        return null;
      } finally {
        setSaving(false);
      }
    },
    [doc, questions, cevap, timer.seconds, loadNext, editingRecordId, navigate],
  );

  const onPrimarySubmit = async () => {
    const missingFields = [];
    if (!hasAtLeastOneQuestion(questions)) missingFields.push('En az bir soru girmelisiniz.');
    if (!isNonEmptyText(cevap)) missingFields.push('Cevap alanı zorunludur.');

    if (missingFields.length) {
      setError(null);
      setValidationWarnings(missingFields);
      setValidationWarningsOpen(true);
      return;
    }
    await submit(false);
  };

  if (!examPassed && role !== 'admin') {
    return (
      <div className="container">
        <div className="lockedAccessPanel">
          <span className="badge warningBadge">Quiz gerekli</span>
          <div className="lockedAccessTitle">Quize başlamadınız veya geçme notunu henüz almadınız.</div>
          <div className="lockedAccessText">
            Gerçek etiketleme yapabilmek için mini sınavdan en az {PASSING_SCORE} puan almalısınız. Quize başladıktan sonra {PASSING_SCORE} ve üzeri puan aldığınızda Etiketleme sekmesi açılır.
          </div>
          <div className="row" style={{ justifyContent: 'flex-end', flexWrap: 'wrap', marginTop: 16 }}>
            <button className="btn" type="button" onClick={() => navigate('/kilavuz')}>
              Kılavuza Dön
            </button>
            <button className="btn primary" type="button" onClick={() => navigate('/sinav')}>
              Quize Başla
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!readyToLabel) {
    return (
      <div className="container">
        <div
          className="card grid"
          style={{ maxWidth: 760, margin: '40px auto 0' }}
        >
          <div>
            <div style={{ fontWeight: 900, fontSize: 22 }}>
              Etiketleme yapmaya hazır mısınız?
            </div>
            <div className="muted" style={{ marginTop: 8 }}>
              Başlamadan önce soru ve cevap çıkarma kurallarını hızlıca gözden
              geçirin.
            </div>
          </div>

          <GuideSectionGrid />

          <div
            className="row"
            style={{ justifyContent: 'flex-end', flexWrap: 'wrap' }}
          >
            <button className="btn" type="button" onClick={() => navigate(-1)}>
              Geri
            </button>
            <button
              className="btn primary"
              type="button"
              onClick={() => setReadyToLabel(true)}
            >
              Hazırım
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (loading) return <LoadingSpinner label="Belge yükleniyor..." />;

  return (
    <div className="container grid">
      <div className="card row between">
        <div>
          <div style={{ fontWeight: 900, fontSize: 20 }}>
            Etiketleme
            {editingRecordId != null ? (
              <span className="muted"> — düzenleme</span>
            ) : null}
          </div>
          <div className="muted" style={{ marginTop: 6 }}>
            {editingRecordId != null
              ? 'Önceki etiketinizi güncelleyebilirsiniz. Kaydedince panele dönersiniz.'
              : 'Sol: özelge metni, Sağ: sorular + cevap.'}
          </div>
        </div>
        <div className="row" style={{ gap: 10 }}>
          <span className="badge">Kaynak: {doc?.display_source}</span>
          <span className="badge">
            Evrak: <span className="mono">{doc?.evrak_id}</span>
          </span>
          <span className="badge">Süre: {timer.seconds}s</span>
        </div>
      </div>

      {error ? (
        <div
          className="card"
          style={{ color: 'var(--danger)', fontWeight: 800 }}
        >
          {error}
        </div>
      ) : null}

      <div className="splitLayout">
        <div className="card">
          <div className="row between">
            <div>
              <div style={{ fontWeight: 900 }}>Özelge Metni</div>
              <div className="muted" style={{ marginTop: 6 }}>
                Konu: {doc?.konu || '-'} | Tarih: {doc?.tarih || '-'}
              </div>
            </div>
          </div>
          <pre
            className="card mono"
            style={{
              marginTop: 12,
              whiteSpace: 'pre-wrap',
              overflow: 'auto',
              maxHeight: '70vh',
            }}
          >
            {readableDocumentText}
          </pre>
        </div>

        <div className="grid" style={{ alignContent: 'start' }}>
          <div className="card">
            <div className="row between">
              <div style={{ fontWeight: 900 }}>Sorular</div>
              <button
                className="btn"
                type="button"
                onClick={() => setQuestions((qs) => [...qs, ''])}
              >
                Yeni Soru Ekle
              </button>
            </div>
            <div className="muted" style={{ marginTop: 6 }}>
              Her soruyu ayrı kutuya yazın. Bağlam eklemeyi unutmayın.
            </div>
          </div>

          {questions.map((q, idx) => (
            <QuestionBox
              key={idx}
              index={idx}
              value={q}
              onChange={(val) =>
                setQuestions((qs) => qs.map((x, i) => (i === idx ? val : x)))
              }
              onRemove={() =>
                setQuestions((qs) => qs.filter((_, i) => i !== idx))
              }
              canRemove={questions.length > 1}
            />
          ))}

          <div className="card">
            <div className="row between" style={{ marginBottom: 8 }}>
              <div style={{ fontWeight: 900 }}>Cevap</div>
              <span className="badge">Zorunlu</span>
            </div>
            <textarea
              value={cevap}
              onChange={(e) => setCevap(e.target.value)}
              placeholder="İdarenin cevap/değerlendirme kısmını buraya yapıştırın..."
            />
          </div>

          <div className="card row between">
            <div className="muted">
              Kaydetmeden önce kontrol edin. Backend gerekirse uyarı modalı
              gösterecek.
            </div>
            <div className="row">
              {editingRecordId != null ? (
                <button
                  className="btn"
                  type="button"
                  onClick={() => navigate('/panel', { replace: true })}
                >
                  İptal
                </button>
              ) : (
                <button className="btn" type="button" onClick={loadNext}>
                  Sonraki Belge
                </button>
              )}
              <button
                className="btn primary"
                disabled={saving}
                type="button"
                onClick={onPrimarySubmit}
              >
                {saving
                  ? 'Kaydediliyor...'
                  : editingRecordId != null
                    ? 'Güncelle'
                    : 'Kaydet'}
              </button>
            </div>
          </div>
        </div>
      </div>

      <WarningModal
        open={warningsOpen}
        warnings={warnings}
        onCancel={() => {
          setWarningsOpen(false);
          setPendingForce(false);
        }}
        onConfirm={async () => {
          setWarningsOpen(false);
          await submit(true);
          setPendingForce(false);
        }}
      />
      <WarningModal
        open={validationWarningsOpen}
        title="Kayıt Engellendi"
        description={
          validationBlockedAfterForce
            ? "Bu hatalar 'Eminim' ile geçilemez. Metni düzeltip tekrar kaydetmeniz gerekir."
            : "Bu kayıt kaydedilemez. Lütfen geçerli bir kayıt yapınız."
        }
        warnings={validationWarnings}
        cancelLabel="Kontrol et"
        onCancel={() => {
          setValidationWarningsOpen(false);
          setValidationBlockedAfterForce(false);
        }}
      />
    </div>
  );
}

function GuideSectionGrid() {
  return (
    <div className="guideQuickGrid compact">
      {QUICK_GUIDE_SECTIONS.map((section) => (
        <section className={`guideInfoBox ${section.accent}`} key={section.title}>
          <div className="guideInfoTitle">{section.title}</div>
          <ul className="guideInfoList">
            {section.items.map((item) => {
              const content = typeof item === 'string' ? item : item.text;
              return (
                <li
                  className={item.important ? 'guideImportantItem' : undefined}
                  key={content}
                >
                  {item.important ? (
                    <span aria-hidden="true" className="guideImportantIcon">!</span>
                  ) : null}
                  <span>{content}</span>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
