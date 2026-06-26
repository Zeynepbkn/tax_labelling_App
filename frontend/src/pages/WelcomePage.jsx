import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

const MOTIVATION_LINES = [
  "Seni burada görmekten mutluyum.",
  "Harika bir iş çıkaracaksın!",
  "Özelge metinleri seni bekliyor.",
  "Etiketleme yolculuğun başlıyor!",
  "Birlikte veri kalitesini artırıyoruz.",
  "Her etiket, modele değer katar.",
];

const CELEBRATION_EMOJIS = ["🎉", "🎊", "✨", "🎈", "⭐", "🎆"];

function CelebrationBurst({ className }) {
  return (
    <div className={`welcomeCelebration ${className}`} aria-hidden="true">
      {CELEBRATION_EMOJIS.map((emoji, i) => (
        <span
          key={`${className}-${emoji}`}
          className="welcomeCelebrationEmoji"
          style={{ "--burst-i": i }}
        >
          {emoji}
        </span>
      ))}
    </div>
  );
}

function ConfettiLayer() {
  const pieces = Array.from({ length: 64 }, (_, i) => i);
  return (
    <div className="welcomeConfetti" aria-hidden="true">
      {pieces.map((i) => (
        <span
          key={i}
          className="welcomeConfettiPiece"
          style={{
            "--i": i,
            "--left": `${(i * 17 + 7) % 100}%`,
            "--delay": `${(i % 12) * 0.18}s`,
            "--duration": `${2.4 + (i % 5) * 0.35}s`,
            "--hue": (i * 41) % 360,
          }}
        />
      ))}
    </div>
  );
}

function AnimatedMotivation() {
  const [index, setIndex] = useState(0);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const interval = setInterval(() => {
      setVisible(false);
      setTimeout(() => {
        setIndex((prev) => (prev + 1) % MOTIVATION_LINES.length);
        setVisible(true);
      }, 420);
    }, 3400);
    return () => clearInterval(interval);
  }, []);

  return (
    <p className={`welcomeMotivation ${visible ? "is-visible" : "is-fading"}`} aria-live="polite">
      <span className="welcomeMotivationGlow">{MOTIVATION_LINES[index]}</span>
    </p>
  );
}

export default function WelcomePage() {
  return (
    <div className="welcomePage">
      <ConfettiLayer />

      <CelebrationBurst className="welcomeCelebrationLeft" />
      <CelebrationBurst className="welcomeCelebrationRight" />

      <div className="welcomeHero card">
        <div className="welcomeEyebrow">ÖzelgeLab · TR</div>
        <h1 className="welcomeTitle">
          <span className="welcomeTitleWave">Hoşgeldiniz!</span>
        </h1>
        <p className="welcomeLead">
          Özelge metinlerinden soru ve cevaplarını belirleyip{" "}
          <strong>etiketleme</strong> yapmaya hazır mısınız?
        </p>

        <AnimatedMotivation />

        <div className="welcomeActions">
          <Link to="/giris" className="btn primary welcomeBtn">
            Giriş Yap
          </Link>
          <Link to="/kayit" className="btn welcomeBtn welcomeBtnOutline">
            Kayıt Ol
          </Link>
        </div>

        <p className="welcomeFootnote muted">
          Hesabınız varsa giriş yapın; yoksa birkaç dakikada kayıt olun ve hemen başlayın.
        </p>
      </div>

      <div className="welcomeFeatures">
        <div className="welcomeFeature card">
          <span className="welcomeFeatureIcon">📄</span>
          <div className="welcomeFeatureTitle">Özelge metinleri</div>
          <p className="muted">Gerçek vergi özelge metinlerinden soru–cevap çiftleri çıkarın.</p>
        </div>
        <div className="welcomeFeature card">
          <span className="welcomeFeatureIcon">🏷️</span>
          <div className="welcomeFeatureTitle">Etiketleme</div>
          <p className="muted">Bağlam, soru ve cevap alanlarını standartlara uygun işaretleyin.</p>
        </div>
        <div className="welcomeFeature card">
          <span className="welcomeFeatureIcon">🏆</span>
          <div className="welcomeFeatureTitle">Lider tablosu</div>
          <p className="muted">Katkınızı takip edin, ekiple birlikte ilerleyin.</p>
        </div>
      </div>
    </div>
  );
}
