import React, { useEffect, useState } from "react";

const dragonAccent = {
  ruby: "#d92d20",
  emerald: "#039855",
  sapphire: "#1570ef",
  amber: "#dc6803",
  violet: "#7a5af8",
  aqua: "#0891b2",
  rose: "#e31b54",
  gold: "#ca8504"
};

function Dragon({ dragon, flying = false }) {
  const color = dragonAccent[dragon.color] || "#1570ef";
  return (
    <div className={`dragon ${flying ? "flyingDragon" : ""}`} style={{ "--dragon": color }}>
      <div className="dragonWing left" />
      <div className="dragonWing right" />
      <div className="dragonBody" />
      <div className="dragonHead" />
      <div className="dragonTail" />
      <div className="dragonFlame" />
    </div>
  );
}

function Sparkles({ active }) {
  if (!active) return null;
  return (
    <div className="sparkleLayer" aria-hidden="true">
      {Array.from({ length: 18 }, (_, index) => (
        <span key={index} style={{ "--i": index }} />
      ))}
    </div>
  );
}

function DragonRewardOverlay({ dragon, onClose }) {
  const rewardCopy = dragon.milestone > 0
    ? `Bugün ${dragon.milestone * 25} belgeye ulaştınız. Koleksiyonunuza yeni bir ejderha katıldı.`
    : "Mini sınavı geçtiniz. İlk ejderhanız koleksiyonunuza katıldı.";
  return (
    <div className="dragonRewardOverlay" role="dialog" aria-modal="true" aria-label="Yeni ejderha ödülü">
      <div className="dragonRewardBurst" aria-hidden="true">
        {Array.from({ length: 28 }, (_, index) => (
          <span key={index} style={{ "--i": index }} />
        ))}
      </div>
      <div className="dragonRewardModal">
        <div className="sectionEyebrow">Yeni ödül</div>
        <div className="dragonRewardTitle">Yumurta çatladı</div>
        <div className="muted dragonRewardCopy">
          {rewardCopy}
        </div>
        <div className="dragonHatchStage" aria-hidden="true">
          <div className="hatchGlow" />
          <div className="hatchingEgg">
            <span className="hatchCrack" />
            <span className="eggShell top" />
            <span className="eggShell bottom" />
          </div>
          <Dragon dragon={dragon} flying />
        </div>
        <div className="dragonRewardName">{dragon.name}</div>
        <div className="muted dragonRewardMeta">{dragon.reward_date} · {dragon.color}</div>
        <button className="btn primary" type="button" onClick={onClose}>
          Devam Et
        </button>
      </div>
    </div>
  );
}

function DailyBars({ dailyCounts = [] }) {
  const max = Math.max(1, ...dailyCounts.map((item) => item.count || 0));
  return (
    <div className="dailyBars">
      {dailyCounts.map((item) => {
        const date = new Date(`${item.date}T00:00:00`);
        const label = Number.isNaN(date.getTime())
          ? item.date
          : date.toLocaleDateString("tr-TR", { weekday: "short" });
        return (
          <div className="dailyBar" key={item.date}>
            <div className="dailyBarTrack">
              <div className="dailyBarFill" style={{ height: `${Math.max(8, ((item.count || 0) / max) * 100)}%` }} />
            </div>
            <div className="dailyBarCount">{item.count || 0}</div>
            <div className="dailyBarLabel">{label}</div>
          </div>
        );
      })}
    </div>
  );
}

export default function GamificationPanel({ progress }) {
  const messages = progress?.motivation_messages || [];
  const dragons = progress?.dragon_rewards || [];
  const newestDragon = dragons[0];
  const showEgg = progress?.dragon_awarded_today && newestDragon;
  const [showRewardOverlay, setShowRewardOverlay] = useState(false);
  const today = progress?.today_completed_count || 0;
  const remaining = 25 - (today % 25);

  useEffect(() => {
    if (!showEgg || !newestDragon?.id) {
      setShowRewardOverlay(false);
      return;
    }
    const storageKey = `taxlabeltr_dragon_reward_seen_${newestDragon.id}`;
    if (localStorage.getItem(storageKey)) {
      setShowRewardOverlay(false);
      return;
    }
    setShowRewardOverlay(true);
    localStorage.setItem(storageKey, "1");
  }, [showEgg, newestDragon?.id]);

  return (
    <>
    {showRewardOverlay ? (
      <DragonRewardOverlay dragon={newestDragon} onClose={() => setShowRewardOverlay(false)} />
    ) : null}
    <div className="gamificationGrid">
      <div className="card gamificationHero">
        <Sparkles active={messages.some((msg) => ["improved", "best", "dragon"].includes(msg.kind))} />
        <div>
          <div className="sectionEyebrow">Motivasyon</div>
          <div className="gameTitle">{messages[0]?.title || "Ritim sende"}</div>
          <div className="muted gameCopy">{messages[0]?.message || "Bugün etiketleme için iyi bir gün."}</div>
        </div>

        {showEgg ? (
          <div className="eggStage">
            <div className="crackingEgg">
              <span />
            </div>
            <Dragon dragon={newestDragon} flying />
          </div>
        ) : (
          <div className="eggStage resting">
            <div className="restingEgg">
              <span>{remaining}</span>
            </div>
            <div className="muted eggNote">
              {`${remaining} belge sonra sıradaki yumurta çatlar`}
            </div>
          </div>
        )}

        {messages.length > 1 ? (
          <div className="messageChips">
            {messages.slice(1).map((msg) => (
              <span className={`messageChip ${msg.kind}`} key={`${msg.kind}-${msg.title}`}>
                {msg.title}
              </span>
            ))}
          </div>
        ) : null}
      </div>

      <div className="card dailyProgressCard">
        <div className="row between">
          <div>
            <div className="sectionEyebrow">Günlük kıyas</div>
            <div style={{ fontWeight: 900, marginTop: 4 }}>Son 7 gün</div>
          </div>
          <span className={`badge ${progress?.improvement_delta > 0 ? "successBadge" : ""}`}>
            {progress?.improvement_delta > 0 ? `+${progress.improvement_delta}` : progress?.improvement_delta || 0}
          </span>
        </div>
        <DailyBars dailyCounts={progress?.daily_counts || []} />
      </div>

      <div className="card dragonCollection">
        <div className="row between">
          <div>
            <div className="sectionEyebrow">Ejderhalar</div>
            <div style={{ fontWeight: 900, marginTop: 4 }}>{dragons.length} ejderha</div>
          </div>
          <span className="badge">Her 25 belge</span>
        </div>
        {dragons.length ? (
          <div className="dragonShelf">
            {dragons.map((dragon) => (
              <div className="dragonCard" key={dragon.id}>
                <Dragon dragon={dragon} />
                <div>
                  <div style={{ fontWeight: 900 }}>{dragon.name}</div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {dragon.reward_date} · {dragon.color}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="emptyDragonShelf">
            <div className="restingEgg small" />
            <div className="muted">İlk ejderha için bir günde 25 belge hedefi var.</div>
          </div>
        )}
      </div>
    </div>
    </>
  );
}
