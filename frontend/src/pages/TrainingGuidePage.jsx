import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../api/apiClient";
import { useAuth } from "../contexts/AuthContext";
import LoadingSpinner from "../components/LoadingSpinner";
import { formatDocumentTextForReading } from "../utils/textFormatting";
import { PASSING_SCORE, QUICK_GUIDE_SECTIONS } from "../utils/labelingGuideContent";

const LABELING_ROUTE = "/etiketleme";

export default function TrainingGuidePage() {
  const { examPassed, role } = useAuth();
  const navigate = useNavigate();
  const canLabel = examPassed || role === "admin";
  const [guide, setGuide] = useState(null);
  const [examples, setExamples] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const g = await apiClient.get("/training/guide");
        const ex = await apiClient.get("/training/examples");
        if (!alive) return;
        setGuide(g.data);
        setExamples(ex.data || []);
      } catch (err) {
        const msg = err?.response?.data?.detail || "Eğitim içeriği alınamadı.";
        setError(typeof msg === "string" ? msg : "Eğitim içeriği alınamadı.");
      } finally {
        if (alive) setLoading(false);
      }
    }
    load();
    return () => {
      alive = false;
    };
  }, []);

  if (loading) return <LoadingSpinner label="Eğitim içeriği yükleniyor..." />;

  return (
    <div className="container grid">
      <div className="card">
        <div className="row between">
          <div>
            <div style={{ fontWeight: 900, fontSize: 20 }}>
              {guide?.title || "Kılavuz"}
            </div>
            <div className="muted" style={{ marginTop: 6 }}>
              {canLabel
                ? "Kısa bilgilendirme ve hızlı başlangıç."
                : "Detaylı eğitim + örnek özelgeler + mini sınav."}
            </div>
          </div>
          <span className="badge">Rol: {role}</span>
        </div>

        {error ? (
          <div style={{ color: "var(--danger)", fontWeight: 700, marginTop: 12 }}>
            {error}
          </div>
        ) : null}

        {!canLabel ? (
          <div className="guideCtaPanel" style={{ marginTop: 14 }}>
            <div>
              <div className="guideCtaTitle">Eğitimi okuduktan sonra quiz burada.</div>
              <div className="guideCtaText">
                Gerçek etiketleme havuzuna geçmek için mini sınavdan en az {PASSING_SCORE} puan almalısınız.
              </div>
            </div>
            <button className="btn primary guideCtaButton" onClick={() => navigate("/sinav")} type="button">
              Quize Başla
            </button>
          </div>
        ) : null}

        {canLabel ? (
          <div className="guideSuccessPanel" style={{ marginTop: 14 }}>
            <div style={{ fontWeight: 900 }}>Sınavı geçtiniz.</div>
            <div className="muted" style={{ marginTop: 6 }}>
              Artık gerçek etiketleme havuzundan belge alabilirsiniz. Aşağıdaki kısa hatırlatmayı etiketlemeye
              başlamadan önce kontrol edin.
            </div>
          </div>
        ) : null}

        <GuideSectionGrid />

        {guide?.content_markdown ? (
          <div className="guidePlainBox" style={{ marginTop: 14 }}>
            <div className="guidePlainTitle">
              {canLabel ? "Kısa Bilgilendirme Metni" : "Eğitim Açıklaması"}
            </div>
            <MarkdownContent value={guide.content_markdown} />
          </div>
        ) : null}

        {canLabel ? (
          <div className="row" style={{ justifyContent: "flex-end", marginTop: 12 }}>
            <button className="btn primary" onClick={() => navigate(LABELING_ROUTE)} type="button">
              Etiketlemeye Başla
            </button>
          </div>
        ) : null}
      </div>

      {!canLabel ? (
        <div className="card">
          <div style={{ fontWeight: 900, fontSize: 18 }}>Örnekler</div>
          <div className="muted" style={{ marginTop: 6 }}>
            Aşağıdaki örnekler, soruların bağlamıyla nasıl çıkarılması gerektiğini gösterir.
          </div>

          <div className="grid" style={{ marginTop: 12 }}>
            {examples.map((ex, idx) => (
              <div className="card" key={`${ex.evrak_id}-${idx}`}>
                <div className="row between">
                  <div style={{ fontWeight: 900 }}>
                    Evrak: <span className="mono">{ex.evrak_id}</span>
                  </div>
                  <span className="badge">
                    {ex.training_label_id ? `Label: ${ex.training_label_id} | ` : ""}
                    Gold soru: {ex.gold_sorular?.length || 0}
                  </span>
                </div>
                <div className="muted" style={{ marginTop: 8, fontSize: 12 }}>
                  Özelge metni (kısaltılmış):
                </div>
                <pre className="card mono" style={{ overflow: "auto", whiteSpace: "pre-wrap", marginTop: 8 }}>
                  {(() => {
                    const full = formatDocumentTextForReading(ex.ozelge_metni || "");
                    return full.length > 1200 ? `${full.slice(0, 1200)}\n\n... (devamı kısaltıldı)` : full;
                  })()}
                </pre>

                <div style={{ marginTop: 10, fontWeight: 800 }}>
                  Doğru soru/sorular
                </div>
                <ul style={{ margin: 0, paddingLeft: 18, marginTop: 6 }}>
                  {(ex.gold_sorular || []).map((q, i) => (
                    <li key={i} style={{ marginBottom: 8 }}>
                      {q}
                    </li>
                  ))}
                </ul>

                {ex.aciklama ? (
                  <>
                    <div style={{ marginTop: 10, fontWeight: 800 }}>
                      Açıklama
                    </div>
                    <div className="card" style={{ marginTop: 6, whiteSpace: "pre-wrap" }}>
                      {ex.aciklama}
                    </div>
                  </>
                ) : null}

                {ex.gold_cevap ? (
                  <>
                    <div style={{ marginTop: 10, fontWeight: 800 }}>
                      Örnek Cevap (varsa)
                    </div>
                    <pre className="card mono" style={{ marginTop: 6, whiteSpace: "pre-wrap" }}>
                      {ex.gold_cevap}
                    </pre>
                  </>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function GuideSectionGrid() {
  return (
    <div className="guideQuickGrid">
      {QUICK_GUIDE_SECTIONS.map((section) => (
        <section className={`guideInfoBox ${section.accent}`} key={section.title}>
          <div className="guideInfoTitle">{section.title}</div>
          <ul className="guideInfoList">
            {section.items.map((item) => {
              const content = typeof item === "string" ? item : item.text;
              return (
                <li
                  className={item.important ? "guideImportantItem" : undefined}
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

function MarkdownContent({ value }) {
  const blocks = parseMarkdown(value || "");
  return (
    <div className="guideMarkdown">
      {blocks.map((block, index) => {
        if (block.type === "heading") {
          const HeadingTag = block.level === 3 ? "h3" : "h2";
          return <HeadingTag key={index}>{renderInlineMarkdown(block.text)}</HeadingTag>;
        }
        if (block.type === "list") {
          return (
            <ul key={index}>
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>{renderInlineMarkdown(item)}</li>
              ))}
            </ul>
          );
        }
        return <p key={index}>{renderInlineMarkdown(block.text)}</p>;
      })}
    </div>
  );
}

function parseMarkdown(markdown) {
  const lines = String(markdown).replace(/\r\n/g, "\n").split("\n");
  const blocks = [];
  let paragraph = [];
  let listItems = [];

  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push({ type: "paragraph", text: paragraph.join(" ").trim() });
      paragraph = [];
    }
  };
  const flushList = () => {
    if (listItems.length) {
      blocks.push({ type: "list", items: listItems });
      listItems = [];
    }
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      flushParagraph();
      flushList();
      continue;
    }
    const headingMatch = line.match(/^(#{2,3})\s+(.+)$/);
    if (headingMatch) {
      flushParagraph();
      flushList();
      blocks.push({ type: "heading", level: headingMatch[1].length, text: headingMatch[2] });
      continue;
    }
    if (line.startsWith("- ")) {
      flushParagraph();
      listItems.push(line.slice(2).trim());
      continue;
    }
    flushList();
    paragraph.push(line);
  }

  flushParagraph();
  flushList();
  return blocks;
}

function renderInlineMarkdown(text) {
  return String(text)
    .split(/(\*\*[^*]+\*\*|`[^`]+`)/g)
    .filter(Boolean)
    .map((part, index) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={index}>{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith("`") && part.endsWith("`")) {
        return <code key={index}>{part.slice(1, -1)}</code>;
      }
      return <React.Fragment key={index}>{part}</React.Fragment>;
    });
}
