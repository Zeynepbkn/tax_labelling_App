import React from "react";
import { formatTime } from "../utils/formatTime";

function LeaderboardRows({ entries }) {
  return entries.map((entry) => (
    <tr key={entry.user_id} className={entry.is_current_user ? "leaderboardCurrentRow" : ""}>
      <td className="leaderboardRank">#{entry.rank}</td>
      <td>
        <div className="leaderboardUser">
          <span>{entry.kullanici_adi}</span>
          {entry.is_current_user ? <span className="badge">Sen</span> : null}
        </div>
      </td>
      <td className="leaderboardScore">{entry.total_score ?? 0}</td>
      <td>{entry.completed_count}</td>
      <td>{entry.today_completed_count}</td>
      <td>{entry.dragon_count}</td>
      <td>{entry.avg_duration_seconds ? formatTime(Math.round(entry.avg_duration_seconds)) : "-"}</td>
    </tr>
  ));
}

export default function LeaderboardTable({ leaderboard, compact = false }) {
  const entries = leaderboard?.entries || [];
  const current = leaderboard?.current_user;
  const currentIsVisible = Boolean(current && entries.some((entry) => entry.user_id === current.user_id));

  if (!entries.length) {
    return <div className="muted" style={{ marginTop: 12 }}>Henüz sıralama için veri yok.</div>;
  }

  return (
    <>
      <table className={`table leaderboardTable ${compact ? "compactLeaderboard" : ""}`} style={{ marginTop: 12 }}>
        <thead>
          <tr>
            <th>Sıra</th>
            <th>Kullanıcı</th>
            <th>Skor</th>
            <th>Toplam</th>
            <th>Bugün</th>
            <th>Ejderha</th>
            <th>Ort. Sure</th>
          </tr>
        </thead>
        <tbody>
          <LeaderboardRows entries={entries} />
        </tbody>
      </table>

      {current && !currentIsVisible ? (
        <div className="ownLeaderboardStrip" style={{ marginTop: 12 }}>
          <span className="leaderboardRank">#{current.rank}</span>
          <span>{current.kullanici_adi}</span>
          <span className="badge">Sen</span>
          <strong>{current.total_score ?? 0} skor</strong>
          <span className="muted">{current.completed_count} belge</span>
        </div>
      ) : null}
    </>
  );
}
